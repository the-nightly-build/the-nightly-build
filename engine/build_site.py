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
import html
import json
import os
import re
import shutil
import sys

from nb import meta as nb_meta

try:
    import yaml
except ImportError:
    sys.stderr.write("build_site.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

PROTOCOL = "1.3"
WORDS_PER_MINUTE = 230
FEED_LIMIT = 50
FEED_CONTENT_LIMIT = 10  # newest N entries carry full content
FEED_CONTENT_MAX = 150_000  # per-entry cap after stripping, bytes
UPSTREAM_REPOSITORY = os.getenv(
    "UPSTREAM_REPOSITORY", "the-nightly-build/the-nightly-build"
)
DIRECTORY_URL = os.getenv("DIRECTORY_URL", "https://the-nightly-build.github.io/")
esc = html.escape

NO_DATE = "unknown"


def night_date(meta):
    """The build-date bucket for an article: its nb-meta date, or the
    NO_DATE sentinel when the date is absent. build_catalog and every
    renderer bucket and filter on this one value, so a dateless article
    lands in exactly one night instead of being lost between a `None`
    date and an `"unknown"` bucket.
    """
    return meta.get("date") or NO_DATE


def date_sort_key(date):
    return "" if date == NO_DATE else date  # dateless sorts first, never wins "latest"


def by_date_and_slug(ed):
    return (ed["meta"].get("date", ""), ed["slug"])


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def load_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_site_config(repo):
    cfg = {}
    path = os.path.join(repo, "press", "site.yaml")
    if os.path.isfile(path):
        cfg = load_yaml(path)
    cfg.setdefault("title", "The Nightly Build")
    cfg.setdefault("theme", "engine/assets/themes/newspaper.css")
    cfg.setdefault("appearance", "auto")
    cfg.setdefault("front", "compact")
    return cfg


def render_assets_html(assets):
    """Head tags for a press's declared trusted external assets.

    Presses may load popular libraries (a syntax highlighter, a math
    typesetter) to power their furniture. These are owner-authored in
    site.yaml on main (never an agent article), pinned and Subresource-
    Integrity-hashed, and validate_config requires the hash. The builder
    injects them into every generated page and article here, on the trusted
    post-merge path; articles themselves stay script-free, so the article
    sandbox is unchanged and auto-merge stays as safe as ever.
    """
    if not assets:
        return ""
    parts = []
    # Owner-authored assets must be https and Subresource-Integrity-pinned: the
    # integrity hash is what lets the browser refuse a tampered CDN response.
    for st in assets.get("styles") or []:
        parts.append(
            f'<link rel="stylesheet" href="{esc(st["url"])}" '
            f'integrity="{esc(st["integrity"])}" '
            'crossorigin="anonymous" referrerpolicy="no-referrer">'
        )
    for sc in assets.get("scripts") or []:
        defer = "" if sc.get("defer") is False else " defer"
        parts.append(
            f'<script src="{esc(sc["url"])}" '
            f'integrity="{esc(sc["integrity"])}" '
            f'crossorigin="anonymous" referrerpolicy="no-referrer"{defer}></script>'
        )
    return "\n".join(parts)


def load_series_configs(repo):
    return {
        sid: load_yaml(os.path.join(repo, "press", "series", sid, "series.yaml"))
        for sid in nb_meta.series_ids(repo)
    }


read_meta = nb_meta.read_meta


def scan_library(root):
    """Yield (series_id, slug, file_path) for every article under root.

    Accepts a library checkout (contains library/) or a bare library folder
    (itself named 'library') — never an arbitrary directory, or a repo
    checkout's templates/ would be ingested as a series.
    """
    lib = os.path.join(root, "library")
    if os.path.isdir(lib):
        base = lib
    elif os.path.basename(os.path.normpath(root)) == "library":
        base = root
    else:
        return
    for sid in sorted(os.listdir(base)):
        d = os.path.join(base, sid)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".html"):
                yield sid, f[:-5], os.path.join(d, f)


