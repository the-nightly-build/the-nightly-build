#!/usr/bin/env python3
"""Test suite for the press, with zero framework dependencies.

Strategy: assemble temp library checkouts from fixture articles, run the
builder, and assert on catalog.json and the rendered pages. Chrome
assertions pin the markup contract, and the theme parity check fails the
suite when any palette block misses a token.

Run: python3 engine/tests/run_builder_tests.py
"""

import datetime as dt
import json
import pathlib
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

import _bootstrap
import build_site as B
import make_fixtures
import validate_config as V

REPO = _bootstrap.REPO

NOW = dt.datetime(2026, 7, 6, 9, 0, tzinfo=dt.timezone.utc)
PASS, FAIL = 0, []
TESTREPO = make_fixtures.test_repo()


def check(name, condition, *, detail=""):
    global PASS
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name} {detail}")


def write_article(root, series, *, slug, html):
    d = pathlib.Path(root) / "library" / series
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.html").write_text(html)


def make_full_library():
    lib = tempfile.mkdtemp()
    write_article(lib, "semiconductors", slug="micron", html=make_fixtures.article())
    write_article(
        lib, "ai-briefs", slug="2026-07-05", html=make_fixtures.brief("2026-07-05")
    )
    write_article(
        lib, "ai-briefs", slug="2026-07-06", html=make_fixtures.brief("2026-07-06")
    )
    return lib


def read(out, *parts):
    path = pathlib.Path(out, *parts)
    return path.read_text()


print("== full build ==")
lib = make_full_library()
out = tempfile.mkdtemp()
catalog = B.build(TESTREPO, lib, out=out, now=NOW)

check("catalog site title", catalog["site_title"] == "The Nightly Build")
semis = next(s for s in catalog["series"] if s["id"] == "semiconductors")
briefs = next(s for s in catalog["series"] if s["id"] == "ai-briefs")
check("collection series count/total", semis["count"] == 1 and semis["total"] == 5)
check(
    "rolling series count, no total", briefs["count"] == 2 and briefs["total"] is None
)
check(
    "articles carry path + position + reading time",
    all(
        "path" in e and "position" in e and "reading_minutes" in e
        for e in catalog["articles"]
    ),
)
check("articles newest-first", catalog["articles"][0]["date"] == "2026-07-06")
check(
    "builds grouped by nb-meta date",
    catalog["builds"]
    == {
        "2026-07-06": ["ai-briefs/2026-07-06", "semiconductors/micron"],
        "2026-07-05": ["ai-briefs/2026-07-05"],
    },
    detail=str(catalog["builds"]),
)
check("tags index", catalog["tags"].get("equity") == ["semiconductors/micron"])

print("== catalog protocol 1.3 (network + chrome fields) ==")
check("protocol is 1.3", catalog["protocol"] == "1.3")
check("footer defaults to None when unset", catalog["footer"] is None)
check("upstream repo credited in catalog", catalog["upstream"] == B.UPSTREAM_REPOSITORY)
check("network directory url in catalog", catalog["network_url"] == B.NETWORK_URL)
check(
    "listed by default under opt-out (no network config)",
    catalog.get("network", {}).get("publish") is True,
)
check(
    "repository derived from a Pages project URL",
    B.derive_self_repository(None, "https://alice.github.io/my-press")
    == "alice/my-press",
)
check(
    "explicit repository wins over derivation",
    B.derive_self_repository("Alice/My-Press", "https://x.github.io/y")
    == "Alice/My-Press",
)
check("repository is None when underivable", B.derive_self_repository(None, "") is None)

