"""Shared readers for the published library.

check.py, build_site.py, and duty.py all read the same published state: each
article's nb-meta block and the series directories under a library checkout.
Keeping the recognition contract and the directory layout here is the single
source of truth, so the proof validates exactly the block the builder renders
and duty schedules against, and all three agree on where a series lives.
"""

import json
import os
import re

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
    """Whether a parsed <script>'s attributes mark it as the nb-meta block.

    check.py's single-pass HTML parse recognizes the block by the same
    contract this module's regex encodes: type application/json and id nb-meta.
    """
    return (
        attrs.get("type") or ""
    ).strip().lower() == "application/json" and attrs.get("id") == "nb-meta"


def read_meta(path: str) -> dict | None:
    """Parse the typed nb-meta block from an article file, or None.

    Returns None when the file has no typed block, its JSON is invalid, or it
    does not parse to an object.
    """
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
    """The on-disk directory for a series inside a library checkout, or None.

    Accepts a full library checkout (contains library/<series>/) or a bare
    library folder (<series>/ directly), returning the first that exists.
    """
    for base in (
        os.path.join(library, "library", series_id),
        os.path.join(library, series_id),
    ):
        if os.path.isdir(base):
            return base
    return None