def reading_minutes(meta):
    rm = meta.get("reading_minutes")
    if isinstance(rm, (int, float)) and rm > 0:
        return int(round(rm))
    words = meta.get("words") or 0
    return max(1, round(words / WORDS_PER_MINUTE)) if words else 1


def collect_articles(
    series_cfgs, library_root, *, preview_root=None
) -> dict[tuple[str, str], dict]:
    """Load every article under the library root, preview drafts included.

    Returns {(series_id, slug): article dict} where each dict carries the
    parsed nb-meta, the source file path, reading minutes, and a draft
    flag. A preview draft with the same (series, slug) as a published
    article replaces it, which is how press-check promotion previews work.
    """
    articles = {}
    sources = [(library_root, False)]
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
            }
    assign_positions(articles, series_cfgs)
    return articles


def assign_positions(articles, series_cfgs):
    """Assign each article its 1-based position in the series' canonical order.

    Sequences order by nb-meta order, collections by config item order
    with unknown slugs last, open series by publication date, rolling
    series by their date slugs. The position feeds catalog.json and the
    'Ed. N of M' labels, so it must be stable across rebuilds.
    """
    by_series = {}
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


# --------------------------------------------------------------------------- #
# Catalog
# --------------------------------------------------------------------------- #


def derive_self_repository(explicit, base_url) -> str | None:
    if explicit:
        return explicit
    # Parse a Pages project URL https://<owner>.github.io/<repo>/; a user or org
    # Pages site has no repo path, so this yields None and chrome omits the star link.
    match = re.match(r"https?://([^./]+)\.github\.io/([^/]+)", base_url or "")
    return f"{match.group(1)}/{match.group(2)}" if match else None


def build_catalog(
    site_cfg, series_cfgs, *, articles, by_series, generated, repository=None
):
    series_entries = []
    for sid, cfg in series_cfgs.items():
        items = cfg.get("items") or []
        entry = {
            "id": sid,
            "name": cfg.get("name", sid),
            "mode": cfg.get("mode"),
            "template": cfg.get("template"),
            "count": len(by_series.get(sid, [])),
            "total": len(items)
            if cfg.get("mode") in ("collection", "sequence")
            else None,
        }
        for key in ("templates", "cadence", "paused", "section"):
            if cfg.get(key):
                entry[key] = cfg[key]
        series_entries.append(entry)
    # articles published for series no longer configured still belong to the site
    for sid in sorted(set(by_series) - set(series_cfgs)):
        eds = by_series[sid]
        series_entries.append(
            {
                "id": sid,
                "name": sid,
                "mode": eds[0]["meta"].get("mode"),
                "template": eds[0]["meta"].get("template"),
                "count": len(eds),
                "total": None,
            }
        )

    article_entries = []
    for ed in sorted(
        articles.values(),
        key=lambda e: (e["meta"].get("date", ""), e["series"], e["slug"]),
        reverse=True,
    ):
        entry = dict(ed["meta"])
        entry["path"] = f"/library/{ed['series']}/{ed['slug']}.html"
        entry["position"] = ed["position"]
        entry["reading_minutes"] = ed["reading_minutes"]
        if ed["draft"]:
            entry["draft"] = True
        article_entries.append(entry)

    builds = {}
    for ed in articles.values():
        d = night_date(ed["meta"])
        builds.setdefault(d, []).append(f"{ed['series']}/{ed['slug']}")
    builds = {
        d: sorted(v)
        for d, v in sorted(
            builds.items(), key=lambda kv: date_sort_key(kv[0]), reverse=True
        )
    }

    tags = {}
    for ed in articles.values():
        for t in ed["meta"].get("tags") or []:
            if not is_safe_tag(t):
                continue
            tags.setdefault(t, []).append(f"{ed['series']}/{ed['slug']}")
    tags = {t: sorted(v) for t, v in sorted(tags.items())}

    catalog = {
        "generated": generated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": PROTOCOL,
        "site_title": site_cfg["title"],
        "footer": site_cfg.get("footer"),
        "repository": repository,
        "upstream": UPSTREAM_REPOSITORY,
        "directory_url": DIRECTORY_URL,
        "series": series_entries,
        "articles": article_entries,
        "builds": builds,
        "tags": tags,
    }
    # Listing on the directory is opt-out: a paper is listed unless it sets
    # directory.publish: false. The block carries only that signal and an optional
    # description; the public URL is never in the catalog. The directory derives
    # each paper's URL from GitHub identity, so no catalog field can point a
    # reader off the paper's own site.
    directory = site_cfg.get("directory") or {}
    if directory.get("publish") is False:
        catalog["directory"] = {"publish": False}
    else:
        catalog["directory"] = {
            "publish": True,
            "description": (directory.get("description") or "").strip(),
        }
    return catalog


