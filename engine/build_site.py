#!/usr/bin/env python3
"""
The Nightly Build — engine/build_site.py (the press).

Reads editions from a library checkout, writes the static site:

    site/
      index.html                  # the newsstand = tonight's build
      builds/index.html           # calendar archive of every build
      builds/<YYYY-MM-DD>/        # one page per night, permanent
      series/index.html           # series directory
      series/<id>/index.html      # per-series pages (mode-aware)
      tags/<tag>/index.html
      catalog.json                # machine-readable library state (§7.1)
      feed.xml, series/<id>/feed.xml   # Atom feeds
      assets/                     # copied from main's engine/assets
      library/<series>/<slug>.html     # editions, copied verbatim

Invocations:
    Publish:      build_site.py --repo <main checkout> --library <library checkout> --out site
    Press check:  build_site.py --repo . --preview press-check/ --out press-check/site/

Documented implementer decisions (handoff §15):
  * Feeds are Atom.
  * builds/ groups strictly by nb-meta `date`; a late merge lands under its
    authored date and the newsstand simply shows the latest date that has editions.
  * Reading time = nb-meta reading_minutes, else max(1, round(words / 230)).
  * Appearance is persisted under localStorage key "nb-appearance".
  * On the mobile feed, non-lead deks clamp to one line (full dek on the edition).

Dependencies: Python stdlib + PyYAML.
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("build_site.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

PROTOCOL = "1.0"
WORDS_PER_MINUTE = 230
FEED_LIMIT = 50
META_RE = re.compile(
    r'<script[^>]*\bid="nb-meta"[^>]*>(.*?)</script>', re.S | re.I)
BODY_TAG_RE = re.compile(r"<body[^>]*>", re.I)

esc = html.escape


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_site_config(repo):
    cfg = load_yaml(os.path.join(repo, "site.yaml"))
    cfg.setdefault("title", "The Nightly Build")
    cfg.setdefault("theme", "engine/assets/themes/newspaper.css")
    cfg.setdefault("appearance", "auto")
    return cfg


def load_series_configs(repo):
    root = os.path.join(repo, "series")
    out = {}
    if not os.path.isdir(root):
        return out
    for sid in sorted(os.listdir(root)):
        path = os.path.join(root, sid, "series.yaml")
        if not sid.startswith("_") and os.path.isfile(path):
            out[sid] = load_yaml(path)
    return out


def read_meta(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        m = META_RE.search(fh.read())
    if not m:
        return None
    try:
        meta = json.loads(m.group(1))
        return meta if isinstance(meta, dict) else None
    except ValueError:
        return None


def editions_dir(root, sid):
    """Accept both a full library checkout and a bare library/ folder."""
    for base in (os.path.join(root, "library", sid), os.path.join(root, sid)):
        if os.path.isdir(base):
            return base
    return None


def scan_library(root):
    """Yield (series_id, slug, file_path) for every edition under root."""
    lib = os.path.join(root, "library")
    base = lib if os.path.isdir(lib) else root
    if not os.path.isdir(base):
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


def collect_editions(series_cfgs, library_root, preview_root=None):
    """Return {(sid, slug): edition dict}. Preview drafts override published."""
    editions = {}
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
            editions[(sid, slug)] = {
                "meta": meta,
                "series": sid,
                "slug": slug,
                "file": path,
                "draft": is_draft,
                "reading_minutes": reading_minutes(meta),
            }
    assign_positions(editions, series_cfgs)
    return editions


def assign_positions(editions, series_cfgs):
    """position = 1-based rank within the series' canonical order:
    sequence → nb-meta order; collection → config item order (unknown slugs
    last, alphabetical); rolling → date ascending."""
    by_series = {}
    for ed in editions.values():
        by_series.setdefault(ed["series"], []).append(ed)
    for sid, eds in by_series.items():
        cfg = series_cfgs.get(sid, {})
        mode = cfg.get("mode") or eds[0]["meta"].get("mode", "collection")
        if mode == "sequence":
            eds.sort(key=lambda e: (e["meta"].get("order") or 10**6, e["slug"]))
        elif mode == "collection":
            order = {it.get("slug"): i for i, it in enumerate(cfg.get("items") or [])}
            eds.sort(key=lambda e: (order.get(e["slug"], 10**6), e["slug"]))
        else:  # rolling
            eds.sort(key=lambda e: e["slug"])
        for i, ed in enumerate(eds, 1):
            ed["position"] = i


# --------------------------------------------------------------------------- #
# Catalog
# --------------------------------------------------------------------------- #

def build_catalog(site_cfg, series_cfgs, editions, generated):
    by_series = {}
    for ed in editions.values():
        by_series.setdefault(ed["series"], []).append(ed)

    series_entries = []
    for sid, cfg in series_cfgs.items():
        items = cfg.get("items") or []
        series_entries.append({
            "id": sid,
            "name": cfg.get("name", sid),
            "mode": cfg.get("mode"),
            "template": cfg.get("template"),
            "count": len(by_series.get(sid, [])),
            "total": len(items) if cfg.get("mode") in ("collection", "sequence") else None,
        })
    # editions published for series no longer configured still belong to the site
    for sid in sorted(set(by_series) - set(series_cfgs)):
        eds = by_series[sid]
        series_entries.append({
            "id": sid, "name": sid, "mode": eds[0]["meta"].get("mode"),
            "template": eds[0]["meta"].get("template"),
            "count": len(eds), "total": None,
        })

    edition_entries = []
    for ed in sorted(editions.values(),
                     key=lambda e: (e["meta"].get("date", ""), e["series"],
                                    e["slug"]), reverse=True):
        entry = dict(ed["meta"])
        entry["path"] = f"/library/{ed['series']}/{ed['slug']}.html"
        entry["position"] = ed["position"]
        entry["reading_minutes"] = ed["reading_minutes"]
        if ed["draft"]:
            entry["draft"] = True
        edition_entries.append(entry)

    builds = {}
    for ed in editions.values():
        d = ed["meta"].get("date") or "unknown"
        builds.setdefault(d, []).append(f"{ed['series']}/{ed['slug']}")
    builds = {d: sorted(v) for d, v in sorted(builds.items(), reverse=True)}

    tags = {}
    for ed in editions.values():
        for t in ed["meta"].get("tags") or []:
            tags.setdefault(t, []).append(f"{ed['series']}/{ed['slug']}")
    tags = {t: sorted(v) for t, v in sorted(tags.items())}

    return {
        "generated": generated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": PROTOCOL,
        "site_title": site_cfg["title"],
        "series": series_entries,
        "editions": edition_entries,
        "builds": builds,
        "tags": tags,
    }


# --------------------------------------------------------------------------- #
# Page chrome
# --------------------------------------------------------------------------- #

FONTS = ("https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@"
         "0,6..72,400..700;1,6..72,400..700&family=Inter:wght@400;500;600&"
         "family=IBM+Plex+Mono:wght@400;500&display=swap")

APPEARANCE_BOOTSTRAP = (
    '<script>try{var m=localStorage.getItem("nb-appearance");'
    'if(m==="light"||m==="dark")document.documentElement.setAttribute("data-mode",m);'
    "}catch(e){}</script>")

NAV_ITEMS = [("Tonight", ""), ("Archive", "builds/"), ("Series", "series/"),
             ("Tags", "tags/"), ("Search", "#nb-search")]


def page(site, title, body, depth=0, active=None, preview=False):
    rel = "../" * depth
    mode_attr = (f' data-mode="{site["appearance"]}"'
                 if site["appearance"] in ("light", "dark") else "")
    banner = ('<div class="nb-presscheck-banner">Press check — unpublished proof'
              "</div>" if preview else "")
    nav_parts = []
    for label, href in NAV_ITEMS:
        url = href if href.startswith("#") else rel + href
        current = ' aria-current="page"' if label == active else ""
        nav_parts.append(f'<a href="{url}"{current}>{label}</a>')
    nav = "".join(nav_parts)
    date_line = site["tonight_label"]
    return f"""<!DOCTYPE html>
