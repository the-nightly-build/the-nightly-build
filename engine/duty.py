# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Compute scheduled work deterministically from config and library state.

The orchestrator runs this before researching anything. It is the single
source of truth for cadence, pauses, completion, commission queues, and
rerun safety, so no agent ever does calendar math on its own.

Because it runs first, it is also where a wrong tree is caught. It refuses,
rather than answering, in two cases:

  No press. An empty work list used to mean the same thing whether the paper
  had no scheduled work or the tree had no press/ at all. On 2026-07-14 a
  scheduled agent read an empty list, went looking for a configuration, and
  adopted the engine's own examples/ folder: three articles for series this
  paper retired months ago, every local proof passing, CI blocking all of it.
  A missing press is not an empty scheduled run. It means you are in the wrong
  tree.

  A stale checkout. A cached workspace serves a press, prompts, and an engine
  the paper has moved past, and nothing downstream can tell.

Run: python3 engine/duty.py --repo . [--library <library-checkout>] [--date YYYY-MM-DD]
Prints JSON: {"date", "weekday", "due": [...], "idle": [...]}. Exits 0, except
2 when the tree is refused (--allow-stale skips the staleness check, for
offline work; nothing skips the missing-press check).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import subprocess
import sys

from nb import meta as nb_meta
from nb.git_handoff import GitHandoffError
from nb.library_checkout import LibraryCheckoutError, ensure_library

try:
    import yaml
