"""What the press and the library hold: config, articles, and their order.

Everything the builder renders starts here. A published article is an HTML
file under library/<series>/<slug>.html carrying an nb-meta block; a series
is a folder under press/series. This module turns that on-disk state into
the article dicts every renderer reads, and nothing here emits markup.
"""

from __future__ import annotations

import html
import pathlib
import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

from nb import meta as nb_meta

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

try:
    import yaml
except ImportError:
    sys.stderr.write("build_site.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

WORDS_PER_MINUTE = 230

NO_DATE = "unknown"

__all__ = (
    "article_body_html",
    "article_text",
    "assign_positions",
    "by_date_and_slug",
    "collect_articles",
    "date_sort_key",
    "load_series_configs",
    "load_site_config",
    "load_yaml",
    "night_date",
    "reading_minutes",
    "scan_library",
)


def night_date(meta: Mapping[str, object]) -> str:
    """Return the build-date bucket for an article.

    Uses the article's nb-meta date, or the NO_DATE sentinel when the date is
    absent. build_catalog and every renderer bucket and filter on this one
    value, so a dateless article lands in exactly one night instead of being
    lost between a `None` date and an `"unknown"` bucket.
    """
    date = meta.get("date")
    return date if isinstance(date, str) and date else NO_DATE


def date_sort_key(date: str) -> str:
    return "" if date == NO_DATE else date  # dateless sorts first, never wins "latest"


def by_date_and_slug(ed: dict) -> tuple[str, str]:
    return (ed["meta"].get("date", ""), ed["slug"])


def load_yaml(path: str | pathlib.Path) -> dict:
    with pathlib.Path(path).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_site_config(repo: str | pathlib.Path) -> dict:
    cfg: dict = {}
    path = pathlib.Path(repo) / "press" / "site.yaml"
    if path.is_file():
        cfg = load_yaml(path)
    cfg.setdefault("title", "The Nightly Build")
    cfg.setdefault("theme", "engine/assets/themes/newspaper.css")
    cfg.setdefault("appearance", "auto")
    cfg.setdefault("front", "compact")
    return cfg


def load_series_configs(repo: str | pathlib.Path) -> dict[str, dict]:
    repo_path = pathlib.Path(repo)
    return {
        sid: load_yaml(repo_path / "press" / "series" / sid / "series.yaml")
        for sid in nb_meta.series_ids(str(repo_path))
    }


read_meta = nb_meta.read_meta


def scan_library(root: str | pathlib.Path) -> Iterator[tuple[str, str, str]]:
    """Yield (series_id, slug, file_path) for every article under root.

    Accepts a library checkout (contains library/) or a bare library folder
    (itself named 'library') — never an arbitrary directory, or a repo
    checkout's templates/ would be ingested as a series.
    """
    root_path = pathlib.Path(root)
    lib = root_path / "library"
    if lib.is_dir():
        base = lib
    elif root_path.name == "library":
        base = root_path
    else:
        return
    for entry in sorted(base.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        for html_file in sorted(entry.iterdir(), key=lambda p: p.name):
            if html_file.suffix == ".html":
                yield entry.name, html_file.stem, str(html_file)


_TOUCHED_PATH_RE = re.compile(r"^library/([a-z0-9-]+)/([a-z0-9-]+)(?:\.html$|/)")


def _last_touched_dates(
    library_root: str | pathlib.Path,
) -> dict[tuple[str, str], str]:
    """Map (series, slug) to the timestamp of the last commit touching the article.

    Tracks both the article HTML and its assets so a revision merge moves the
    feed's `updated`. Returns {} without full git history: a plain directory
    or a shallow checkout (where the grafted boundary commit misattributes
    every file to one date). The build stays a pure function of the tree in
    those cases.
    """
    git_bin = shutil.which("git")
    if git_bin is None:
        return {}
    shallow = subprocess.run(
        [git_bin, "-C", str(library_root), "rev-parse", "--is-shallow-repository"],
        capture_output=True,
        text=True,
        check=False,
    )
    if shallow.returncode != 0 or shallow.stdout.strip() != "false":
        return {}
    log = subprocess.run(
        [
            git_bin,
            "-C",
            str(library_root),
            "log",
            "--format=%x01%cI",
            "--name-only",
            "--",
            "library/",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if log.returncode != 0:
        return {}
    dates: dict[tuple[str, str], str] = {}
    stamp = None
    for line in log.stdout.splitlines():
        if line.startswith("\x01"):
            stamp = line[1:]
        elif line and stamp:
            m = _TOUCHED_PATH_RE.match(line)
            if m:  # newest-first log: the first date seen is the last touch
                dates.setdefault((m.group(1), m.group(2)), stamp)
    return dates


def reading_minutes(meta: Mapping[str, object]) -> int:
    rm = meta.get("reading_minutes")
    if isinstance(rm, (int, float)) and not isinstance(rm, bool) and rm > 0:
        return round(rm)
    words = meta.get("words")
    return (
        max(1, round(words / WORDS_PER_MINUTE))
        if isinstance(words, (int, float)) and not isinstance(words, bool) and words
        else 1
    )


def collect_articles(
    series_cfgs: Mapping[str, dict],
    library_root: str | pathlib.Path | None,
    *,
    preview_root: str | pathlib.Path | None = None,
) -> dict[tuple[str, str], dict]:
    """Load every article under the library root, preview drafts included.

    Returns {(series_id, slug): article dict} where each dict carries the
    parsed nb-meta, the source file path, reading minutes, and a draft
    flag. A preview draft with the same (series, slug) as a published
    article replaces it, which is how press-check promotion previews work.
    """
    articles: dict[tuple[str, str], dict] = {}
    revised = _last_touched_dates(library_root) if library_root else {}
    sources: list[tuple[str | pathlib.Path | None, bool]] = [(library_root, False)]
    if preview_root:
        sources.append((preview_root, True))
    for root, is_draft in sources:
        if not root:
            continue
        for sid, slug, path in scan_library(root):
            meta = read_meta(path)
            if meta is None:
                sys.stderr.write(f"warning: skipping {path} (no parseable nb-meta)\n")
                continue
            articles[(sid, slug)] = {
                "meta": meta,
                "series": sid,
                "slug": slug,
                "file": path,
                "draft": is_draft,
                "reading_minutes": reading_minutes(meta),
                "revised": None if is_draft else revised.get((sid, slug)),
            }
    assign_positions(articles, series_cfgs)
    return articles


def assign_positions(articles: Mapping[tuple[str, str], dict], series_cfgs: Mapping[str, dict]) -> None:
    """Assign each article its 1-based position in the series' canonical order.

    Sequences order by nb-meta order, collections by config item order
    with unknown slugs last, open series by publication date, rolling
    series by their date slugs. The position feeds catalog.json and the
    'Ed. N of M' labels, so it must be stable across rebuilds.
    """
    by_series: dict[str, list[dict]] = {}
    for ed in articles.values():
        by_series.setdefault(ed["series"], []).append(ed)
    for sid, eds in by_series.items():
        cfg = series_cfgs.get(sid, {})
        mode = cfg.get("mode") or eds[0]["meta"].get("mode", "collection")
        if mode == "sequence":
            eds.sort(key=lambda e: (e["meta"].get("order") or 10**6, e["slug"]))
        elif mode == "collection":
            order = {it.get("slug"): i for i, it in enumerate(cfg.get("items") or [])}
            eds.sort(key=lambda e: (order.get(e["slug"], 10**6), e["slug"]))
        elif mode == "open":  # topical slugs; publication date is the order
            eds.sort(key=by_date_and_slug)
        else:  # rolling
            eds.sort(key=lambda e: e["slug"])
        for i, ed in enumerate(eds, 1):
            ed["position"] = i


TEXT_STRIP_RE = re.compile(
    r"<!--[\s\S]*?-->|<script[\s\S]*?</script>|<style[\s\S]*?</style>"
    r"|<[^>]+>",
    re.IGNORECASE,
)
BODY_RE = re.compile(r"<body[^>]*>([\s\S]*?)</body>", re.IGNORECASE)


def article_body_html(path: str | pathlib.Path) -> str:
    raw = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    m = BODY_RE.search(raw)
    return m.group(1) if m else raw


def article_text(path: str | pathlib.Path) -> str:
    text = TEXT_STRIP_RE.sub(" ", article_body_html(path))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()
