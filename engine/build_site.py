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
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys

from nb.site.catalog import (
    DIRECTORY_URL,
    UPSTREAM_REPOSITORY,
    build_catalog,
    derive_self_repository,
    is_safe_tag,
)
from nb.site.feeds import atom_feed
from nb.site.library import (
    by_date_and_slug,
    collect_articles,
    date_sort_key,
    load_series_configs,
    load_site_config,
    night_date,
    read_meta,
)
from nb.site.pages import (
    build_search_index,
    chrome_footer,
    chrome_header,
    render_assets_html,
    render_build_archive,
    render_build_page,
    render_newsstand,
    render_search_page,
    render_series_index,
    render_series_page,
    render_tag_page,
    render_tags_index,
    story_item,
)

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


def asset_stamp(repo, css_paths=()):
    """Return a short content hash of the shared assets for cache busting.

    Every generated page and article copy links assets with ?v=<stamp>,
    so a returning reader can never pair cached old CSS with newer markup.
    The stamp folds in nb.css, nb.js, and every CSS owner concatenated
    into assets/theme.css (the configured theme plus all furniture, shared
    and template-scoped). copy_assets rebuilds theme.css from those owners
    every build, so editing any of them busts the reader's cache and the
    new look actually reaches them.
    """
    h = hashlib.md5()
    base = os.path.join(repo, "engine", "assets")
    paths = [os.path.join(base, "nb.css"), os.path.join(base, "nb.js"), *css_paths]
    for path in paths:
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:10]


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def template_dirs(repo):
    """Map each template id to its resolved folder, press shadowing shipped.

    A template is a folder holding a manifest.yaml (the folder name is the
    id); a press/templates/<id> package replaces a shipped one of the same
    id wholesale. A folder without a manifest.yaml is not a template and is
    skipped, so a stray asset left beside the packages is ignored.
    """
    dirs = {}
    for base in (
        os.path.join(repo, "templates"),
        os.path.join(repo, "press", "templates"),  # press shadows shipped
    ):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if os.path.isfile(os.path.join(folder, "manifest.yaml")):
                dirs[name] = folder
    return dirs


def css_owners(repo, site_cfg):
    """Every CSS file concatenated into the published assets/theme.css.

    Deterministically ordered so the cascade is stable and a later owner
    can lean on tokens an earlier one defines: the site theme first, then
    the shared press furniture, then each template's bespoke furniture in
    id order. Missing optional files are filtered out.
    """
    owners = [os.path.join(repo, site_cfg["theme"])]
    owners.append(os.path.join(repo, "press", "furniture", "styles.css"))
    for _id, folder in sorted(template_dirs(repo).items()):
        owners.append(os.path.join(folder, "furniture.css"))
    return [path for path in owners if os.path.isfile(path)]


def copy_assets(repo, site_cfg, *, out):
    src = os.path.join(repo, "engine", "assets")
    dst = os.path.join(out, "assets")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    # Every CSS owner is concatenated under the stable name assets/theme.css:
    # the configured theme plus all furniture (shared and template-scoped). The
    # output name never changes, so page links and article copies need no edit,
    # and a theme or furniture change restyles every already-published article.
    blocks = []
    for path in css_owners(repo, site_cfg):
        with open(path, encoding="utf-8") as fh:
            blocks.append(
                f"/* --- {os.path.basename(path)} --- */\n{fh.read().rstrip()}"
            )
    write(os.path.join(dst, "theme.css"), "\n\n".join(blocks) + "\n")


ARTICLE_ASSET_RE = re.compile(
    r'((?:href|src)="(?:\.\./)*assets/(?:nb\.css|nb\.js|theme\.css))(")'
)
BODY_OPEN_RE = re.compile(r"<body\b[^>]*>", re.IGNORECASE)

# Site copies of articles live at library/<series>/<slug>.html.
ARTICLE_DEPTH = 2


def dress_article(raw, site):
    """Return the article markup with the site chrome and press assets in place.

    An article is authored as a standalone page, so the bar and footer that
    generated pages get from page() are spliced in here, at copy time: the same
    Python builds both, and the whole back catalogue wears the current chrome on
    the next build. Idempotent, so an article that already carries a bar (an
    already-dressed copy handed back in) is left with exactly one.
    """
    if site["assets_html"]:
        raw = raw.replace("</head>", f"{site['assets_html']}\n</head>", 1)
    body_open = BODY_OPEN_RE.search(raw)
    if not body_open or 'class="nb-bar"' in raw:
        return raw
    header = chrome_header(site, depth=ARTICLE_DEPTH)
    at = body_open.end()
    raw = f"{raw[:at]}\n{header}{raw[at:]}"
    return raw.replace("</body>", f"{chrome_footer(site)}\n</body>", 1)


