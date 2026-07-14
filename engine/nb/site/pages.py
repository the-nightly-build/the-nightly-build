"""Every page the builder writes, and the chrome they all wear.

One shell — the bar, the content column, the footer — dresses the newsstand,
the nights, the sections, the tags, and the search page, and dress_article
splices the same bar and footer into an article copy. A change here changes
the whole paper on the next build.
"""

import datetime as dt
import html

from nb.site.catalog import DIRECTORY_URL
from nb.site.library import article_text, by_date_and_slug, date_sort_key

esc = html.escape

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