# A press that opts into the network, built with a Pages URL.
net_repo = pathlib.Path(tempfile.mkdtemp()) / "repo"
shutil.copytree(TESTREPO, net_repo)
pathlib.Path(net_repo, "press", "site.yaml").write_text(
    'title: "Alice\'s Nightly Build"\n'
    'footer: "Read it with your coffee."\n'
    "network:\n"
    "  publish: true\n"
    '  description: "Books, law, and the quiet parts of the news."\n'
)
net_out = tempfile.mkdtemp()
net_catalog = B.build(
    net_repo,
    make_full_library(),
    out=net_out,
    base_url="https://alice.github.io/my-press",
    now=NOW,
)
check(
    "custom footer flows to the catalog",
    net_catalog["footer"] == "Read it with your coffee.",
)
check("repository derived at build time", net_catalog["repository"] == "alice/my-press")
check(
    "network block is publish + description only, no URL",
    net_catalog.get("network")
    == {
        "publish": True,
        "description": "Books, law, and the quiet parts of the news.",
    },
    detail=str(net_catalog.get("network")),
)

# A press that opts out emits only publish:false.
out_repo = pathlib.Path(tempfile.mkdtemp()) / "repo"
shutil.copytree(TESTREPO, out_repo)
pathlib.Path(out_repo, "press", "site.yaml").write_text("network:\n  publish: false\n")
out_catalog = B.build(
    out_repo,
    make_full_library(),
    out=tempfile.mkdtemp(),
    base_url="https://x.github.io/y",
    now=NOW,
)
check(
    "opt-out emits only publish:false",
    out_catalog.get("network") == {"publish": False},
    detail=str(out_catalog.get("network")),
)

newsstand = read(out, "index.html")
check("newsstand leads with the night's date", "Monday, July 6, 2026" in newsstand)
check(
    "newsstand totals the night's reading",
    "min read</span>" in newsstand and "nb-articleline" in newsstand,
)
check(
    "lead cell is the longest read (the article, 15 min)",
    'nb-lead-cell" href="library/semiconductors/micron.html"' in newsstand,
    detail="lead selection",
)
check("newsstand has appearance toggle", 'class="nb-appearance"' in newsstand)
check("stories carry section kickers", 'class="nb-kicker"' in newsstand)
check("cells show the article's source count", ">8 sources</span>" in newsstand)
check("a second cell shows its own source count", ">5 sources</span>" in newsstand)
check("newsstand links the previous night", 'href="builds/2026-07-05/"' in newsstand)
check("no press-check banner on a real build", "Press check" not in newsstand)
check("menu says Today", ">Today</a>" in newsstand)

# Reader chrome: ecosystem links and the footer imprint. The default build has
# no repository (star link omitted) and no footer (default imprint), linked to
# the canonical repo; the network build carries both.
check(
    "default imprint credits the canonical repo",
    f'class="nb-imprint" href="https://github.com/{B.UPSTREAM_REPOSITORY}"'
    in newsstand,
    detail="default imprint missing",
)
check("footer drops the old GitHub link", ">GitHub</a>" not in newsstand)
check(
    "start-your-own recruits to canonical",
    f'href="https://github.com/{B.UPSTREAM_REPOSITORY}" target="_blank" '
    'rel="noopener noreferrer">Start your own' in newsstand,
)
check(
    "hamburger links to the network directory",
    f'href="{B.NETWORK_URL}" target="_blank" '
    'rel="noopener noreferrer">The whole newspaper' in newsstand,
)
check(
    "star link omitted when the repository is unknown",
    "Star on GitHub" not in newsstand,
)
net_front = read(net_out, "index.html")
check(
    "custom footer renders as an unlinked imprint",
    '<span class="nb-imprint">Read it with your coffee.</span>' in net_front,
)
check(
    "star link targets this press when the repository is known",
    'href="https://github.com/alice/my-press" target="_blank" '
    'rel="noopener noreferrer">Star on GitHub' in net_front,
)

