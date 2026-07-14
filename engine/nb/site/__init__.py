"""The press: one build, from a library checkout to a static site.

build() is the whole sequence — read the press and the library, derive the
catalog, render every page and feed, copy the assets and the articles. The
modules beside it each own one of those steps; build_site.py is the door.
"""

import datetime as dt
import json
import os

from nb.site.assets import asset_stamp, copy_articles, copy_assets, css_owners, write
from nb.site.catalog import UPSTREAM_REPOSITORY, build_catalog, derive_self_repository
from nb.site.feeds import atom_feed
from nb.site.library import (
    by_date_and_slug,
    collect_articles,
    date_sort_key,
    load_series_configs,
    load_site_config,
    night_date,
)
from nb.site.pages import (
    build_search_index,
    render_assets_html,
    render_build_archive,
    render_build_page,
    render_newsstand,
    render_search_page,
    render_series_index,
    render_series_page,
    render_tag_page,
    render_tags_index,
)


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