except ImportError:
    sys.stderr.write("duty.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
CADENCE_WORDS = ("daily", "weekdays", "weekends", "manual")


def cadence_is_valid(cadence: object) -> bool:
    """Validate an author-time cadence value strictly.

    This is the strict author-time twin of cadence_includes: validate_config
    asks this, while the fail-open evaluation below never skips work over a
    value validation would have flagged. Keeping both here means the vocabulary
    cannot drift between the validator and the scheduler.
    """
    if isinstance(cadence, str):
        return cadence in CADENCE_WORDS
    return isinstance(cadence, list) and len(cadence) > 0 and all(d in DAY_NAMES for d in cadence)


def cadence_includes(cadence: object, day: str) -> bool:
    if cadence in (None, "daily"):
        return True
    scalar_rules = {
        "weekdays": day not in ("sat", "sun"),
        "weekends": day in ("sat", "sun"),
        "manual": False,
    }
    if isinstance(cadence, str) and cadence in scalar_rules:
        return scalar_rules[cadence]
    if isinstance(cadence, list):
        days = [str(d).lower() for d in cadence]
        if "manual" in days:
            return False  # a stated manual must never fail open into daily work
        return day in days if any(d in DAY_NAMES for d in days) else True
    return True  # unknown value: validate_config flags it; never skip work here


def published_state(library: str | pathlib.Path, series_id: str) -> tuple[set[str], set[str]]:
    """Return (published slugs, published nb-meta dates) for one series.

    Slugs drive dedupe and completion checks. The nb-meta dates exist for rerun
    safety: an article published on the current UTC date idles its series even
    when its slug is topical rather than dated.
    """
    base = nb_meta.series_dir(str(library), series_id)
    if base is None:
        return set(), set()
    slugs: set[str] = set()
    dates: set[str] = set()
    for path in pathlib.Path(base).iterdir():
        if path.suffix != ".html":
            continue
        slugs.add(path.stem)
        meta = nb_meta.read_meta(str(path))
        date = meta.get("date") if meta else None
        if isinstance(date, str):
            dates.add(date)
    return slugs, dates


def config_items(cfg: dict[str, object]) -> list[dict[str, object]]:
    """Return the series' items list, defensively narrowed from parsed YAML.

    series.yaml is user-edited, so items may be missing or malformed.
    Non-list values become an empty list, non-dict entries are dropped,
    and entries without a string slug are dropped too — every returned
    item is safe to index by ``slug``.
    """
    raw = cfg.get("items")
    if not isinstance(raw, list):
        return []
    items = [{str(k): v for k, v in it.items()} for it in raw if isinstance(it, dict)]
    return [it for it in items if isinstance(it.get("slug"), str)]


def _rolling_duty(entry: dict[str, object], *, pub: set[str], date: dt.date) -> tuple[bool, dict[str, object]]:
    slug = date.isoformat()
    if slug in pub:
        return False, {**entry, "reason": "already published on selected UTC date"}
    return True, {**entry, "slug": slug, "reason": "selected UTC date is unpublished"}


def _sequence_duty(
    entry: dict[str, object],
    *,
    items: list[dict[str, object]],
    unpublished: list[object],
) -> tuple[bool, dict[str, object]]:
    if not unpublished:
        return False, {**entry, "reason": "complete"}
    nxt = unpublished[0]
    order = next(i for i, it in enumerate(items, 1) if it.get("slug") == nxt)
    return True, {
        **entry,
        "slug": nxt,
        "order": order,
        "reason": f"{len(items) - len(unpublished)} of {len(items)} published; '{nxt}' is next",
    }


def _collection_duty(
    entry: dict[str, object],
    *,
    cfg: dict[str, object],
    items: list[dict[str, object]],
    unpublished: list[object],
) -> tuple[bool, dict[str, object]]:
    if not unpublished:
        return False, {**entry, "reason": "complete"}
    selection = cfg.get("selection", "in-order")
    candidates = unpublished if selection == "random" else unpublished[:1]
    return True, {
        **entry,
        "candidates": candidates,
        "selection": selection,
        "reason": f"{len(unpublished)} of {len(items)} items unpublished",
    }


def _open_duty(entry: dict[str, object], *, unpublished: list[object]) -> tuple[bool, dict[str, object]]:
    if unpublished:
        return True, {
            **entry,
            "commissions": unpublished,
            "reason": "commissioned items pending — publish one of these before an open pick",
        }
    return True, {
        **entry,
        "commissions": [],
        "reason": "open section — choose a topic within the beat; do not repeat a published slug",
    }


def _gate_reason(cfg: dict[str, object], *, pub_dates: set[str], date: dt.date, day: str) -> str | None:
    if cfg.get("paused"):
        return "paused"
    cadence = cfg.get("cadence")
    if not cadence_includes(cadence, day):
        return f"cadence {cadence} excludes the selected UTC date"
    if date.isoformat() in pub_dates:
        return "already published on selected UTC date"
    return None


def series_duty(
    sid: str,
    cfg: dict[str, object],
    *,
    pub: set[str],
    pub_dates: set[str],
    date: dt.date,
    day: str,
) -> tuple[bool, dict[str, object]]:
    """Decide whether one series publishes on the selected UTC date, and why.

    Returns (is_due, entry). The entry always names the series and mode,
    then either a reason for sitting out (paused, off-cadence, already
    published on the selected date, complete) or what to publish: a slug for
    sequence and rolling, candidates for collection (all remaining items under
    selection: random, otherwise just the next one), and commissions for open
    series with queued items. Gates apply in order: paused, then cadence, then
    already published on this date, so a paused series never reports a cadence
    excuse.
    """
    mode = cfg.get("mode")
    entry: dict[str, object] = {"series": sid, "mode": mode}

    reason = _gate_reason(cfg, pub_dates=pub_dates, date=date, day=day)
    if reason is not None:
        return False, {**entry, "reason": reason}

    items = config_items(cfg)
    unpublished = [it["slug"] for it in items if it.get("slug") not in pub]

    if mode == "rolling":
        return _rolling_duty(entry, pub=pub, date=date)
    if mode == "sequence":
        return _sequence_duty(entry, items=items, unpublished=unpublished)
    if mode == "collection":
        return _collection_duty(entry, cfg=cfg, items=items, unpublished=unpublished)
    if mode == "open":
        return _open_duty(entry, unpublished=unpublished)
    return False, {**entry, "reason": f"unknown mode {mode!r}"}


def git(repo: str | pathlib.Path, *args: str) -> str | None:
    git_bin = shutil.which("git")
    if git_bin is None:
        return None
    try:
        done = subprocess.run(
            [git_bin, "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def stale_checkout(repo: str | pathlib.Path) -> str | None:
    """Say how the tree is behind origin/main, or None when it is not.

    Only a strict ancestor of origin/main is stale: a branch with local work
    is ahead or diverged, and a press check on a feature branch must keep
    working. A tree with no git, no origin, or no reachable remote cannot be
    judged, so it passes rather than blocking an offline run.
    """
    if git(repo, "rev-parse", "--git-dir") is None:
        return None
    if git(repo, "remote", "get-url", "origin") is None:
        return None
    git(repo, "fetch", "--quiet", "origin", "main")
    head = git(repo, "rev-parse", "HEAD")
    remote = git(repo, "rev-parse", "origin/main")
    if head is None or remote is None or head == remote:
        return None
    if git(repo, "merge-base", "HEAD", "origin/main") != head:
        return None  # ahead or diverged: local work, not a stale clone
    behind = git(repo, "rev-list", "--count", f"{head}..origin/main") or "?"
    return (
        f"stale checkout: HEAD is {head[:8]}, {behind} commits behind "
        f"origin/main ({remote[:8]}). The press, the prompts, and the engine "
        f"in this tree are not the ones this paper runs. Sync first:\n"
        f"    git -C {repo} fetch origin && git -C {repo} reset --hard origin/main\n"
        f"then run duty again. (--allow-stale overrides, for offline work only.)"
    )


def missing_press(repo: str | pathlib.Path) -> str | None:
    """Say why this tree holds no press, or None when it holds one.

    A paper whose series are all idle for the selected UTC date has no scheduled
    work, and duty answers with an empty due list. A tree with no press/series
    at all is the wrong directory, and an empty answer could invite the
    scheduled agent to find configuration somewhere else.
    """
    root = pathlib.Path(repo) / "press" / "series"
    if root.is_dir() and nb_meta.series_ids(str(repo)):
        return None
    return (
        f"no press at {repo!r}: {root} holds no configured series. This is not "
        f"an empty scheduled run; it is the wrong tree. The press is press/ and "
        f"nothing else: examples/ is documentation, never configuration, and "
        f"an article "
        f"written from it names a series the proof will refuse. Check out the "
        f"paper's main branch and run duty from its root."
    )


def _load_series_config(series_file: pathlib.Path) -> dict[str, object] | None:
    try:
        with series_file.open(encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
    except yaml.YAMLError:
        return None
    return cfg if isinstance(cfg, dict) else None


def _collect_schedule(
    repo: str, library: str, *, date: dt.date, day: str
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    due: list[dict[str, object]] = []
    idle: list[dict[str, object]] = []
    root = pathlib.Path(repo) / "press" / "series"
    for sid in nb_meta.series_ids(repo):
        cfg = _load_series_config(root / sid / "series.yaml")
        if cfg is None:
            # A bare string/list or unparseable series.yaml idles one series
            # with a reason; the run still exits 0 for every other series.
            idle.append({"series": sid, "mode": None, "reason": "series.yaml is not a mapping"})
            continue
        pub, pub_dates = published_state(library, sid)
        is_due, entry = series_duty(sid, cfg, pub=pub, pub_dates=pub_dates, date=date, day=day)
        (due if is_due else idle).append(entry)
    return due, idle


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Deterministic scheduled work list")
    p.add_argument("--repo", default=".", help="repo root (main checkout)")
    p.add_argument(
        "--library",
        default=None,
        help="library-branch checkout (published state); defaults to a checkout "
        "of origin/library that duty keeps under .nb-work/",
    )
    p.add_argument("--date", default=None, help="UTC date, default today")
    p.add_argument(
        "--allow-stale",
        action="store_true",
        help="compute a work list even from a tree behind origin/main",
    )
    args = p.parse_args(argv)

    refusal = missing_press(args.repo)
    if refusal is None and not args.allow_stale:
        refusal = stale_checkout(args.repo)
    if refusal:
        sys.stderr.write(f"duty.py: {refusal}\n")
        return 2
    library = args.library
    if library is None:
        try:
            library = str(ensure_library(pathlib.Path(args.repo)))
        except LibraryCheckoutError as error:
            sys.stderr.write(f"duty.py: {error}\n")
            return 2
        except GitHandoffError as error:
            return error.emit()

    date = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(dt.timezone.utc).date()
    day = DAY_NAMES[date.weekday()]
    due, idle = _collect_schedule(args.repo, library, date=date, day=day)
    payload = json.dumps(
        {"date": date.isoformat(), "weekday": day, "due": due, "idle": idle},
        indent=2,
    )
    sys.stdout.write(f"{payload}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