check(
    "build page links the previous night",
    "← Sunday, July 5, 2026" in read(out, "builds", "2026-07-06", "index.html"),
)
check(
    "older night links forward to the newsstand",
    'href="../../">Monday, July 6, 2026 →'
    in read(out, "builds", "2026-07-05", "index.html"),
)
sections_page = read(out, "series", "index.html")
check(
    "sections page lists desks",
    'class="nb-desk' in sections_page and "Semiconductors" in sections_page,
)
check("sections page shows collection progress", "1 of 5" in sections_page)
check("build archive groups by month", "July 2026" in read(out, "builds", "index.html"))

series_page = read(out, "series", "semiconductors", "index.html")
check("collection page shows published card", "Micron Technology" in series_page)
check(
    "collection page greys unpublished items",
    series_page.count("coming") == 4,
    detail=f"count={series_page.count('coming')}",
)
rolling_page = read(out, "series", "ai-briefs", "index.html")
check("rolling page groups by month", "July 2026" in rolling_page)
check(
    "rolling page reverse-chron",
    rolling_page.find("2026-07-06") < rolling_page.rfind("2026-07-05"),
)

check(
    "tag page lists tagged article",
    "Micron Technology" in read(out, "tags", "equity", "index.html"),
)

feed = ET.fromstring(read(out, "feed.xml"))
NS = "{http://www.w3.org/2005/Atom}"
check("global atom feed has all articles", len(feed.findall(f"{NS}entry")) == 3)
first_entry = feed.findall(f"{NS}entry")[0]
content_el = first_entry.find(f"{NS}content")
content_text = content_el.text or "" if content_el is not None else ""
check("newest entries carry full content", "Micron" in content_text)
check("feed content is script-free", "<script" not in content_text)
series_feed = ET.fromstring(read(out, "series", "ai-briefs", "feed.xml"))
check("series feed scoped to series", len(series_feed.findall(f"{NS}entry")) == 2)

check(
    "assets copied",
    all(
        pathlib.Path(out, "assets", f).is_file()
        for f in ("nb.js", "nb.css", "theme.css", "themes/newspaper.css")
    ),
)
micron_copy = read(out, "library", "semiconductors", "micron.html")
stamp_m = re.search(r"nb\.css\?v=([0-9a-f]+)", micron_copy)
check("article site copies get cache-busting asset stamps", bool(stamp_m))
stamp = stamp_m.group(1) if stamp_m else ""
check(
    "article content otherwise untouched",
    micron_copy.replace("?v=" + stamp, "") == make_fixtures.article(),
)
check("chrome pages carry the same stamp", f"assets/nb.css?v={stamp}" in newsstand)
index0 = json.loads(read(out, "search-index.json"))[0]
check(
    "search index text is clean prose",
    "<" not in index0["text"] and not index0["text"].startswith("class="),
)
check(
    "sections page never says 'of None'",
    "of None" not in read(out, "series", "index.html"),
)

print("== email digest ==")
email = read(out, "email-latest.html")
check(
    "email digest exists with article titles",
    "Micron Technology" in email and "Daily brief for 2026-07-06" in email,
)
check("email digest is latest build only", "2026-07-05" not in email)
check(
    "email digest is inline-only (no scripts, no engine assets)",
    "<script" not in email and "assets/" not in email,
)
check(
    "email subject line",
    read(out, "email-latest-subject.txt").strip()
    == "The Nightly Build — 2026-07-06: 2 articles",
)
check(
    "per-build digests are permanent",
    "Daily brief for 2026-07-05" in read(out, "builds", "2026-07-05", "email.html"),
)