<html lang="en"{mode_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="{rel}assets/theme.css">
<link rel="stylesheet" href="{rel}assets/nb.css">
<link rel="alternate" type="application/atom+xml" href="{rel}feed.xml" title="{esc(site['title'])}">
{APPEARANCE_BOOTSTRAP}
<script defer src="{rel}assets/nb.js"></script>
</head>
<body>
{banner}
<header class="nb-masthead"><div class="nb-wrap">
  <div class="nb-masthead-row">
    <a class="nb-site-title" href="{rel}">{esc(site['title'])}<span class="nb-period">.</span></a>
    <span class="nb-masthead-date">{esc(date_line)}</span>
    <span class="nb-masthead-tools">
      <button class="nb-appearance" type="button">◐ auto</button>
    </span>
  </div>
  <nav class="nb-nav">{nav}</nav>
  <div class="nb-search" id="nb-search">
    <input type="search" placeholder="Search the library…" aria-label="Search">
    <div class="nb-search-results"></div>
  </div>
</div></header>
<main class="nb-wrap">
{body}
</main>
<footer class="nb-footer"><div class="nb-wrap">
  <a href="{rel}feed.xml">Atom feed</a> · Built by
  <a href="https://github.com/RyanSaxe/the-nightly-build">The Nightly Build</a>
  — while you slept.
</div></footer>
</body></html>"""


def card(ed, series_cfgs, depth=0, lead=False, is_new=False):
    rel = "../" * depth
    meta = ed["meta"]
    cfg = series_cfgs.get(ed["series"], {})
    name = cfg.get("name", ed["series"])
    total = len(cfg.get("items") or []) if cfg.get("mode") in ("collection", "sequence") else 0
    context = esc(name)
    if cfg.get("mode") == "sequence" and total:
        context += f" · Ed. {ed['position']} of {total}"
    meta_bits = []
    if is_new:
        meta_bits.append('<span class="nb-new-dot">●</span> new')
    meta_bits.append(f"{ed['reading_minutes']} min read")
    if isinstance(meta.get("sources"), int):
        meta_bits.append(f"{meta['sources']} sources")
    if meta.get("model"):
        meta_bits.append(esc(str(meta["model"])))
    draft = ' <span class="nb-draft-tag">draft</span>' if ed["draft"] else ""
    return (
        f'<a class="nb-card{" nb-card-lead" if lead else ""}" '
        f'href="{rel}library/{ed["series"]}/{ed["slug"]}.html">'
        f'<span class="nb-badge">{esc(str(meta.get("template", "")))}</span>{draft}'
        f'<div class="nb-card-context">{context}</div>'
        f"<h3>{esc(str(meta.get('title', ed['slug'])))}</h3>"
        f'<p class="nb-dek">{esc(str(meta.get("dek", "")))}</p>'
        f'<div class="nb-card-meta">{" · ".join(meta_bits)}</div>'
        "</a>")


def cards_block(eds, series_cfgs, depth, new_dates=()):
    if not eds:
        return ""
    lead = max(eds, key=lambda e: e["reading_minutes"])
    ordered = [lead] + [e for e in eds if e is not lead]
    return '<div class="nb-cards">' + "".join(
        card(e, series_cfgs, depth, lead=(e is lead),
             is_new=e["meta"].get("date") in new_dates)
        for e in ordered) + "</div>"


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #

def month_grouped_dates(dates, depth, current=None):
    """Compact month-grouped date navigator linking to builds/<date>/."""
    rel = "../" * depth
    out, seen_month = [], None
    for d in sorted(dates, reverse=True):
        month = d[:7]
        if month != seen_month:
            try:
                label = dt.date.fromisoformat(d).strftime("%B %Y")
            except ValueError:
                label = month
            out.append(f'<span class="nb-month-label">{esc(label)}</span>')
            seen_month = month
        cur = ' aria-current="page"' if d == current else ""
        out.append(f'<a href="{rel}builds/{d}/"{cur}>{d[8:]}</a>')
    return f'<div class="nb-dates">{"".join(out)}</div>'


def series_strip(sinfo, cfg, eds, depth):
    rel = "../" * depth
    total = sinfo.get("total")
    count = sinfo["count"]
    mode = sinfo.get("mode")
    if mode == "sequence" and total:
        items = cfg.get("items") or []
        published = {e["slug"] for e in eds}
        nxt = next((it for it in items if it.get("slug") not in published), None)
        info = (f"continue: {esc(str(nxt.get('title')))}" if nxt else "complete")
        pct = round(100 * count / total) if total else 0
        bar = f'<span class="nb-progress"><b style="width:{pct}%"></b></span>'
        info = f"{count} of {total} · {info}"
    elif mode == "collection" and total:
        pct = round(100 * count / total) if total else 0
        bar = f'<span class="nb-progress"><b style="width:{pct}%"></b></span>'
        info = f"{count} of {total}"
    else:
        bar = ""
        latest = max((e["meta"].get("date", "") for e in eds), default=None)
        info = f"latest: {latest}" if latest else "no editions yet"
    return (f'<a class="nb-strip" href="{rel}series/{sinfo["id"]}/">'
            f'<span class="nb-strip-name">{esc(sinfo["name"])}</span>{bar}'
            f'<span class="nb-strip-info">{info}</span></a>')


def render_newsstand(site, catalog, series_cfgs, editions, now):
    by_series = {}
    for ed in editions.values():
        by_series.setdefault(ed["series"], []).append(ed)

    if not editions:
        body = ('<div class="nb-empty" style="margin-top:26px">'
                "<h2>The presses are ready</h2>"
                "<p>Set up your first series — ask your agent to "
                "“set me up”, then run a press check.</p></div>")
        strips = "".join(
            series_strip(s, series_cfgs.get(s["id"], {}), [], 0)
            for s in catalog["series"])
        if strips:
            body += '<div class="nb-rule-label">Series</div>' + strips
        return page(site, site["title"], body, active="Tonight",
                    preview=site["preview"])

    latest = max(catalog["builds"])
    tonight = [ed for ed in editions.values() if ed["meta"].get("date") == latest]
    label = ("Tonight’s build" if latest == now.date().isoformat()
             else f"Last night’s build · {latest}")
    built = now.strftime("%H:%M UTC")
    body = (f'<div class="nb-rule-label">{label} · {len(tonight)} '
            f'edition{"s" if len(tonight) != 1 else ""} · built {built}</div>')
    body += cards_block(tonight, series_cfgs, 0, new_dates={latest})

    strips = "".join(
        series_strip(s, series_cfgs.get(s["id"], {}), by_series.get(s["id"], []), 0)
        for s in catalog["series"])
    if strips:
        body += '<div class="nb-rule-label">Series</div>' + strips
    body += '<div class="nb-rule-label">Past builds</div>'
    body += month_grouped_dates(catalog["builds"], 0)
    return page(site, site["title"], body, active="Tonight",
                preview=site["preview"])


def render_build_page(site, date, dates, editions, series_cfgs):
    eds = [e for e in editions.values() if e["meta"].get("date") == date]
    body = (f'<div class="nb-rule-label">Build of {date} · {len(eds)} '
            f'edition{"s" if len(eds) != 1 else ""}</div>')
    body += cards_block(eds, series_cfgs, 2)
    ordered = sorted(dates)
    i = ordered.index(date)
    prev_d = ordered[i - 1] if i > 0 else None
    next_d = ordered[i + 1] if i < len(ordered) - 1 else None
    body += ('<div class="nb-pager">'
             + (f'<a href="../{prev_d}/">← {prev_d}</a>' if prev_d else "<span></span>")
             + '<a href="../">all builds</a>'
             + (f'<a href="../{next_d}/">{next_d} →</a>' if next_d else "<span></span>")
             + "</div>")
    return page(site, f"Build of {date} — {site['title']}", body, depth=2,
                active="Archive", preview=site["preview"])


def render_build_archive(site, dates):
    body = '<div class="nb-rule-label">Every build</div>'
    body += (month_grouped_dates(dates, 1) if dates
             else '<div class="nb-empty"><p>No builds yet.</p></div>')
    return page(site, f"Archive — {site['title']}", body, depth=1,
                active="Archive", preview=site["preview"])


def render_series_index(site, catalog, series_cfgs, editions):
    by_series = {}
    for ed in editions.values():
        by_series.setdefault(ed["series"], []).append(ed)
    body = '<div class="nb-rule-label">Series</div>'
    strips = "".join(
        series_strip(s, series_cfgs.get(s["id"], {}), by_series.get(s["id"], []), 1)
        for s in catalog["series"])
    body += strips or '<div class="nb-empty"><p>No series configured.</p></div>'
    return page(site, f"Series — {site['title']}", body, depth=1,
                active="Series", preview=site["preview"])


def render_series_page(site, sid, cfg, eds, series_cfgs):
    name = cfg.get("name", sid)
    mode = cfg.get("mode", "collection")
    eds = sorted(eds, key=lambda e: e["position"])
    published = {e["slug"]: e for e in eds}
    items = cfg.get("items") or []
    total = len(items)

    head = (f'<div class="nb-series-head"><h1>{esc(name)}</h1>'
            f'<div class="nb-series-sub">{esc(mode)} · '
            f'{esc(str(cfg.get("template", "")))} · {len(eds)}'
            f'{f" of {total}" if total and mode != "rolling" else ""} published'
            "</div></div>")

    if mode == "sequence":
        pct = round(100 * len(eds) / total) if total else 0
        head += f'<div class="nb-progress-wide"><b style="width:{pct}%"></b></div>'
        rows = []
        continue_slug = next(
            (it.get("slug") for it in items if it.get("slug") not in published), None)
        for i, it in enumerate(items, 1):
            slug, title = it.get("slug"), it.get("title", it.get("slug"))
            if slug in published:
                rows.append(
                    f'<li><a href="../../library/{sid}/{slug}.html">'
                    f'<span class="nb-seq-n">{i:02d}</span>'
                    f'<span class="nb-seq-t">{esc(str(title))}</span></a></li>')
            else:
                marker = (' <a class="nb-continue" href="#">continue here</a>'
                          if slug == continue_slug else "")
                rows.append(
                    f'<li><span class="nb-seq-unpub">'
                    f'<span class="nb-seq-n">{i:02d}</span>'
                    f'<span class="nb-seq-t">{esc(str(title))}{marker}</span>'
                    "</span></li>")
        body = head + f'<ol class="nb-seq">{"".join(rows)}</ol>'
    elif mode == "rolling":
        parts, seen_month = [], None
        for ed in sorted(eds, key=lambda e: e["slug"], reverse=True):
            month = ed["slug"][:7]
            if month != seen_month:
                try:
                    label = dt.date.fromisoformat(ed["slug"]).strftime("%B %Y")
                except ValueError:
                    label = month
                parts.append(f'<div class="nb-rule-label">{esc(label)}</div>')
                seen_month = month
            parts.append(card(ed, series_cfgs, 2))
        body = head + '<div class="nb-cards" style="grid-template-columns:1fr">' \
            + "".join(parts) + "</div>" if parts else head + \
            '<div class="nb-empty"><p>No editions yet.</p></div>'
    else:  # collection: grid in config order
        cards = [card(published[it["slug"]], series_cfgs, 2)
                 for it in items if it.get("slug") in published]
        cards += [card(e, series_cfgs, 2)
                  for e in eds if not any(it.get("slug") == e["slug"] for it in items)]
        unpub = [f'<div class="nb-card" style="color:var(--faint)">'
                 f'<span class="nb-badge">{esc(str(cfg.get("template", "")))}</span>'
                 f'<h3>{esc(str(it.get("title", it.get("slug"))))}</h3>'
                 f'<p class="nb-dek">coming</p></div>'
                 for it in items if it.get("slug") not in published]
        body = head + f'<div class="nb-cards">{"".join(cards + unpub)}</div>'

    return page(site, f"{name} — {site['title']}", body, depth=2,
                active="Series", preview=site["preview"])


def render_tags_index(site, catalog):
    body = '<div class="nb-rule-label">Tags</div>'
    if catalog["tags"]:
        body += '<div class="nb-dates">' + "".join(
            f'<a href="{esc(t)}/">#{esc(t)} · {len(v)}</a>'
            for t, v in catalog["tags"].items()) + "</div>"
    else:
        body += '<div class="nb-empty"><p>No tags yet.</p></div>'
    return page(site, f"Tags — {site['title']}", body, depth=1,
                active="Tags", preview=site["preview"])


def render_tag_page(site, tag, refs, editions, series_cfgs):
    eds = [editions[tuple(r.split("/", 1))] for r in refs
           if tuple(r.split("/", 1)) in editions]
    body = f'<div class="nb-rule-label">#{esc(tag)} · {len(eds)} editions</div>'
    body += cards_block(
        sorted(eds, key=lambda e: e["meta"].get("date", ""), reverse=True),
        series_cfgs, 2)
    return page(site, f"#{tag} — {site['title']}", body, depth=2,
                active="Tags", preview=site["preview"])


# --------------------------------------------------------------------------- #
# Feeds (Atom)
# --------------------------------------------------------------------------- #

def atom_feed(site, base_url, feed_path, title, eds, generated):
    def absolute(path):
        return f"{base_url}{path}" if base_url else path

    entries = []
    for ed in eds[:FEED_LIMIT]:
        meta = ed["meta"]
        link = absolute(f"/library/{ed['series']}/{ed['slug']}.html")
        updated = f"{meta.get('date', generated.date().isoformat())}T00:00:00Z"
        entries.append(f"""  <entry>
    <title>{esc(str(meta.get('title', ed['slug'])))}</title>
    <link rel="alternate" type="text/html" href="{esc(link)}"/>
    <id>urn:nightly-build:{ed['series']}/{ed['slug']}</id>
    <updated>{updated}</updated>
    <summary>{esc(str(meta.get('dek', '')))}</summary>
    <category term="{esc(ed['series'])}"/>
  </entry>""")
    self_link = absolute(f"/{feed_path}")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{esc(title)}</title>
  <link rel="self" type="application/atom+xml" href="{esc(self_link)}"/>
  <link rel="alternate" type="text/html" href="{esc(absolute('/') or '/')}"/>
  <id>urn:nightly-build:{esc(feed_path)}</id>
  <updated>{generated.strftime('%Y-%m-%dT%H:%M:%SZ')}</updated>
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


def copy_assets(repo, site_cfg, out):
    src = os.path.join(repo, "engine", "assets")
    dst = os.path.join(out, "assets")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    # the configured theme is also published under the stable name assets/theme.css
    # so a site.yaml theme swap restyles every already-published edition
    theme_src = os.path.join(repo, site_cfg["theme"])
    shutil.copyfile(theme_src, os.path.join(dst, "theme.css"))


def copy_editions(editions, out, preview):
    banner = ('<div class="nb-presscheck-banner">Press check — '
              "unpublished proof</div>")
    for ed in editions.values():
        dst = os.path.join(out, "library", ed["series"], f"{ed['slug']}.html")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if preview and ed["draft"]:
            with open(ed["file"], "r", encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
            raw = BODY_TAG_RE.sub(lambda m: m.group(0) + banner, raw, count=1)
            write(dst, raw)
        else:
            shutil.copyfile(ed["file"], dst)


def build(repo, library_root, out, preview_root=None, base_url="", now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    site_cfg = load_site_config(repo)
    series_cfgs = load_series_configs(repo)
    editions = collect_editions(series_cfgs, library_root, preview_root)
    catalog = build_catalog(site_cfg, series_cfgs, editions, now)

    site = {
        "title": site_cfg["title"],
        "appearance": site_cfg["appearance"],
        "preview": bool(preview_root),
        "tonight_label": now.strftime("%A, %B %-d, %Y")
        if os.name != "nt" else now.strftime("%A, %B %d, %Y"),
    }

    os.makedirs(out, exist_ok=True)
    write(os.path.join(out, "catalog.json"), json.dumps(catalog, indent=2) + "\n")
    write(os.path.join(out, "index.html"),
          render_newsstand(site, catalog, series_cfgs, editions, now))
    write(os.path.join(out, "builds", "index.html"),
          render_build_archive(site, list(catalog["builds"])))
    for date in catalog["builds"]:
        write(os.path.join(out, "builds", date, "index.html"),
              render_build_page(site, date, list(catalog["builds"]),
                                editions, series_cfgs))
    write(os.path.join(out, "series", "index.html"),
          render_series_index(site, catalog, series_cfgs, editions))
    by_series = {}
    for ed in editions.values():
        by_series.setdefault(ed["series"], []).append(ed)
    for s in catalog["series"]:
        sid = s["id"]
        write(os.path.join(out, "series", sid, "index.html"),
              render_series_page(site, sid, series_cfgs.get(sid, {}),
                                 by_series.get(sid, []), series_cfgs))
    write(os.path.join(out, "tags", "index.html"),
          render_tags_index(site, catalog))
    for tag, refs in catalog["tags"].items():
        write(os.path.join(out, "tags", tag, "index.html"),
              render_tag_page(site, tag, refs, editions, series_cfgs))

    all_sorted = sorted(editions.values(),
                        key=lambda e: (e["meta"].get("date", ""), e["slug"]),
                        reverse=True)
    write(os.path.join(out, "feed.xml"),
          atom_feed(site, base_url, "feed.xml", site_cfg["title"],
                    all_sorted, now))
    for s in catalog["series"]:
        sid = s["id"]
        eds = sorted(by_series.get(sid, []),
                     key=lambda e: (e["meta"].get("date", ""), e["slug"]),
                     reverse=True)
        write(os.path.join(out, "series", sid, "feed.xml"),
              atom_feed(site, base_url, f"series/{sid}/feed.xml",
                        f"{site_cfg['title']} — {s['name']}", eds, now))

    copy_assets(repo, site_cfg, out)
    copy_editions(editions, out, bool(preview_root))
    return catalog


def main(argv=None):
    p = argparse.ArgumentParser(description="The Nightly Build site builder")
    p.add_argument("--repo", default=".",
                   help="main checkout (engine, templates, series, site.yaml)")
    p.add_argument("--library", default=".",
                   help="library checkout (published editions)")
    p.add_argument("--out", default="site", help="output directory")
    p.add_argument("--preview",
                   help="press-check dir; its library/ drafts are merged in "
                        "and every page is bannered")
    p.add_argument("--base-url", default="",
                   help="absolute site base URL (no trailing slash) for feeds")
    p.add_argument("--now", help="override the build timestamp (tests), ISO-8601 UTC")
    args = p.parse_args(argv)

    now = None
    if args.now:
        now = dt.datetime.fromisoformat(args.now)
        if now.tzinfo is None:
            now = now.replace(tzinfo=dt.timezone.utc)

    catalog = build(args.repo, args.library, args.out,
                    preview_root=args.preview,
                    base_url=args.base_url.rstrip("/"), now=now)
    n = len(catalog["editions"])
    print(f"site built: {args.out} ({n} edition{'s' if n != 1 else ''}, "
          f"{len(catalog['builds'])} builds)")
    if args.preview:
        print("press check preview — serve with: "
              f"python3 -m http.server -d {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
