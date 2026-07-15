"""Shared readers and grammar for the published library.

check.py, build_site.py, duty.py, and the CI helpers all read the same
published state: each article's nb-meta block, the series directories under
a library checkout, and the press's configured series. Keeping the
recognition contract, the directory layout, and the identifier grammar here
is the single source of truth, so the proof validates exactly the block the
builder renders and duty schedules against, the validator approves only ids
the 2am proof will accept, and every module agrees on where a series lives.
"""

import json
import os
import re

# The identifier grammar and the article-bundle PR shape built from it.
# validate_config approves against these, the proof enforces them, and
# ci_helpers derives the render probe's target with them — one definition or
# they drift apart.
SERIES_RE = re.compile(r"^[a-z0-9-]{1,32}$")
SLUG_RE = re.compile(r"^[a-z0-9-]{1,64}$")
PR_PATH_RE = re.compile(r"^library/([a-z0-9-]{1,32})/([a-z0-9-]{1,64})\.html$")
ARTICLE_ASSET_RE = re.compile(
    r"^library/([a-z0-9-]{1,32})/([a-z0-9-]{1,64})/"
    r"[a-z0-9][a-z0-9._-]*\.(?:png|jpe?g|webp)$"
)
MODES = ("collection", "sequence", "rolling", "open")

# The one nb-meta block every consumer honors: a typed
# <script type="application/json" id="nb-meta">. Requiring the type (in any
# attribute order) means an untyped decoy the proof cannot see is invisible to
# the builder and duty too, instead of overriding the shipped metadata.
META_RE = re.compile(
    r'<script\b(?=[^>]*\btype="application/json")(?=[^>]*\bid="nb-meta")'
    r"[^>]*>(.*?)</script>",
    re.S | re.I,
)


def is_meta_script(attrs: dict) -> bool:
    return (
        attrs.get("type") or ""
    ).strip().lower() == "application/json" and attrs.get("id") == "nb-meta"


def read_meta(path: str) -> dict | None:
    with open(path, encoding="utf-8", errors="replace") as fh:
        m = META_RE.search(fh.read())
    if not m:
        return None
    try:
        meta = json.loads(m.group(1))
    except ValueError:
        return None
    return meta if isinstance(meta, dict) else None


def series_dir(library: str, series_id: str) -> str | None:
    for base in (
        os.path.join(library, "library", series_id),
        os.path.join(library, series_id),
    ):
        if os.path.isdir(base):
            return base
    return None


def article_bundle_path(
    changes: list[tuple[str, str]], *, status: str = "A"
) -> str | None:
    """Return the one article a content diff adds or retracts, if isolated.

    An article bundle keeps the canonical article at ``<slug>.html`` and any
    captured figures directly under the matching ``<slug>/`` directory. No
    other path or status belongs in a nightly content PR.
    """
    articles = [
        path for state, path in changes if state == status and PR_PATH_RE.match(path)
    ]
    if len(articles) != 1 or len(changes) < 1:
        return None
    article = articles[0]
    match = PR_PATH_RE.match(article)
    if match is None:
        return None
    series_id, slug = match.groups()
    for state, path in changes:
        if state != status:
            return None
        if path == article:
            continue
        asset = ARTICLE_ASSET_RE.match(path)
        if asset is None or asset.groups() != (series_id, slug):
            return None
    return article


def series_ids(repo: str) -> list[str]:
    """Every configured series id, sorted. A `_`-prefixed folder is a shared
    fragment home (press/series/_tags), never a series; a folder without a
    series.yaml is ignored here, and validate_config is where authors hear
    about it."""
    root = os.path.join(repo, "press", "series")
    if not os.path.isdir(root):
        return []
    return sorted(
        sid
        for sid in os.listdir(root)
        if not sid.startswith("_")
        and os.path.isfile(os.path.join(root, sid, "series.yaml"))
    )
