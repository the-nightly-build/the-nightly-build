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
import hashlib
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

PROTOCOL = "1.1"
WORDS_PER_MINUTE = 230
FEED_LIMIT = 50
FEED_CONTENT_LIMIT = 10        # newest N entries carry full content
FEED_CONTENT_MAX = 150_000     # per-entry cap after stripping, bytes
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
    """Engine defaults, overridden by the user's press/site.yaml if present."""
    cfg = {}
    path = os.path.join(repo, "press", "site.yaml")
    if os.path.isfile(path):
        cfg = load_yaml(path)
    cfg.setdefault("title", "The Nightly Build")
    cfg.setdefault("theme", "engine/assets/themes/newspaper.css")
    cfg.setdefault("appearance", "auto")
    cfg.setdefault("front", "compact")
    return cfg


def load_series_configs(repo):
    root = os.path.join(repo, "press", "series")
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
    """Yield (series_id, slug, file_path) for every edition under root.

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
        elif mode == "open":  # topical slugs; publication date is the order
            eds.sort(key=lambda e: (e["meta"].get("date", ""), e["slug"]))
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
        entry = {
            "id": sid,
            "name": cfg.get("name", sid),
            "mode": cfg.get("mode"),
            "template": cfg.get("template"),
            "count": len(by_series.get(sid, [])),
            "total": len(items) if cfg.get("mode") in ("collection", "sequence") else None,
        }
        for key in ("templates", "cadence", "paused", "section"):
            if cfg.get(key):
                entry[key] = cfg[key]
        series_entries.append(entry)
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

NAV_ITEMS = [("Today", ""), ("Sections", "series/"), ("Search", "search/"),
             ("RSS", "feed.xml")]


WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday")
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


def pretty_date(iso):
    """2026-07-06 → Monday, July 6, 2026 (platform-independent)."""
    try:
        d = dt.date.fromisoformat(iso)
    except (ValueError, TypeError):
        return iso
    return f"{WEEKDAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}"


def asset_stamp(repo):
    """Content hash of the shared assets: cache-busting version tag. A
    returning reader must never see new markup with a stale stylesheet."""
    h = hashlib.md5()
    base = os.path.join(repo, "engine", "assets")
    for name in ("nb.css", "nb.js"):
        path = os.path.join(base, name)
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:10]


def page(site, title, body, depth=0, active=None):
    """One page chrome for every page: two-element bar + thin bottom footer."""
    rel = "../" * depth
    mode_attr = (f' data-mode="{site["appearance"]}"'
                 if site["appearance"] in ("light", "dark") else "")
    nav_parts = []
    for label, href in NAV_ITEMS:
        current = ' aria-current="page"' if label == active else ""
        nav_parts.append(f'<a href="{rel + href}"{current}>{label}</a>')
    nav = "".join(nav_parts)
    return f"""<!DOCTYPE html>
