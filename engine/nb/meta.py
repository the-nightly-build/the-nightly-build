"""Shared readers and grammar for the published library.

check.py, build_site.py, duty.py, and the CI helpers all read the same
published state: each article's nb-meta block, the series directories under
a library checkout, and the press's configured series. Keeping the
recognition contract, the directory layout, and the identifier grammar here
is the single source of truth, so the proof validates exactly the block the
builder renders and duty schedules against, the validator approves only ids
the 2am proof will accept, and every module agrees on where a series lives.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

# The identifier grammar and the article-bundle PR shape built from it.
# validate_config approves against these, the proof enforces them, and
# ci_helpers derives the render probe's target with them — one definition or
# they drift apart.
SERIES_RE = re.compile(r"^[a-z0-9-]{1,32}$")
SLUG_RE = re.compile(r"^[a-z0-9-]{1,64}$")
TAG_RE = re.compile(r"^[a-z0-9-]{1,32}(?:/[a-z0-9-]{1,32})*$")
PR_PATH_RE = re.compile(r"^library/([a-z0-9-]{1,32})/([a-z0-9-]{1,64})\.html$")
AGENT_ARTIFACT_RE = re.compile(r"^agent-artifacts/([a-z0-9-]{1,32})/([a-z0-9-]{1,64})/[^/].*$")
REVISION_NOTE_RE = re.compile(
    r"^agent-artifacts/([a-z0-9-]{1,32})/([a-z0-9-]{1,64})/"
    r"revisions/((?:0[1-9]|[1-9][0-9]))\.md$"
)
# Images, plus a chart's committed provenance (chart-N.py and its data).
# The provenance files are inert bundle data: the engine and CI never
# execute them, and the article sandbox cannot reference them.
ARTICLE_ASSET_RE = re.compile(
    r"^library/([a-z0-9-]{1,32})/([a-z0-9-]{1,64})/"
    r"(?:[a-z0-9][a-z0-9._-]*\.(?:png|jpe?g|webp)"
    r"|chart-\d+\.(?:py|csv|json))$"
)
MODES = ("collection", "sequence", "rolling", "open")

__all__ = (
    "AGENT_ARTIFACT_RE",
    "ARTICLE_ASSET_RE",
    "META_RE",
    "MODES",
    "PR_PATH_RE",
    "REVISION_NOTE_RE",
    "SERIES_RE",
    "SLUG_RE",
    "TAG_RE",
    "article_bundle_path",
    "is_meta_script",
    "is_safe_tag",
    "parse_meta",
    "read_meta",
    "revision_bundle_path",
    "series_dir",
    "series_ids",
)


def is_safe_tag(tag: str) -> bool:
    """Return whether a tag is safe as a nested static-site path.

    Tags use one or more lowercase slug segments separated by single slashes.
    The grammar excludes empty segments, traversal markers, backslashes, and
    absolute paths before a builder ever joins the value to its output root.
    """
    return isinstance(tag, str) and bool(TAG_RE.fullmatch(tag))


# The one nb-meta block every consumer honors: a typed
# <script type="application/json" id="nb-meta">. Requiring the type (in any
# attribute order) means an untyped decoy the proof cannot see is invisible to
# the builder and duty too, instead of overriding the shipped metadata.
META_RE = re.compile(
    r'<script\b(?=[^>]*\btype="application/json")(?=[^>]*\bid="nb-meta")'
    r"[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)


def is_meta_script(attrs: Mapping[str, object]) -> bool:
    raw_type = attrs.get("type")
    return isinstance(raw_type, str) and raw_type.strip().lower() == "application/json" and attrs.get("id") == "nb-meta"


def parse_meta(source: str) -> dict[str, object] | None:
    """Read the first typed nb-meta object from article source text.

    Return ``None`` when no recognized block exists, its JSON is invalid, or
    the decoded value is not an object. Field-level validation belongs to the
    proof; this shared reader only establishes the object boundary used by
    scheduling, building, PR identity checks, and file-backed ``read_meta``.
    """
    m = META_RE.search(source)
    if not m:
        return None
    try:
        meta = json.loads(m.group(1))
    except ValueError:
        return None
    return meta if isinstance(meta, dict) else None


def read_meta(path: str | pathlib.Path) -> dict[str, object] | None:
    return parse_meta(pathlib.Path(path).read_text(encoding="utf-8", errors="replace"))


def series_dir(library: str | pathlib.Path, series_id: str) -> str | None:
    library_path = pathlib.Path(library)
    for base in (
        library_path / "library" / series_id,
        library_path / series_id,
    ):
        if base.is_dir():
            return str(base)
    return None


def article_bundle_path(changes: list[tuple[str, str]], *, status: str = "A") -> str | None:
    """Return the one article a content diff adds or retracts, if isolated.

    An article bundle keeps the canonical article at ``<slug>.html`` and any
    captured figures directly under the matching ``<slug>/`` directory. No
    other path or status belongs in a nightly content PR.
    """
    articles = [path for state, path in changes if state == status and PR_PATH_RE.match(path)]
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
        artifact = AGENT_ARTIFACT_RE.match(path)
        if (asset is None or asset.groups() != (series_id, slug)) and (
            artifact is None or artifact.groups() != (series_id, slug)
        ):
            return None
    return article


def _revision_entry(state: str, path: str) -> tuple[tuple[str, str], bool] | None:
    article = PR_PATH_RE.match(path)
    if article is not None:
        return ((article.group(1), article.group(2)), True) if state == "M" else None
    asset = ARTICLE_ASSET_RE.match(path)
    if asset is not None:
        return ((asset.group(1), asset.group(2)), True) if state in ("A", "M", "D") else None
    note = REVISION_NOTE_RE.match(path)
    if note is not None:
        return ((note.group(1), note.group(2)), False) if state == "A" else None
    return None


def revision_bundle_path(changes: list[tuple[str, str]]) -> str | None:
    """Return the article identified by an isolated revision diff.

    A revision changes one published HTML file and/or its matching assets, and
    may only add matching numbered revision notes. Content and note validation
    happen after this path-level classification succeeds.
    """
    identities: set[tuple[str, str]] = set()
    content_changed = False
    for state, path in changes:
        entry = _revision_entry(state, path)
        if entry is None:
            return None
        identity, is_content = entry
        identities.add(identity)
        content_changed = content_changed or is_content
    if not content_changed or len(identities) != 1:
        return None
    series_id, slug = identities.pop()
    return f"library/{series_id}/{slug}.html"


def series_ids(repo: str | pathlib.Path) -> list[str]:
    """Return every configured series id, sorted.

    A ``_``-prefixed folder is a shared fragment home (``press/series/_tags``),
    never a series; a folder without a ``series.yaml`` is ignored here, and
    ``validate_config`` is where authors hear about it.
    """
    root = pathlib.Path(repo) / "press" / "series"
    if not root.is_dir():
        return []
    return sorted(
        entry.name for entry in root.iterdir() if not entry.name.startswith("_") and (entry / "series.yaml").is_file()
    )