# --------------------------------------------------------------------------- #
# Page chrome
# --------------------------------------------------------------------------- #

FONTS = (
    "https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@"
    "0,6..72,400..700;1,6..72,400..700&family=Inter:wght@400;500;600&"
    "family=IBM+Plex+Mono:wght@400;500&display=swap"
)

APPEARANCE_BOOTSTRAP = (
    '<script>try{var m=localStorage.getItem("nb-appearance");'
    'if(m==="light"||m==="dark")document.documentElement.setAttribute("data-mode",m);'
    "}catch(e){}</script>"
)

NAV_ITEMS = [
    ("Today", ""),
    ("Sections", "series/"),
    ("Search", "search/"),
    ("RSS", "feed.xml"),
]


WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def pretty_date(iso):
    try:
        d = dt.date.fromisoformat(iso)
    except (ValueError, TypeError):
        return iso
    return f"{WEEKDAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}"


def month_label(iso, fallback):
    try:
        md = dt.date.fromisoformat(iso)
    except ValueError:
        return fallback
    return f"{MONTHS[md.month - 1]} {md.year}"


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


def chrome_eco_links(site):
    ext = 'target="_blank" rel="noopener noreferrer"'
    links = []
    if site.get("repository"):
        links.append(
            f'<a href="https://github.com/{site["repository"]}" {ext}>'
            f"Star on GitHub ↗</a>"
        )
    links.append(
        f'<a href="https://github.com/{site["upstream"]}" {ext}>Start your own ↗</a>'
    )
    links.append(f'<a href="{DIRECTORY_URL}" {ext}>The whole newspaper ↗</a>')
    return "".join(links)


def chrome_imprint(site):
    ext = 'target="_blank" rel="noopener noreferrer"'
    if site.get("footer"):
        return f'<span class="nb-imprint">{esc(site["footer"])}</span>'
    return (
        f'<a class="nb-imprint" href="https://github.com/{site["upstream"]}" {ext}>'
        f"A Nightly Build paper</a>"
    )


def chrome_header(site, *, depth=0, active=None):
    rel = "../" * depth
    nav_parts = []
    for label, href in NAV_ITEMS:
        current = ' aria-current="page"' if label == active else ""
        nav_parts.append(f'<a href="{rel + href}"{current}>{label}</a>')
    nav = "".join(nav_parts)
    eco = chrome_eco_links(site)
    return f"""<header class="nb-bar"><div class="nb-bar-in">
  <a class="nb-wordmark" href="{rel}">{esc(site["title"])}<span class="nb-period">.</span></a>
  <details class="nb-menu"><summary aria-label="Menu"><span class="nb-burger"></span></summary>
  <nav class="nb-menu-panel"><div class="nb-menu-nav">{nav}</div><div class="nb-menu-eco">{eco}</div></nav></details>
</div></header>"""


def chrome_footer(site):
    return f"""<footer class="nb-footer"><div class="nb-footer-in">
  {chrome_imprint(site)}
  <button class="nb-appearance" type="button">◐ auto</button>
</div></footer>"""