<html lang="en"{mode_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="{rel}assets/theme.css?v={site['stamp']}">
<link rel="stylesheet" href="{rel}assets/nb.css?v={site['stamp']}">
<link rel="alternate" type="application/atom+xml" href="{rel}feed.xml" title="{esc(site['title'])}">
{APPEARANCE_BOOTSTRAP}
<script defer src="{rel}assets/nb.js?v={site['stamp']}"></script>
</head>
<body{site['body_class']}>
<header class="nb-bar"><div class="nb-bar-in">
  <a class="nb-wordmark" href="{rel}">{esc(site['title'])}<span class="nb-period">.</span></a>
  <details class="nb-menu"><summary aria-label="Menu"><span class="nb-burger"></span></summary>
  <nav class="nb-menu-panel">{nav}</nav></details>
</div></header>
<main class="nb-shell">
{body}
</main>
<footer class="nb-footer"><div class="nb-footer-in">
  <a href="{rel}feed.xml">RSS</a>
  <a href="https://github.com/RyanSaxe/the-nightly-build">GitHub</a>
  <button class="nb-appearance" type="button">◐ auto</button>
</div></footer>
</body></html>"""


def kicker_text(ed, series_cfgs):
    cfg = series_cfgs.get(ed["series"], {})
    name = cfg.get("name", ed["series"])
    section = cfg.get("section")
    return f"{section} — {name}" if section else name


def item_meta_row(ed):
    form = str(ed["meta"].get("template", "")).capitalize()
    return (f'<div class="nb-meta"><span>{ed["reading_minutes"]} min read</span>'
            f"<span>{esc(form)}</span></div>")


def story_item(ed, series_cfgs, depth=0):
    rel = "../" * depth
    dek = str(ed["meta"].get("dek", ""))
    dek_html = f'<p class="nb-dek nb-cell-dek">{esc(dek)}</p>' if dek else ""
    return (f'<a class="nb-item" href="{rel}library/{ed["series"]}/{ed["slug"]}.html">'
            f'<div class="nb-kicker">{esc(kicker_text(ed, series_cfgs))}</div>'
            f'<h3>{esc(str(ed["meta"].get("title", ed["slug"])))}</h3>'
            f"{dek_html}{item_meta_row(ed)}</a>")


def lead_cell(ed, series_cfgs, depth=0):
    rel = "../" * depth
    meta = ed["meta"]
    return (f'<a class="nb-item nb-lead-cell" '
            f'href="{rel}library/{ed["series"]}/{ed["slug"]}.html">'
            f'<div class="nb-kicker">{esc(kicker_text(ed, series_cfgs))}</div>'
            f'<h2>{esc(str(meta.get("title", ed["slug"])))}</h2>'
            f'<p class="nb-dek">{esc(str(meta.get("dek", "")))}</p>'
            f"{item_meta_row(ed)}</a>")


def night_body(eds, series_cfgs, depth, date):
    """One night's page: edition line, then ONE ruled table — the lead is
    its full-width first cell, the rest of the night fills the grid."""
    eds = sorted(eds, key=lambda e: -e["reading_minutes"])
    total = sum(e["reading_minutes"] for e in eds)
    body = (f'<div class="nb-editionline"><span>{esc(pretty_date(date))}</span>'
            f'<span class="nb-editionline-facts">{total} min read</span></div>')
    if not eds:
        return body + '<div class="nb-empty"><p>No editions this night.</p></div>'
    cells = lead_cell(eds[0], series_cfgs, depth) + "".join(
        story_item(e, series_cfgs, depth) for e in eds[1:])
    return body + f'<div class="nb-grid">{cells}</div>' 


def render_newsstand(site, catalog, series_cfgs, editions, now):
    if not editions:
        body = ('<div class="nb-empty" style="margin-top:26px">'
                "<h2>The presses are ready</h2>"
                "<p>Set up your first series — ask your agent to "
                "“set me up”, then run a press check.</p></div>")
        return page(site, site["title"], body, active="Today")
    dates = sorted(catalog["builds"])
    latest = dates[-1]
    tonight = [ed for ed in editions.values()
               if ed["meta"].get("date") == latest]
    body = night_body(tonight, series_cfgs, 0, latest)
    if len(dates) > 1:
        prev = dates[-2]
        body += (f'<nav class="nb-nightnav"><a href="builds/{prev}/">'
                 f"← {esc(pretty_date(prev))}</a></nav>")
    return page(site, site["title"], body, active="Today")


def render_build_page(site, date, dates, editions, series_cfgs):
    eds = [e for e in editions.values() if e["meta"].get("date") == date]
    body = night_body(eds, series_cfgs, 2, date)
    ordered = sorted(dates)
    i = ordered.index(date)
    prev_d = ordered[i - 1] if i > 0 else None
    next_d = ordered[i + 1] if i < len(ordered) - 1 else None
    left = (f'<a href="../{prev_d}/">← {esc(pretty_date(prev_d))}</a>'
            if prev_d else "<span></span>")
    if next_d and next_d == ordered[-1]:
        right = f'<a href="../../">{esc(pretty_date(next_d))} →</a>'
    elif next_d:
        right = f'<a href="../{next_d}/">{esc(pretty_date(next_d))} →</a>'
    else:
        right = "<span></span>"
    body += f'<nav class="nb-nightnav">{left}{right}</nav>'
    return page(site, f"{pretty_date(date)} — {site['title']}", body, depth=2)


def render_build_archive(site, dates):
    body = ('<div class="nb-pagehead"><h1>All nights</h1>'
            f'<span class="nb-pagehead-facts">{len(dates)} builds</span></div>')
    if not dates:
        body += '<div class="nb-empty"><p>No builds yet.</p></div>'
    seen_month = None
    for d in sorted(dates, reverse=True):
        month = d[:7]
        if month != seen_month:
            try:
                md = dt.date.fromisoformat(d)
                label = f"{MONTHS[md.month - 1]} {md.year}"
            except ValueError:
                label = month
            body += f'<span class="nb-month-label">{esc(label)}</span>'
            seen_month = month
        body += (f'<div class="nb-list"><a class="nb-nightnav" '
                 f'style="padding:8px 0" href="{d}/">{esc(pretty_date(d))}'
                 f"</a></div>")
    return page(site, f"All nights — {site['title']}", body, depth=1)


def desk_status(s, cfg):
    """(status_html, is_resting) for one desk on the Sections page."""
    mode, count, total = s.get("mode"), s["count"], s.get("total")
    if cfg.get("paused"):
        return "paused", True
    if mode in ("collection", "sequence"):
        if total and count >= total:
            return f"complete · {count} edition{'s' if count != 1 else ''}", True
        if not total:   # published but not in press config (or no items yet)
            return f"{count} published", False
        pct = round(100 * count / total)
        return (f'<span class="nb-progress"><b style="width:{pct}%"></b></span>'
                f"{count} of {total}", False)
    if mode == "rolling":
        cadence = cfg.get("cadence")
        return (esc(str(cadence)) if isinstance(cadence, str) else "nightly"), False
    return f"{count} published", False


def render_series_index(site, catalog, series_cfgs, editions):
    latest_by_series = {}
    for ed in editions.values():
        cur = latest_by_series.get(ed["series"])
        if cur is None or ed["meta"].get("date", "") > cur["meta"].get("date", ""):
            latest_by_series[ed["series"]] = ed

    groups, resting, ndesks = {}, [], 0
    for s in catalog["series"]:
        cfg = series_cfgs.get(s["id"], {})
        status, rests = desk_status(s, cfg)
        latest = latest_by_series.get(s["id"])
        latest_line = ""
        if latest:
            latest_line = (f'<span class="nb-desk-latest">'
                           f'{esc(str(latest["meta"].get("title", "")))} · '
                           f'{esc(pretty_date(latest["meta"].get("date", "")))}'
                           "</span>")
        row = (f'<a class="nb-desk{" nb-desk-done" if rests else ""}" '
               f'href="{s["id"]}/">'
               f'<span class="nb-desk-name">{esc(s.get("name", s["id"]))}</span>'
               f"{latest_line}"
               f'<span class="nb-desk-status">{status}</span></a>')
        ndesks += 1
        if rests:
            resting.append(row)
        else:
            groups.setdefault(cfg.get("section") or "Desks", []).append(row)

    facts = (f"{max(len(groups), 1)} section{'s' if len(groups) != 1 else ''} · "
             f"{ndesks} desk{'s' if ndesks != 1 else ''} · "
             f"{len(catalog['editions'])} edition"
             f"{'s' if len(catalog['editions']) != 1 else ''}")
    body = ('<div class="nb-pagehead"><h1>Sections</h1>'
            f'<span class="nb-pagehead-facts">{facts}</span></div>')
    if not groups and not resting:
        body += '<div class="nb-empty"><p>No series configured.</p></div>'
    for section, rows in groups.items():
        body += (f'<div class="nb-secgroup"><div class="nb-sechead">'
                 f"<h2>{esc(section)}</h2><span>{len(rows)} desk"
                 f"{'s' if len(rows) != 1 else ''}</span></div>"
                 f"{''.join(rows)}</div>")
    if resting:
        body += (f'<details class="nb-stacks"><summary>In the stacks — '
                 f"{len(resting)} desk{'s' if len(resting) != 1 else ''}"
                 f"</summary>{''.join(resting)}</details>")
    return page(site, f"Sections — {site['title']}", body, depth=1,
                active="Sections")


def render_series_page(site, sid, cfg, eds, series_cfgs):
    name = cfg.get("name", sid)
    mode = cfg.get("mode", "collection")
    eds = sorted(eds, key=lambda e: e["position"])
    published = {e["slug"]: e for e in eds}
    items = cfg.get("items") or []
    total = len(items)

    tpl_label = ", ".join(cfg.get("templates")
                          or ([cfg["template"]] if cfg.get("template") else []))
    sub_bits = [esc(mode), esc(tpl_label)]
    if total and mode in ("collection", "sequence"):
        sub_bits.append(f"{len(eds)} of {total} published")
    else:
        sub_bits.append(f"{len(eds)} published")
    head = (f'<div class="nb-serieshead"><h1>{esc(name)}</h1>'
            f'<div class="nb-series-sub">{" · ".join(b for b in sub_bits if b)}'
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
                marker = ('<span class="nb-continue">continue here</span>'
                          if slug == continue_slug else "")
                rows.append(
                    f'<li><span class="nb-seq-unpub">'
                    f'<span class="nb-seq-n">{i:02d}</span>'
                    f'<span class="nb-seq-t">{esc(str(title))}</span>{marker}'
                    "</span></li>")
        body = head + f'<ol class="nb-seq">{"".join(rows)}</ol>'
    elif mode in ("rolling", "open"):
        date_of = (lambda e: e["slug"]) if mode == "rolling"             else (lambda e: e["meta"].get("date", ""))
        parts, seen_month = [], None
        for ed in sorted(eds, key=lambda e: (date_of(e), e["slug"]), reverse=True):
            month = date_of(ed)[:7]
            if month != seen_month:
                try:
                    md = dt.date.fromisoformat(date_of(ed))
                    label = f"{MONTHS[md.month - 1]} {md.year}"
                except ValueError:
                    label = month
                parts.append(f'<span class="nb-month-label">{esc(label)}</span>')
                seen_month = month
            parts.append(story_item(ed, series_cfgs, 2))
        if mode == "open":
            parts += [f'<div class="nb-item" style="color:var(--faint);'
                      f'padding:14px 0 12px;border-bottom:1px solid var(--hair)">'
                      f'<div class="nb-kicker">commissioned</div>'
                      f'<h3>{esc(str(it.get("title", it.get("slug"))))}</h3>'
                      f'<div class="nb-meta"><span>coming</span></div></div>'
                      for it in items if it.get("slug") not in published]
        body = head + (f'<div class="nb-list">{"".join(parts)}</div>' if parts
                       else '<div class="nb-empty"><p>No editions yet.</p></div>')
    else:  # collection, in config order
        rows = [story_item(published[it["slug"]], series_cfgs, 2)
                for it in items if it.get("slug") in published]
        rows += [story_item(e, series_cfgs, 2)
                 for e in eds if not any(it.get("slug") == e["slug"] for it in items)]
        rows += [f'<div class="nb-item" style="color:var(--faint);'
                 f'padding:14px 0 12px;border-bottom:1px solid var(--hair)">'
                 f'<h3>{esc(str(it.get("title", it.get("slug"))))}</h3>'
                 f'<div class="nb-meta"><span>coming</span></div></div>'
                 for it in items if it.get("slug") not in published]
        body = head + f'<div class="nb-list">{"".join(rows)}</div>'

    return page(site, f"{name} — {site['title']}", body, depth=2,
                active="Sections")


def render_tags_index(site, catalog):
    body = '<div class="nb-pagehead"><h1>Tags</h1></div>'
    if catalog["tags"]:
        body += ('<div class="nb-chips" style="flex-wrap:wrap">' + "".join(
            f'<a href="{esc(t)}/">#{esc(t)} · {len(v)}</a>'
            for t, v in catalog["tags"].items()) + "</div>")
    else:
        body += '<div class="nb-empty"><p>No tags yet.</p></div>'
    return page(site, f"Tags — {site['title']}", body, depth=1)


def render_tag_page(site, tag, refs, editions, series_cfgs):
    eds = [editions[tuple(r.split("/", 1))] for r in refs
           if tuple(r.split("/", 1)) in editions]
    body = (f'<div class="nb-pagehead"><h1>#{esc(tag)}</h1>'
            f'<span class="nb-pagehead-facts">{len(eds)} edition'
            f'{"s" if len(eds) != 1 else ""}</span></div>')
    body += '<div class="nb-list">' + "".join(
        story_item(e, series_cfgs, 2) for e in
        sorted(eds, key=lambda e: e["meta"].get("date", ""), reverse=True)) + "</div>"
    return page(site, f"#{tag} — {site['title']}", body, depth=2)


def render_search_page(site):
    body = ('<div class="nb-pagehead"><h1>Search</h1>'
            '<span class="nb-pagehead-facts">the whole library, as it grows'
            "</span></div>"
            '<div class="nb-searchbox"><input id="nb-q" type="search" '
            'placeholder="Fuzzy-search the library…" '
            'aria-label="Search the library" autocomplete="off"></div>'
            '<div class="nb-chips" id="nb-scopes">'
            '<a href="#" class="on" data-scope="all">Everything</a>'
            '<a href="#" data-scope="titles">Titles &amp; deks</a>'
            '<a href="#" data-scope="desks">Desks</a>'
            '<a href="#" data-scope="tags">Tags</a>'
            '<a href="#" data-scope="text">Full text</a></div>'
            '<div class="nb-results-count" id="nb-count"></div>'
            '<div class="nb-results" id="nb-results"></div>')
    return page(site, f"Search — {site['title']}", body, depth=1,
                active="Search")


TEXT_STRIP_RE = re.compile(
    r"<!--[\s\S]*?-->|<script[\s\S]*?</script>|<style[\s\S]*?</style>"
    r"|<[^>]+>", re.I)
BODY_RE = re.compile(r"<body[^>]*>([\s\S]*?)</body>", re.I)


def edition_text(path):
    """Readable text of an edition, for the search index."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    m = BODY_RE.search(raw)
    text = TEXT_STRIP_RE.sub(" ", m.group(1) if m else raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def build_search_index(editions, series_cfgs):
    out = []
    for ed in sorted(editions.values(),
                     key=lambda e: (e["meta"].get("date", ""), e["slug"]),
                     reverse=True):
        meta = ed["meta"]
        cfg = series_cfgs.get(ed["series"], {})
        out.append({
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
            "text": edition_text(ed["file"]),
        })
    return out


# --------------------------------------------------------------------------- #
# Feeds (Atom)
# --------------------------------------------------------------------------- #

FEED_STRIP_RE = re.compile(
    r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", re.I)
HREF_RE = re.compile(r'((?:href|src)=")([^"]+)(")', re.I)


def feed_content_html(path, base_url):
    """Edition body as a feed-safe HTML fragment: scripts/styles stripped,
    URLs absolutized when a base URL is known."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    m = re.search(r"<body[^>]*>([\s\S]*?)</body>", raw, re.I)
    body = FEED_STRIP_RE.sub(" ", m.group(1) if m else raw)

    def absolutize(match):
        pre, url, post = match.groups()
        if base_url and url.startswith("../"):
            return f'{pre}{base_url}/{url.replace("../", "")}{post}'
        if base_url and url.startswith("/"):
            return f"{pre}{base_url}{url}{post}"
        return match.group(0)

    body = HREF_RE.sub(absolutize, body)
    return body if len(body) <= FEED_CONTENT_MAX else ""


def atom_feed(site, base_url, feed_path, title, eds, generated):
    def absolute(path):
        return f"{base_url}{path}" if base_url else path

    entries = []
    for i, ed in enumerate(eds[:FEED_LIMIT]):
        meta = ed["meta"]
        link = absolute(f"/library/{ed['series']}/{ed['slug']}.html")
        updated = f"{meta.get('date', generated.date().isoformat())}T00:00:00Z"
        content = ""
        if i < FEED_CONTENT_LIMIT:
            fragment = feed_content_html(ed["file"], base_url)
            if fragment:
                content = ('\n    <content type="html">' + esc(fragment)
                           + "</content>")
        entries.append(f"""  <entry>
    <title>{esc(str(meta.get('title', ed['slug'])))}</title>
    <link rel="alternate" type="text/html" href="{esc(link)}"/>
    <id>urn:nightly-build:{ed['series']}/{ed['slug']}</id>
    <updated>{updated}</updated>
    <summary>{esc(str(meta.get('dek', '')))}</summary>{content}
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
# Morning email digest (procedural — assembled from nb-meta, no model)
# --------------------------------------------------------------------------- #

def render_email(site_title, date, eds, series_cfgs, base_url):
    """Email-safe digest: inline styles only, no scripts, absolute links."""
    def absolute(path):
        return f"{base_url}{path}" if base_url else path

    eds = sorted(eds, key=lambda e: -e["reading_minutes"])
    total_minutes = sum(e["reading_minutes"] for e in eds)
    rows = []
    for ed in eds:
        meta = ed["meta"]
        cfg = series_cfgs.get(ed["series"], {})
        url = absolute(f"/library/{ed['series']}/{ed['slug']}.html")
        rows.append(f"""
  <div style="border-top:1px solid #D9E2EE;padding:18px 0 14px">
    <div style="font-family:monospace;font-size:11px;letter-spacing:1px;
                text-transform:uppercase;color:#8A5C08">
      {esc(str(meta.get('template', '')))} · {esc(cfg.get('name', ed['series']))}</div>
    <div style="font-family:Georgia,serif;font-size:20px;line-height:1.3;
                margin:6px 0 4px">
      <a href="{esc(url)}" style="color:#161D28;text-decoration:none">
        {esc(str(meta.get('title', ed['slug'])))}</a></div>
    <div style="font-family:Georgia,serif;font-style:italic;font-size:14px;
                color:#4E5866;margin:0 0 6px">{esc(str(meta.get('dek', '')))}</div>
    <div style="font-family:monospace;font-size:11px;color:#8794A4">
      {ed['reading_minutes']} min read · {meta.get('sources', '?')} sources</div>
  </div>""")
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#F4F7FB">
<div style="max-width:600px;margin:0 auto;padding:28px 20px;color:#161D28">
  <div style="font-family:Georgia,serif;font-size:26px;font-weight:bold;
              letter-spacing:-0.5px">{esc(site_title)}<span
              style="color:#8A5C08">.</span></div>
  <div style="font-family:monospace;font-size:12px;color:#4E5866;
              text-transform:uppercase;letter-spacing:1px;margin:4px 0 10px">
    Tonight's build · {esc(date)}</div>
  <div style="font-family:Georgia,serif;font-size:15px;margin:0 0 12px">
    {len(eds)} edition{"s" if len(eds) != 1 else ""} ·
    {total_minutes} minutes of reading, built while you slept.</div>
  {"".join(rows)}
  <div style="border-top:2px solid #161D28;margin-top:16px;padding-top:12px;
              font-family:monospace;font-size:11px;color:#8794A4">
    <a href="{esc(absolute('/') or '/')}" style="color:#935F00">the newsstand</a> ·
    <a href="{esc(absolute('/feed.xml'))}" style="color:#935F00">feed</a> ·
    The Nightly Build</div>
</div>
</body></html>
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


EDITION_ASSET_RE = re.compile(
    r'((?:href|src)="(?:\.\./)*assets/(?:nb\.css|nb\.js|theme\.css))(")')


def copy_editions(editions, out, preview, stamp=""):
    """Editions are canonical on the library branch; the SITE copy is a build
    artifact, so its shared-asset links get the cache-busting stamp."""
    for ed in editions.values():
        dst = os.path.join(out, "library", ed["series"], f"{ed['slug']}.html")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if stamp:
            with open(ed["file"], "r", encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
            write(dst, EDITION_ASSET_RE.sub(rf"\1?v={stamp}\2", raw))
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
        "stamp": asset_stamp(repo),
        "body_class": (' class="nb-front-comfortable"'
                       if site_cfg.get("front") == "comfortable" else ""),
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
    write(os.path.join(out, "search", "index.html"),
          render_search_page(site))
    write(os.path.join(out, "search-index.json"),
          json.dumps(build_search_index(editions, series_cfgs)) + "\n")
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

    # email digests: one per build (permanent) + the latest at a stable path
    # for the morning-mail workflow
    for date in catalog["builds"]:
        eds = [e for e in editions.values() if e["meta"].get("date") == date]
        write(os.path.join(out, "builds", date, "email.html"),
              render_email(site_cfg["title"], date, eds, series_cfgs, base_url))
    latest = max(catalog["builds"], default=None)
    if latest:
        eds = [e for e in editions.values()
               if e["meta"].get("date") == latest]
        write(os.path.join(out, "email-latest.html"),
              render_email(site_cfg["title"], latest, eds, series_cfgs, base_url))
        write(os.path.join(out, "email-latest-subject.txt"),
              f"{site_cfg['title']} — {latest}: {len(eds)} "
              f"edition{'s' if len(eds) != 1 else ''}\n")

    copy_assets(repo, site_cfg, out)
    copy_editions(editions, out, bool(preview_root), site["stamp"])
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
