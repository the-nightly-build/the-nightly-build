#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Compute tonight's work list deterministically from config and library state.

The correspondent runs this before researching anything. It is the single
source of truth for cadence, pauses, completion, commission queues, and
rerun safety, so no agent ever does calendar math on its own.

Because it runs first, it is also where a stale checkout is caught. A night
shift handed a cached workspace reads a press that no longer exists and
writes a confident, internally consistent, entirely wrong edition: every
article cites retired series, every local proof passes, and CI blocks all of
it (this happened on 2026-07-14). So duty refuses to compute a work list from
a tree that is behind origin/main, and says how to fix it.

Run: python3 engine/duty.py --repo . --library <library-checkout> [--date YYYY-MM-DD]
Prints JSON: {"date", "weekday", "due": [...], "idle": [...]}. Exits 0, except
2 when the checkout is stale (--allow-stale skips the check, for offline work).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys

import nb_meta

try:
    import yaml
except ImportError:
    sys.stderr.write("duty.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
CADENCE_WORDS = ("daily", "weekdays", "weekends")


def cadence_is_valid(cadence) -> bool:
    """The strict author-time twin of cadence_includes: validate_config asks
    this, while the fail-open evaluation below never skips work over a value
    validation would have flagged. Keeping both here means the vocabulary
    cannot drift between the validator and the scheduler."""
    if isinstance(cadence, str):
        return cadence in CADENCE_WORDS
    return (
        isinstance(cadence, list)
        and len(cadence) > 0
        and all(d in DAY_NAMES for d in cadence)
    )


def cadence_includes(cadence, day: str) -> bool:
    if cadence in (None, "daily"):
        return True
    if cadence == "weekdays":
        return day not in ("sat", "sun")
    if cadence == "weekends":
        return day in ("sat", "sun")
    if isinstance(cadence, list):
        days = [str(d).lower() for d in cadence]
        if not any(d in DAY_NAMES for d in days):
            return True  # no recognized day name: fail open, like an unknown scalar
        return day in days
    return True  # unknown value: validate_config flags it; never skip work here


def published_state(library: str, series_id: str) -> tuple[set[str], set[str]]:
    """Return (published slugs, published nb-meta dates) for one series.

    Slugs drive dedupe and completion checks. The nb-meta dates exist
    for rerun safety: an article published tonight idles its series even
    when its slug is topical rather than dated.
    """
    base = nb_meta.series_dir(library, series_id)
    if base is None:
        return set(), set()
    slugs, dates = set(), set()
    for fname in os.listdir(base):
        if not fname.endswith(".html"):
            continue
        slugs.add(fname[:-5])
        meta = nb_meta.read_meta(os.path.join(base, fname))
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


def series_duty(
    sid: str,
    cfg: dict[str, object],
    *,
    pub: set[str],
    pub_dates: set[str],
    date: _dt.date,
    day: str,
) -> tuple[bool, dict[str, object]]:
    """Decide whether one series publishes tonight, and why.

    Returns (is_due, entry). The entry always names the series and mode,
    then either a reason for sitting out (paused, off-cadence, already
    published tonight, complete) or what to publish: a slug for sequence
    and rolling, candidates for collection (all remaining items under
    selection: random, otherwise just the next one), and commissions for
    open series with queued items. Gates apply in order: paused, then
    cadence, then already-published-tonight, so a paused series never
    reports a cadence excuse.
    """
    mode = cfg.get("mode")
    entry = {"series": sid, "mode": mode}

    if cfg.get("paused"):
        return False, {**entry, "reason": "paused"}
    cadence = cfg.get("cadence")
    if not cadence_includes(cadence, day):
        return False, {**entry, "reason": f"cadence {cadence} — not tonight"}
    if date.isoformat() in pub_dates:
        return False, {**entry, "reason": "already published tonight"}

    items = config_items(cfg)
    unpublished = [it["slug"] for it in items if it.get("slug") not in pub]

    if mode == "rolling":
        slug = date.isoformat()
        if slug in pub:
            return False, {**entry, "reason": "already published tonight"}
        return True, {**entry, "slug": slug, "reason": "tonight's date is unpublished"}
    if mode == "sequence":
        if not unpublished:
            return False, {**entry, "reason": "complete"}
        nxt = unpublished[0]
        order = next(i for i, it in enumerate(items, 1) if it.get("slug") == nxt)
        return True, {
            **entry,
            "slug": nxt,
            "order": order,
            "reason": f"{len(items) - len(unpublished)} of {len(items)} "
            f"published; '{nxt}' is next",
        }
    if mode == "collection":
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
    if mode == "open":
        if unpublished:
            return True, {
                **entry,
                "commissions": unpublished,
                "reason": "commissioned items pending — publish "
                "one of these before an open pick",
            }
        return True, {
            **entry,
            "commissions": [],
            "reason": "open section — invent tonight's topic within "
            "the beat; do not repeat a published slug",
        }
    return False, {**entry, "reason": f"unknown mode {mode!r}"}


def git(repo, *args) -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", repo, *args], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def stale_checkout(repo) -> str | None:
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


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Tonight's deterministic work list")
    p.add_argument("--repo", default=".", help="repo root (main checkout)")
    p.add_argument(
        "--library", required=True, help="library-branch checkout (published state)"
    )
    p.add_argument("--date", default=None, help="UTC date, default today")
    p.add_argument(
        "--allow-stale",
        action="store_true",
        help="compute a work list even from a tree behind origin/main",
    )
    args = p.parse_args(argv)

    if not args.allow_stale:
        stale = stale_checkout(args.repo)
        if stale:
            sys.stderr.write(f"duty.py: {stale}\n")
            return 2

    date = (
        _dt.date.fromisoformat(args.date)
        if args.date
        else _dt.datetime.now(_dt.timezone.utc).date()
    )
    day = DAY_NAMES[date.weekday()]

    due, idle = [], []
    root = os.path.join(args.repo, "press", "series")
    for sid in nb_meta.series_ids(args.repo):
        try:
            with open(os.path.join(root, sid, "series.yaml"), encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh)
        except yaml.YAMLError:
            cfg = None
        if not isinstance(cfg, dict):
            # A bare string/list or unparseable series.yaml idles one series
            # with a reason; the run still exits 0 for every other series.
            idle.append(
                {"series": sid, "mode": None, "reason": "series.yaml is not a mapping"}
            )
            continue
        pub, pub_dates = published_state(args.library, sid)
        is_due, entry = series_duty(
            sid, cfg, pub=pub, pub_dates=pub_dates, date=date, day=day
        )
        (due if is_due else idle).append(entry)

    print(
        json.dumps(
            {"date": date.isoformat(), "weekday": day, "due": due, "idle": idle},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
