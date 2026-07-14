#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Build the static site from a library checkout: the press.

Every page shares one 800px content column and the shared assets under
engine/assets, so a stylesheet or theme change restyles the entire back
catalog on the next build. Article copies get content-hash stamped asset
links; the canonical files on the library branch stay byte-exact.

Output layout:

    site/
      index.html                       tonight's build
      builds/<YYYY-MM-DD>/             one page per night, linked prev/next
      builds/index.html                all nights
      series/index.html                the Sections page
      series/<id>/index.html           per-series pages, mode-aware
      tags/<tag>/index.html            tag pages
      search/index.html                client-side fuzzy search
      search-index.json                full-text index for the search page
      catalog.json                     machine-readable library state
      feed.xml, series/<id>/feed.xml   Atom; newest entries carry full content
      assets/                          copied from main's engine/assets
      library/<series>/<slug>.html     articles, asset links stamped

Invocations:

    Publish:      build_site.py --repo <main> --library <library checkout> --out site
    Press check:  build_site.py --repo . --preview press-check/ --out press-check/site/

Implementer decisions: feeds are Atom and the newest FEED_CONTENT_LIMIT
entries embed full content; builds/ groups strictly by nb-meta date, so a
late merge lands under its authored date; reading time falls back to
max(1, round(words / 230)); appearance persists under the localStorage key
"nb-appearance".

The build itself lives in nb/site/; this file is the door it opens by.
"""

import argparse
import datetime as dt
import os
import sys

from nb.site import build
from nb.site.assets import dress_article, template_dirs
from nb.site.catalog import (
    DIRECTORY_URL,
    UPSTREAM_REPOSITORY,
    derive_self_repository,
    is_safe_tag,
)
from nb.site.feeds import atom_feed
from nb.site.library import date_sort_key, read_meta
from nb.site.pages import render_assets_html, story_item

# `import build_site` is how the suite and validate_config.py reach the press.
# These names are that surface; the code behind them is in nb/site/.
__all__ = [
    "DIRECTORY_URL",
    "UPSTREAM_REPOSITORY",
    "atom_feed",
    "build",
    "date_sort_key",
    "derive_self_repository",
    "dress_article",
    "is_safe_tag",
    "main",
    "read_meta",
    "render_assets_html",
    "story_item",
    "template_dirs",
]


def main(argv=None):
    p = argparse.ArgumentParser(description="The Nightly Build site builder")
    p.add_argument(
        "--repo",
        default=".",
        help="main checkout (engine, templates, series, site.yaml)",
    )
    p.add_argument(
        "--library", default=".", help="library checkout (published articles)"
    )
    p.add_argument("--out", default="site", help="output directory")
    p.add_argument(
        "--preview",
        help="press-check dir; its library/ drafts are merged in",
    )
    p.add_argument(
        "--base-url",
        default="",
        help="absolute site base URL (no trailing slash) for feeds",
    )
    p.add_argument(
        "--repository",
        default=os.getenv("GITHUB_REPOSITORY"),
        help="this press's owner/repo (defaults to $GITHUB_REPOSITORY) for the "
        "'star this press' chrome link; falls back to parsing the Pages URL",
    )
    p.add_argument("--now", help="override the build timestamp (tests), ISO-8601 UTC")
    args = p.parse_args(argv)

    now = None
    if args.now:
        now = dt.datetime.fromisoformat(args.now)
        if now.tzinfo is None:
            now = now.replace(tzinfo=dt.timezone.utc)

    catalog = build(
        args.repo,
        args.library,
        out=args.out,
        preview_root=args.preview,
        base_url=args.base_url.rstrip("/"),
        repository=args.repository,
        now=now,
    )
    n = len(catalog["articles"])
    print(
        f"site built: {args.out} ({n} article{'s' if n != 1 else ''}, "
        f"{len(catalog['builds'])} builds)"
    )
    if args.preview:
        print(f"press check preview — serve with: python3 -m http.server -d {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
