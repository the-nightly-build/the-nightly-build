#!/usr/bin/env python3
"""Generate the fixture articles and fixture repos used by every suite.

The suites never read the repo's shipped configuration because forks
replace it during setup, and the tests must stay green on any fork.
Instead test_repo() fabricates a complete press with two fixture series
(semiconductors, ai-briefs) on top of the real templates and engine
assets, so what the tests exercise is the shipped machinery.
"""

import pathlib
import re
import shutil
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent.parent

SEMICONDUCTORS_YAML = """\
name: Semiconductors
mode: collection
template: article
prompt: prompt.md
autopublish: true
strict: false
min_sources: 8
tags:
  equity: ../_tags/equity.md
consult:
  - https://www.sec.gov/
items:
  - slug: micron
    title: Micron Technology
    tags: [equity]
    prompt: "Emphasize the HBM supply-agreement structure and the memory-cycle debate."
  - slug: tsmc
    title: TSMC
    tags: [equity]
  - slug: asml
    title: ASML
    tags: [equity]
  - slug: sk-hynix
    title: SK Hynix
    tags: [equity]
  - slug: nvidia
    title: Nvidia
    tags: [equity]
"""

AI_BRIEFS_YAML = """\
name: AI & Semiconductors
mode: rolling
template: brief
prompt: prompt.md
autopublish: true
strict: false
min_sources: 5
cadence: daily
"""

SITE_YAML = """\
title: "The Nightly Build"
theme: engine/assets/themes/newspaper.css
appearance: auto
"""


def test_repo():
    # A temp repo with the fixture series plus the real templates and assets.
    root = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(REPO / "templates", root / "templates")
    shutil.copytree(REPO / "engine" / "assets", root / "engine" / "assets")
    (root / "press" / "series").mkdir(parents=True)
    (root / "press" / "site.yaml").write_text(SITE_YAML)
    semis = root / "press" / "series" / "semiconductors"
    semis.mkdir(parents=True)
    (semis / "series.yaml").write_text(SEMICONDUCTORS_YAML)
    (semis / "prompt.md").write_text("Deep dives on the semiconductor supply chain.\n")
    briefs = root / "press" / "series" / "ai-briefs"
    briefs.mkdir(parents=True)
    (briefs / "series.yaml").write_text(AI_BRIEFS_YAML)
    (briefs / "prompt.md").write_text("A nightly brief on AI and semiconductors.\n")
    tags = root / "press" / "series" / "_tags"
    tags.mkdir()
    (tags / "equity.md").write_text("Frame companies for a public-market reader.\n")
    return str(root)


FIX = pathlib.Path(__file__).parent / "fixtures"
FIX.mkdir(parents=True, exist_ok=True)

LOREM = (
    "The memory industry operates on a brutal capacity cycle that has bankrupted "
    "dozens of firms over four decades, and understanding that cycle is the "
    "precondition for judging any single company inside it. "
)