def page(site, title, *, body, depth=0, active=None):
    rel = "../" * depth
    mode_attr = (
        f' data-mode="{site["appearance"]}"'
        if site["appearance"] in ("light", "dark")
        else ""
    )
    press_assets = f"\n{site['assets_html']}" if site.get("assets_html") else ""
    return f"""<!DOCTYPE html>
<html lang="en"{mode_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="{rel}assets/theme.css?v={site["stamp"]}">
<link rel="stylesheet" href="{rel}assets/nb.css?v={site["stamp"]}">
<link rel="alternate" type="application/atom+xml" href="{rel}feed.xml" title="{esc(site["title"])}">
{APPEARANCE_BOOTSTRAP}
<script defer src="{rel}assets/nb.js?v={site["stamp"]}"></script>{press_assets}
</head>
<body{site["body_class"]}>
{chrome_header(site, depth=depth, active=active)}
<main class="nb-shell">
{body}
</main>
{chrome_footer(site)}
</body></html>"""


def kicker_text(ed, series_cfgs):
    cfg = series_cfgs.get(ed["series"], {})
    name = cfg.get("name", ed["series"])
    section = cfg.get("section")
    return f"{section} · {name}" if section else name


def source_label(meta):
    n = meta.get("sources")
    if not isinstance(n, int) or n <= 0:
        return ""
    return f"{n} source" if n == 1 else f"{n} sources"


def item_meta_row(ed):
    return (
        f'<div class="nb-meta"><span>{ed["reading_minutes"]} min read</span>'
        f"<span>{esc(source_label(ed['meta']))}</span></div>"
    )


def story_item(ed, series_cfgs, *, depth=0, lead=False):
    rel = "../" * depth
    dek = str(ed["meta"].get("dek", ""))
    if lead:
        cls, tag = " nb-lead-cell", "h2"
        dek_html = f'<p class="nb-dek">{esc(dek)}</p>'
    else:
        cls, tag = "", "h3"
        dek_html = f'<p class="nb-dek nb-cell-dek">{esc(dek)}</p>' if dek else ""
    return (
        f'<a class="nb-item{cls}" href="{rel}library/{esc(ed["series"])}/{esc(ed["slug"])}.html">'
        f'<div class="nb-kicker">{esc(kicker_text(ed, series_cfgs))}</div>'
        f"<{tag}>{esc(str(ed['meta'].get('title', ed['slug'])))}</{tag}>"
        f"{dek_html}{item_meta_row(ed)}</a>"
    )


def night_body(eds, series_cfgs, *, depth, date):
    """Render one night as an article line plus a single ruled table.

    The longest read leads as the table's full-width first cell and the
    rest of the night fills the two-column grid beneath it. Every visual
    separation on the page is a rule of this one table.
    """
    eds = sorted(eds, key=lambda e: -e["reading_minutes"])
    total = sum(e["reading_minutes"] for e in eds)
    body = (
        f'<div class="nb-articleline"><span>{esc(pretty_date(date))}</span>'
        f'<span class="nb-articleline-facts">{total} min read</span></div>'
    )
    cells = story_item(eds[0], series_cfgs, depth=depth, lead=True) + "".join(
        story_item(e, series_cfgs, depth=depth) for e in eds[1:]
    )
    return body + f'<div class="nb-grid">{cells}</div>'


def render_newsstand(site, catalog, *, series_cfgs, articles, by_night):
    if not articles:
        body = (
            '<div class="nb-empty" style="margin-top:26px">'
            "<h2>The presses are ready</h2>"
            "<p>Set up your first series — ask your agent to "
            "“set me up”, then run a press check.</p></div>"
        )
        return page(site, site["title"], body=body, active="Today")
    dates = sorted(catalog["builds"], key=date_sort_key)
    latest = dates[-1]
    tonight = by_night.get(latest, [])
    body = night_body(tonight, series_cfgs, depth=0, date=latest)
    if len(dates) > 1:
        prev = dates[-2]
        body += (
            f'<nav class="nb-nightnav"><a href="builds/{prev}/">'
            f"← {esc(pretty_date(prev))}</a></nav>"
        )
    return page(site, site["title"], body=body, active="Today")