def copy_articles(articles, out, *, site):
    """Copy articles into the site, stamping their shared-asset links and
    dressing each copy in the site chrome.

    The canonical files on the library branch stay byte-exact; only the
    generated site copy gets ?v=<stamp> on nb.css, nb.js, and theme.css so
    cached assets can never mismatch the markup, the press assets so
    library-backed furniture (a highlighter, say) works in every article, and
    the reader chrome so an article is a page of this paper.
    """
    for ed in articles.values():
        dst = os.path.join(out, "library", ed["series"], f"{ed['slug']}.html")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(ed["file"], encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        if site["stamp"]:
            raw = ARTICLE_ASSET_RE.sub(rf"\1?v={site['stamp']}\2", raw)
        write(dst, dress_article(raw, site))


def build(
    repo,
    library_root,
    *,
    out,
    preview_root=None,
    base_url="",
    repository=None,
    now=None,
) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    site_cfg = load_site_config(repo)
    series_cfgs = load_series_configs(repo)
    articles = collect_articles(series_cfgs, library_root, preview_root=preview_root)
    repository = derive_self_repository(repository, base_url)
    # One pass groups the library both ways; every per-night and per-series
    # consumer below reuses these instead of rescanning all articles per key.
    by_series, by_night = {}, {}
    for ed in articles.values():
        by_series.setdefault(ed["series"], []).append(ed)
        by_night.setdefault(night_date(ed["meta"]), []).append(ed)
    catalog = build_catalog(
        site_cfg,
        series_cfgs,
        articles=articles,
        by_series=by_series,
        generated=now,
        repository=repository,
    )

    site = {
        "title": site_cfg["title"],
        "appearance": site_cfg["appearance"],
        "stamp": asset_stamp(repo, css_owners(repo, site_cfg)),
        "assets_html": render_assets_html(site_cfg.get("assets")),
        "footer": site_cfg.get("footer"),
        "repository": repository,
        "upstream": UPSTREAM_REPOSITORY,
        "body_class": (
            ' class="nb-front-comfortable"'
            if site_cfg.get("front") == "comfortable"
            else ""
        ),
    }

    os.makedirs(out, exist_ok=True)
    write(os.path.join(out, "catalog.json"), json.dumps(catalog, indent=2) + "\n")
    write(
        os.path.join(out, "index.html"),
        render_newsstand(
            site, catalog, series_cfgs=series_cfgs, articles=articles, by_night=by_night
        ),
    )
    write(
        os.path.join(out, "builds", "index.html"),
        render_build_archive(site, list(catalog["builds"])),
    )
    ordered = sorted(catalog["builds"], key=date_sort_key)
    for i, date in enumerate(ordered):
        write(
            os.path.join(out, "builds", date, "index.html"),
            render_build_page(
                site,
                date,
                ordered=ordered,
                i=i,
                eds=by_night.get(date, []),
                series_cfgs=series_cfgs,
            ),
        )
    write(
        os.path.join(out, "series", "index.html"),
        render_series_index(site, catalog, series_cfgs=series_cfgs, articles=articles),
    )
    for s in catalog["series"]:
        sid = s["id"]
        write(
            os.path.join(out, "series", sid, "index.html"),
            render_series_page(
                site,
                sid,
                cfg=series_cfgs.get(sid, {}),
                eds=by_series.get(sid, []),
                series_cfgs=series_cfgs,
            ),
        )
    write(os.path.join(out, "search", "index.html"), render_search_page(site))
    write(
        os.path.join(out, "search-index.json"),
        json.dumps(build_search_index(articles, series_cfgs)) + "\n",
    )
    write(os.path.join(out, "tags", "index.html"), render_tags_index(site, catalog))
    for tag, refs in catalog["tags"].items():
        write(
            os.path.join(out, "tags", tag, "index.html"),
            render_tag_page(
                site, tag, refs=refs, articles=articles, series_cfgs=series_cfgs
            ),
        )

    all_sorted = sorted(
        articles.values(),
        key=by_date_and_slug,
        reverse=True,
    )
    write(
        os.path.join(out, "feed.xml"),
        atom_feed(
            base_url,
            "feed.xml",
            title=site_cfg["title"],
            eds=all_sorted,
            generated=now,
            author=site_cfg["title"],
        ),
    )
    for s in catalog["series"]:
        sid = s["id"]
        eds = sorted(
            by_series.get(sid, []),
            key=by_date_and_slug,
            reverse=True,
        )
        write(
            os.path.join(out, "series", sid, "feed.xml"),
            atom_feed(
                base_url,
                f"series/{sid}/feed.xml",
                title=f"{site_cfg['title']} · {s['name']}",
                eds=eds,
                generated=now,
                author=site_cfg["title"],
            ),
        )

    copy_assets(repo, site_cfg, out=out)
    copy_articles(articles, out, site=site)
    return catalog


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