def article():
    sec_defs = [
        ("orientation", "Orientation", 3),
        ("memory-economics", "Memory economics 101", 8),
        ("microns-position", "Micron's position", 8),
        ("bull-versus-bear", "Bull versus bear", 6),
        ("go-deeper", "Go deeper", 3),
    ]
    ci = 0
    body = []
    for sid, title, paras in sec_defs:
        ps = []
        for _ in range(paras):
            n = (ci % 8) + 1
            ci += 1
            ps.append(
                f'<p>{LOREM * 6}<sup class="nb-cite"><a href="#s{n}">{n}</a></sup></p>'
            )
        body.append(
            f'<section data-nb-section="{sid}"><h2>{title}</h2>{"".join(ps)}</section>'
        )

    src = []
    for i in range(1, 9):
        req = ' data-nb-required="mu-10k-2025"' if i == 1 else ""
        href = (
            "https://www.sec.gov/filings/mu-10k"
            if i == 2
            else f"https://example.org/src{i}"
        )
        src.append(
            f'<li id="s{i}"><span>Source {i}</span> '
            f'<a data-nb-source{req} href="{href}">link</a></li>'
        )

    meta = """{
  "protocol": "1.0", "series": "semiconductors", "slug": "micron",
  "template": "article",
  "title": "Micron Technology: The Scarcest Commodity in AI",
  "mode": "collection", "order": null, "date": "2026-07-06", "tags": ["equity"],
  "sources": 8, "words": 5400, "reading_minutes": 15,
  "dek": "How a cyclical commodity maker became the AI era's bottleneck.",
  "harness": "test-fixture", "model": "claude-fable-5"
}"""
    chart = (
        '{"type":"bar","labels":["FY23","FY24","FY25"],'
        '"series":[{"name":"Revenue $B","values":[15.5,25.1,37.4]}]}'
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Micron Technology</title>
<link href="https://fonts.googleapis.com/css2?family=Newsreader&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="../../assets/theme.css">
<link rel="stylesheet" href="../../assets/nb.css">
<script defer src="../../assets/nb.js"></script>
<script type="application/json" id="nb-meta">
{meta}
</script>
<style>body{{font-family:serif}}</style>
</head><body>
<article>
{"".join(body)}
<figure>
<script type="application/json" data-nb-chart>
{chart}
</script>
</figure>
<section data-nb-section="sources"><h2>Sources</h2><ol>{"".join(src)}</ol></section>
</article>
</body></html>"""


def brief(date="2026-07-06"):
    items = []
    for i in range(1, 6):
        items.append(
            f'<div data-nb-item><span class="tag">topic{i}</span>'
            f"<h4>Development number {i} happened today"
            f'<sup class="nb-cite"><a href="#s{i}">{i}</a></sup></h4>'
            f"<p>Two sentences of what happened and the immediate context around it. "
            f"The specifics are grounded in the cited source.</p>"
            f"<p data-nb-why><b>Why it matters</b> — it moves the larger story we track.</p>"
            f"</div>"
        )
    src = "".join(
        f'<li id="s{i}"><a data-nb-source href="https://example.org/news{i}">src</a></li>'
        for i in range(1, 6)
    )
    meta = f"""{{
  "protocol": "1.0", "series": "ai-briefs", "slug": "{date}",
  "template": "brief", "title": "Daily brief for {date}",
  "mode": "rolling", "order": null, "date": "{date}", "tags": [],
  "sources": 5, "words": 300, "reading_minutes": 5,
  "dek": "Five items, each with why it matters.",
  "harness": "test-fixture", "model": "claude-fable-5"
}}"""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Brief {date}</title>
<script type="application/json" id="nb-meta">
{meta}
</script>
</head><body>
<section data-nb-section="items">{"".join(items)}</section>
<section data-nb-section="sources"><ol>{src}</ol></section>
</body></html>"""


def _count_words(body_html):
    text = re.sub(r"<[^>]+>", " ", body_html)
    return len(re.findall(r"\S+", text))


def _meta(series, slug, *, template, title, mode, order, words, n_sources):
    return f"""{{
  "protocol": "1.0", "series": "{series}", "slug": "{slug}",
  "template": "{template}", "title": "{title}",
  "mode": "{mode}", "order": {order}, "date": "2026-07-06", "tags": [],
  "sources": {n_sources}, "words": {words},
  "reading_minutes": {max(1, round(words / 230))},
  "dek": "A one-sentence teaser for the newsstand card.",
  "harness": "test-fixture", "model": "claude-fable-5"
}}"""


def _page(title, *, meta, body):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script defer src="../../assets/nb.js"></script>
<script type="application/json" id="nb-meta">
{meta}
</script>
</head><body class="nb-article">
{body}
</body></html>"""


def _sources(n):
    return (
        '<section class="nb-sources" data-nb-section="sources"><h2>Sources</h2><ol>'
        + "".join(
            f'<li id="s{i}"><a data-nb-source '
            f'href="https://example.org/src{i}">link</a></li>'
            for i in range(1, n + 1)
        )
        + "</ol></section>"
    )


def _cited_paras(count, n_sources, *, start=0):
    ps = []
    for k in range(count):
        n = ((start + k) % n_sources) + 1
        ps.append(
            f'<p>{LOREM * 6}<sup class="nb-cite"><a href="#s{n}">{n}</a></sup></p>'
        )
    return "".join(ps)


def chronicle():
    events = "".join(
        f'<li class="nb-tl-event"><span class="nb-tl-date">19{70 + i}</span>'
        f"<h3>Event {i}"
        f'<sup class="nb-cite"><a href="#s{(i % 8) + 1}">{(i % 8) + 1}</a></sup></h3>'
        f"<p>{LOREM * 3}</p></li>"
        for i in range(8)
    )
    body = (
        '<section data-nb-section="orientation"><h2>Orientation</h2>'
        f"{_cited_paras(4, 8, start=0)}</section>"
        '<section data-nb-section="timeline"><h2>The timeline</h2>'
        f'<ol class="nb-timeline">{events}</ol></section>'
        '<section data-nb-section="echoes"><h2>Echoes today</h2>'
        f"{_cited_paras(4, 8, start=4)}</section>"
        '<section data-nb-section="go-deeper"><h2>Go deeper</h2>'
        f"{_cited_paras(1, 8, start=2)}</section>" + _sources(8)
    )
    meta = _meta(
        "histories",
        "unix",
        template="article",
        title="A History of Unix",
        mode="collection",
        order="null",
        words=_count_words(body),
        n_sources=8,
    )
    return _page("A History of Unix", meta=meta, body=body)


if __name__ == "__main__":
    (FIX / "valid-article.html").write_text(article())
    (FIX / "valid-brief.html").write_text(brief())
    (FIX / "valid-chronicle.html").write_text(chronicle())
    print("fixtures written:", sorted(p.name for p in FIX.iterdir()))