def render_build_page(site, date, *, ordered, i, eds, series_cfgs):
    body = night_body(eds, series_cfgs, depth=2, date=date)
    prev_d = ordered[i - 1] if i > 0 else None
    next_d = ordered[i + 1] if i < len(ordered) - 1 else None
    left = (
        f'<a href="../{prev_d}/">← {esc(pretty_date(prev_d))}</a>'
        if prev_d
        else "<span></span>"
    )
    if next_d and next_d == ordered[-1]:
        right = f'<a href="../../">{esc(pretty_date(next_d))} →</a>'
    elif next_d:
        right = f'<a href="../{next_d}/">{esc(pretty_date(next_d))} →</a>'
    else:
        right = "<span></span>"
    body += f'<nav class="nb-nightnav">{left}{right}</nav>'
    return page(site, f"{pretty_date(date)} · {site['title']}", body=body, depth=2)


def render_build_archive(site, dates):
    body = (
        '<div class="nb-pagehead"><h1>All nights</h1>'
        f'<span class="nb-pagehead-facts">{len(dates)} builds</span></div>'
    )
    if not dates:
        body += '<div class="nb-empty"><p>No builds yet.</p></div>'
    seen_month = None
    for d in sorted(dates, key=date_sort_key, reverse=True):
        month = d[:7]
        if month != seen_month:
            body += f'<span class="nb-month-label">{esc(month_label(d, month))}</span>'
            seen_month = month
        body += (
            f'<div class="nb-list"><a class="nb-nightnav" '
            f'style="padding:8px 0" href="{d}/">{esc(pretty_date(d))}'
            f"</a></div>"
        )
    return page(site, f"All nights · {site['title']}", body=body, depth=1)


def series_status(s, cfg):
    """Return (status_html, is_resting) for one series on the Sections page.

    Finite series read complete once every configured item is published and
    otherwise report their published count; rolling series show their cadence.
    Resting series (complete or paused) collect under the In-the-stacks
    disclosure instead of their section.
    """
    mode, count, total = s.get("mode"), s["count"], s.get("total")
    if cfg.get("paused"):
        return "paused", True
    if mode in ("collection", "sequence"):
        if total and count >= total:
            return f"complete · {count} article{'s' if count != 1 else ''}", True
        return f"{count} published", False
    if mode == "rolling":
        cadence = cfg.get("cadence")
        return (esc(str(cadence)) if isinstance(cadence, str) else "nightly"), False
    return f"{count} published", False


def render_series_index(site, catalog, *, series_cfgs, articles):
    latest_by_series = {}
    for ed in articles.values():
        cur = latest_by_series.get(ed["series"])
        if cur is None or ed["meta"].get("date", "") > cur["meta"].get("date", ""):
            latest_by_series[ed["series"]] = ed

    groups, resting, nseries = {}, [], 0
    for s in catalog["series"]:
        cfg = series_cfgs.get(s["id"], {})
        status, rests = series_status(s, cfg)
        latest = latest_by_series.get(s["id"])
        latest_line = ""
        if latest:
            latest_line = (
                f'<span class="nb-series-latest">'
                f"{esc(str(latest['meta'].get('title', '')))} · "
                f"{esc(pretty_date(latest['meta'].get('date', '')))}"
                "</span>"
            )
        row = (
            f'<a class="nb-series{" nb-series-done" if rests else ""}" '
            f'href="{esc(s["id"])}/">'
            f'<span class="nb-series-name">{esc(s.get("name", s["id"]))}</span>'
            f"{latest_line}"
            f'<span class="nb-series-status">{status}</span></a>'
        )
        nseries += 1
        if rests:
            resting.append(row)
        else:
            groups.setdefault(cfg.get("section") or "Other", []).append(row)

    facts = (
        f"{max(len(groups), 1)} section{'s' if len(groups) != 1 else ''} · "
        f"{nseries} series · "
        f"{len(catalog['articles'])} article"
        f"{'s' if len(catalog['articles']) != 1 else ''}"
    )
    body = (
        '<div class="nb-pagehead"><h1>Sections</h1>'
        f'<span class="nb-pagehead-facts">{facts}</span></div>'
    )
    if not groups and not resting:
        body += '<div class="nb-empty"><p>No series configured.</p></div>'
    for section, rows in groups.items():
        body += (
            f'<div class="nb-secgroup"><div class="nb-sechead">'
            f"<h2>{esc(section)}</h2><span>{len(rows)} series</span></div>"
            f"{''.join(rows)}</div>"
        )
    if resting:
        body += (
            f'<details class="nb-stacks"><summary>In the stacks · '
            f"{len(resting)} series"
            f"</summary>{''.join(resting)}</details>"
        )
    return page(
        site, f"Sections · {site['title']}", body=body, depth=1, active="Sections"
    )


