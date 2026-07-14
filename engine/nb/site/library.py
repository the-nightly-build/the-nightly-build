"""What the press and the library hold: config, articles, and their order.

Everything the builder renders starts here. A published article is an HTML
file under library/<series>/<slug>.html carrying an nb-meta block; a series
is a folder under press/series. This module turns that on-disk state into
the article dicts every renderer reads, and nothing here emits markup.
"""

import html
import os
import re
import sys

from nb import meta as nb_meta

try:
    import yaml
except ImportError:
    sys.stderr.write("build_site.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

WORDS_PER_MINUTE = 230

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