print("== sequence series ==")
seq_repo = str(pathlib.Path(tempfile.mkdtemp()) / "repo")
shutil.copytree(TESTREPO, seq_repo)
sy = pathlib.Path(seq_repo) / "press" / "series" / "semiconductors" / "series.yaml"
sy.write_text(sy.read_text().replace("mode: collection", "mode: sequence"))
seq_lib = tempfile.mkdtemp()
seq_ed = make_fixtures.article().replace(
    '"mode": "collection", "order": null', '"mode": "sequence", "order": 1'
)
write_article(seq_lib, "semiconductors", slug="micron", html=seq_ed)
seq_out = tempfile.mkdtemp()
B.build(seq_repo, seq_lib, out=seq_out, now=NOW)
seq_page = read(seq_out, "series", "semiconductors", "index.html")
check("sequence page has progress bar", "nb-progress-wide" in seq_page)
check("sequence page numbers items", ">01<" in seq_page and ">05<" in seq_page)
check(
    "sequence page marks continue-here on next item",
    "continue here" in seq_page
    and seq_page.find("TSMC") < seq_page.find("continue here"),
)
check(
    "sequence progress on the sections page",
    "1 of 5" in read(seq_out, "series", "index.html"),
)

print("== press check preview ==")
pc = tempfile.mkdtemp()
draft = (
    make_fixtures.article()
    .replace('"slug": "micron"', '"slug": "tsmc"')
    .replace(
        "Micron Technology: The Scarcest Commodity in AI",
        "TSMC: The Foundry at the Center of the World",
    )
)
write_article(pc, "semiconductors", slug="tsmc", html=draft)
pv_out = tempfile.mkdtemp()
pv_catalog = B.build(TESTREPO, lib, out=pv_out, preview_root=pc, now=NOW)
pv_index = read(pv_out, "index.html")
check(
    "preview renders identically to production (no banner)",
    "Press check" not in pv_index,
)
check(
    "preview merges draft with published library",
    "TSMC: The Foundry" in pv_index and "Micron Technology" in pv_index,
)
check(
    "draft flagged in catalog",
    any(e.get("draft") for e in pv_catalog["articles"] if e["slug"] == "tsmc"),
)
check(
    "published article not flagged draft",
    not any(e.get("draft") for e in pv_catalog["articles"] if e["slug"] == "micron"),
)
check(
    "draft article file copied modulo the asset stamp",
    re.sub(r"\?v=[0-9a-f]+", "", read(pv_out, "library", "semiconductors", "tsmc.html"))
    == draft,
)
check(
    "published article file untouched",
    "Press check" not in read(pv_out, "library", "semiconductors", "micron.html"),
)

print("== open series ==")
open_repo = tempfile.mkdtemp()
for sub in ("press", "templates", "engine"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(open_repo) / sub)
wd = pathlib.Path(open_repo) / "press" / "series" / "wildcard"
wd.mkdir()
(wd / "series.yaml").write_text(
    "name: Wildcard\nmode: open\ntemplates: [article, brief]\n"
    "cadence: weekdays\nautopublish: true\nstrict: false\n"
    "items:\n  - {slug: commissioned-piece, title: On Commission}\n"
)
open_ed = (
    make_fixtures.article()
    .replace(
        '"series": "semiconductors", "slug": "micron",',
        '"series": "wildcard", "slug": "the-cuda-moat",',
    )
    .replace('"mode": "collection"', '"mode": "open"')
)
open_lib = tempfile.mkdtemp()
write_article(open_lib, "wildcard", slug="the-cuda-moat", html=open_ed)
open_out = tempfile.mkdtemp()
open_catalog = B.build(open_repo, open_lib, out=open_out, now=NOW)
wc = next(s for s in open_catalog["series"] if s["id"] == "wildcard")
check(
    "open series in catalog with choice list + cadence",
    wc["mode"] == "open"
    and wc["templates"] == ["article", "brief"]
    and wc["cadence"] == "weekdays"
    and wc["total"] is None,
)
open_page = read(open_out, "series", "wildcard", "index.html")
check(
    "open series page renders reverse-chron with month label",
    "July 2026" in open_page and "the-cuda-moat" in open_page,
)
check(
    "pending commission shows as coming",
    "On Commission" in open_page and "commissioned" in open_page,
)
check("open series page shows the template choice list", "article, brief" in open_page)