def series_head_html(name, *, mode, cfg, eds):
    tpl_label = ", ".join(
        cfg.get("templates") or ([cfg["template"]] if cfg.get("template") else [])
    )
    sub_bits = [esc(mode), esc(tpl_label), f"{len(eds)} published"]
    return (
        f'<div class="nb-serieshead"><h1>{esc(name)}</h1>'
        f'<div class="nb-series-sub">{" · ".join(b for b in sub_bits if b)}'
        "</div></div>"
    )


def render_sequence_body(sid, *, items, published):
    """Render the published entries of a sequence in config order.

    Numbering follows each item's position in the configured sequence, so
    published entries keep their canonical number even when earlier or later
    items are not yet published.
    """
    rows = [
        f'<li><a href="../../library/{esc(sid)}/{esc(str(it.get("slug")))}.html">'
        f'<span class="nb-seq-n">{i:02d}</span>'
        f'<span class="nb-seq-t">{esc(str(it.get("title", it.get("slug"))))}</span>'
        "</a></li>"
        for i, it in enumerate(items, 1)
        if it.get("slug") in published
    ]
    return f'<ol class="nb-seq">{"".join(rows)}</ol>'


def render_timeline_body(*, mode, eds, series_cfgs):
    date_of = (
        (lambda e: e["slug"])
        if mode == "rolling"
        else (lambda e: e["meta"].get("date", ""))
    )
    parts, seen_month = [], None
    for ed in sorted(eds, key=lambda e: (date_of(e), e["slug"]), reverse=True):
        month = date_of(ed)[:7]
        if month != seen_month:
            label = month_label(date_of(ed), month)
            parts.append(f'<span class="nb-month-label">{esc(label)}</span>')
            seen_month = month
        parts.append(story_item(ed, series_cfgs, depth=2))
    return (
        f'<div class="nb-list">{"".join(parts)}</div>'
        if parts
        else '<div class="nb-empty"><p>No articles yet.</p></div>'
    )


def render_collection_body(*, items, published, eds, series_cfgs):
    rows = [
        story_item(published[it["slug"]], series_cfgs, depth=2)
        for it in items
        if it.get("slug") in published
    ]
    rows += [
        story_item(e, series_cfgs, depth=2)
        for e in eds
        if not any(it.get("slug") == e["slug"] for it in items)
    ]
    return f'<div class="nb-list">{"".join(rows)}</div>'


def render_series_page(site, sid, *, cfg, eds, series_cfgs):
    name = cfg.get("name", sid)
    mode = cfg.get("mode", "collection")
    eds = sorted(eds, key=lambda e: e["position"])
    published = {e["slug"]: e for e in eds}
    items = cfg.get("items") or []
    head = series_head_html(name, mode=mode, cfg=cfg, eds=eds)

    if mode == "sequence":
        body = head + render_sequence_body(sid, items=items, published=published)
    elif mode in ("rolling", "open"):
        body = head + render_timeline_body(mode=mode, eds=eds, series_cfgs=series_cfgs)
    else:  # collection, in config order
        body = head + render_collection_body(
            items=items, published=published, eds=eds, series_cfgs=series_cfgs
        )

    return page(
        site, f"{name} · {site['title']}", body=body, depth=2, active="Sections"
    )


def render_tags_index(site, catalog):
    body = '<div class="nb-pagehead"><h1>Tags</h1></div>'
    if catalog["tags"]:
        body += (
            '<div class="nb-chips" style="flex-wrap:wrap">'
            + "".join(
                f'<a href="{esc(t)}/">#{esc(t)} · {len(v)}</a>'
                for t, v in catalog["tags"].items()
            )
            + "</div>"
        )
    else:
        body += '<div class="nb-empty"><p>No tags yet.</p></div>'
    return page(site, f"Tags · {site['title']}", body=body, depth=1)


def is_safe_tag(tag):
    """Whether a tag can be turned into a tags/<tag>/index.html page safely.

    Tags are untrusted (they come from auto-merged night-shift content and
    check.py does not constrain them), and the builder writes each one as a
    directory under tags/. A tag whose segments escape that tree — `..`,
    `.`, an absolute path, a backslash, or an empty segment from a leading/
    trailing/double slash — is dropped from the catalog entirely, so no
    page, link, or os.makedirs is ever created outside --out. A plain
    nested tag like `a/b` is safe and renders at its true depth.
    """
    if not isinstance(tag, str) or not tag or tag != tag.strip():
        return False
    if "\\" in tag or tag.startswith("/"):
        return False
    return all(seg and seg not in (".", "..") for seg in tag.split("/"))


def render_tag_page(site, tag, *, refs, articles, series_cfgs):
    depth = 1 + len(tag.split("/"))
    # A plain tag sits at depth 2 (tags/ + tag); a nested a/b is one deeper per
    # segment, so links resolve either way.
    eds = [
        articles[tuple(r.split("/", 1))]
        for r in refs
        if tuple(r.split("/", 1)) in articles
    ]
    body = (
        f'<div class="nb-pagehead"><h1>#{esc(tag)}</h1>'
        f'<span class="nb-pagehead-facts">{len(eds)} article'
        f"{'s' if len(eds) != 1 else ''}</span></div>"
    )
    body += (
        '<div class="nb-list">'
        + "".join(
            story_item(e, series_cfgs, depth=depth)
            for e in sorted(eds, key=lambda e: e["meta"].get("date", ""), reverse=True)
        )
        + "</div>"
    )
    return page(site, f"#{tag} · {site['title']}", body=body, depth=depth)


def render_search_page(site):
    body = (
        '<div class="nb-pagehead"><h1>Search</h1></div>'
        '<div class="nb-searchbox"><input id="nb-q" type="search" '
        'placeholder="Fuzzy-search the library…" '
        'aria-label="Search the library" autocomplete="off"></div>'
        '<div class="nb-results-count" id="nb-count"></div>'
        '<div class="nb-results" id="nb-results"></div>'
    )
    return page(site, f"Search · {site['title']}", body=body, depth=1, active="Search")


TEXT_STRIP_RE = re.compile(
    r"<!--[\s\S]*?-->|<script[\s\S]*?</script>|<style[\s\S]*?</style>"
    r"|<[^>]+>",
    re.I,
)
BODY_RE = re.compile(r"<body[^>]*>([\s\S]*?)</body>", re.I)