print("== stale newsstand ==")
stale_out = tempfile.mkdtemp()
B.build(
    TESTREPO,
    lib,
    out=stale_out,
    now=dt.datetime(2026, 7, 10, 9, 0, tzinfo=dt.timezone.utc),
)
check(
    "a gap shows the build's true date",
    "Monday, July 6, 2026" in read(stale_out, "index.html"),
)

print("== theme token parity ==")
theme_css = (REPO / "engine" / "assets" / "themes" / "newspaper.css").read_text()
blocks = re.findall(r"(:root[^{]*|@media[^{]*\{\s*:root[^{]*)\{([^}]*)\}", theme_css)
tokens_per_block = [set(re.findall(r"--([a-z0-9-]+)\s*:", body)) for _, body in blocks]
NON_COLOR = {"serif", "sans", "mono", "radius"}
base_colors = tokens_per_block[0] - NON_COLOR
check(
    "theme has 4 palette blocks",
    len(tokens_per_block) == 4,
    detail=f"found {len(tokens_per_block)}",
)
for i, toks in enumerate(tokens_per_block[1:], 1):
    missing = base_colors - toks
    check(
        f"palette block {i + 1} defines every color token",
        not missing,
        detail=f"missing {sorted(missing)}",
    )

print("== empty library ==")
empty_out = tempfile.mkdtemp()
B.build(TESTREPO, tempfile.mkdtemp(), out=empty_out, now=NOW)
empty_index = read(empty_out, "index.html")
check("fresh-fork empty state", "The presses are ready" in empty_index)
check(
    "empty build still renders a sections page",
    'class="nb-desk' in read(empty_out, "series", "index.html"),
)

print("== press trusted external assets ==")
# validate_config requires https + SRI on every declared asset
no_sri = []
V.check_site_assets({"scripts": [{"url": "https://cdn.example/x.js"}]}, errors=no_sri)
check("asset without integrity is rejected", any("integrity" in e for e in no_sri))
not_https = []
V.check_site_assets(
    {"scripts": [{"url": "http://cdn.example/x.js", "integrity": "sha384-AAA"}]},
    errors=not_https,
)
check("non-https asset url is rejected", any("https" in e for e in not_https))
ok_assets = []
V.check_site_assets(
    {
        "scripts": [
            {"url": "https://cdn.example/x.js", "integrity": "sha384-A", "defer": True}
        ],
        "styles": [{"url": "https://cdn.example/x.css", "integrity": "sha512-B"}],
    },
    errors=ok_assets,
)
check("pinned + SRI assets validate", ok_assets == [])

# render emits SRI + crossorigin, and nothing when nothing is declared
tag_html = B.render_assets_html(
    {"scripts": [{"url": "https://cdn.example/x.js", "integrity": "sha384-A"}]}
)
check(
    "rendered asset carries integrity + crossorigin",
    'integrity="sha384-A"' in tag_html and 'crossorigin="anonymous"' in tag_html,
)
check("no assets renders nothing", B.render_assets_html(None) == "")

# a real build injects the declared asset into chrome pages AND articles
assets_repo = tempfile.mkdtemp()
shutil.copytree(TESTREPO, assets_repo, dirs_exist_ok=True)
site_yaml = pathlib.Path(assets_repo) / "press" / "site.yaml"
site_yaml.write_text(
    site_yaml.read_text()
    + "assets:\n  scripts:\n    - url: https://cdn.example/hi.js\n"
    + "      integrity: sha384-TESTHASH\n"
)
assets_out = tempfile.mkdtemp()
B.build(assets_repo, make_full_library(), out=assets_out, now=NOW)
injected = 'src="https://cdn.example/hi.js"'
check(
    "declared asset injected into chrome page",
    injected in read(assets_out, "index.html"),
)
check(
    "declared asset injected into article copy",
    injected in read(assets_out, "library", "semiconductors", "micron.html"),
)

print()
print(f"{PASS} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