def article_body_html(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    m = BODY_RE.search(raw)
    return m.group(1) if m else raw


def article_text(path):
    text = TEXT_STRIP_RE.sub(" ", article_body_html(path))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def build_search_index(articles, series_cfgs):
    out = []
    for ed in sorted(
        articles.values(),
        key=by_date_and_slug,
        reverse=True,
    ):
        meta = ed["meta"]
        cfg = series_cfgs.get(ed["series"], {})
        out.append(
            {
                "series": ed["series"],
                "series_name": cfg.get("name", ed["series"]),
                "section": cfg.get("section"),
                "slug": ed["slug"],
                "title": meta.get("title", ed["slug"]),
                "dek": meta.get("dek", ""),
                "tags": meta.get("tags") or [],
                "template": meta.get("template"),
                "date": meta.get("date"),
                "reading_minutes": ed["reading_minutes"],
                "path": f"/library/{ed['series']}/{ed['slug']}.html",
                "text": article_text(ed["file"]),
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Feeds (Atom)
# --------------------------------------------------------------------------- #

FEED_STRIP_RE = re.compile(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", re.I)
HREF_RE = re.compile(r'((?:href|src)=")([^"]+)(")', re.I)


def absolutize_url(base_url, path):
    return f"{base_url}{path}" if base_url else path


def feed_content_html(path, base_url):
    """Return the article body as a feed-safe HTML fragment.

    Scripts, styles, and comments are stripped so feed readers get
    content, not code. When a base URL is known, relative hrefs are
    absolutized; oversized bodies return empty so the entry falls back
    to its summary.
    """
    body = FEED_STRIP_RE.sub(" ", article_body_html(path))

    def absolutize(match):
        pre, url, post = match.groups()
        if base_url and url.startswith("../"):
            return f"{pre}{base_url}/{url.replace('../', '')}{post}"
        if base_url and url.startswith("/"):
            return f"{pre}{base_url}{url}{post}"
        return match.group(0)

    body = HREF_RE.sub(absolutize, body)
    return body if len(body) <= FEED_CONTENT_MAX else ""


def feed_tag_id(base_url, resource, *, year):
    """A globally-unique, stable Atom id for a feed or entry.

    When the paper has a base_url its id is an RFC 4151 tag: IRI whose
    authority is the paper's own domain and whose specific part is the
    resource path under it, so two independent papers — even two on the
    same host under different paths, or two publishing the same
    series/slug — never collide (the constant urn:nightly-build: ids they
    replace were byte-identical across papers). With no base_url (a local
    build) it falls back to that urn scheme, which is fine offline.
    """
    match = re.match(r"https?://([^/]+)(/.*)?$", base_url or "")
    if not match:
        return f"urn:nightly-build:{resource}"
    host = match.group(1)
    prefix = (match.group(2) or "").strip("/")
    specific = f"{prefix}/{resource}".strip("/")
    return f"tag:{host},{year}:{specific}"


def entry_year(meta, generated):
    date = meta.get("date")
    if isinstance(date, str) and len(date) >= 4 and date[:4].isdigit():
        return date[:4]
    return generated.strftime("%Y")


def atom_feed(base_url, feed_path, *, title, eds, generated, author=None):
    author = author or title

    def absolute(path):
        return absolutize_url(base_url, path)

    entries = []
    for i, ed in enumerate(eds[:FEED_LIMIT]):
        meta = ed["meta"]
        link = absolute(f"/library/{ed['series']}/{ed['slug']}.html")
        updated = f"{meta.get('date', generated.date().isoformat())}T00:00:00Z"
        entry_id = feed_tag_id(
            base_url,
            f"library/{ed['series']}/{ed['slug']}",
            year=entry_year(meta, generated),
        )
        content = ""
        if i < FEED_CONTENT_LIMIT:
            fragment = feed_content_html(ed["file"], base_url)
            if fragment:
                content = '\n    <content type="html">' + esc(fragment) + "</content>"
        entries.append(f"""  <entry>
    <title>{esc(str(meta.get("title", ed["slug"])))}</title>
    <link rel="alternate" type="text/html" href="{esc(link)}"/>
    <id>{esc(entry_id)}</id>
    <updated>{updated}</updated>
    <summary>{esc(str(meta.get("dek", "")))}</summary>{content}
    <category term="{esc(ed["series"])}"/>
  </entry>""")
    self_link = absolute(f"/{feed_path}")
    feed_id = feed_tag_id(base_url, feed_path, year=generated.strftime("%Y"))
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{esc(title)}</title>
  <link rel="self" type="application/atom+xml" href="{esc(self_link)}"/>
  <link rel="alternate" type="text/html" href="{esc(absolute("/") or "/")}"/>
  <id>{esc(feed_id)}</id>
  <author><name>{esc(author)}</name></author>
  <updated>{generated.strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>
{chr(10).join(entries)}
</feed>
"""


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
