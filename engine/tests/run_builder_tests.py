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


def snippet(haystack, needle=None, *, width=240):
    text = haystack if isinstance(haystack, str) else str(haystack)
    if needle:
        i = text.find(needle if isinstance(needle, str) else str(needle))
        if i != -1:
            lo = max(0, i - width // 2)
            hi = i + len(str(needle)) + width // 2
            return ("…" if lo else "") + text[lo:hi] + ("…" if hi < len(text) else "")
    return text[:width] + ("…" if len(text) > width else "")


def check(name, condition, *, detail="", needle=None, haystack=None):
    global PASS
    if condition:
        PASS += 1
        print(f"  ok   {name}")
        return
    FAIL.append(name)
    print(f"  FAIL {name}")
    if needle is not None:
        print(f"        looked for: {needle!r}")
    if haystack is not None:
        print(f"        in: {snippet(haystack, needle)}")
    if detail:
        print(f"        {detail}")


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


def find_text(elem, path):
    node = elem.find(path)
    assert node is not None, f"missing element: {path}"
    return node.text or ""


def asset_stamp_of(page_html):
    m = re.search(r"nb\.css\?v=([0-9a-f]+)", page_html)
    assert m is not None, "no asset stamp in page"
    return m.group(1)


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

print("== catalog protocol 1.3 (directory + chrome fields) ==")
check("protocol is 1.3", catalog["protocol"] == "1.3")
check("footer defaults to None when unset", catalog["footer"] is None)
check("upstream repo credited in catalog", catalog["upstream"] == B.UPSTREAM_REPOSITORY)
check("directory directory url in catalog", catalog["directory_url"] == B.DIRECTORY_URL)
check(
    "listed by default under opt-out (no directory config)",
    catalog.get("directory", {}).get("publish") is True,
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

# A press that opts into the directory, built with a Pages URL.
net_repo = pathlib.Path(tempfile.mkdtemp()) / "repo"
shutil.copytree(TESTREPO, net_repo)
pathlib.Path(net_repo, "press", "site.yaml").write_text(
    'title: "Alice\'s Nightly Build"\n'
    'footer: "Read it with your coffee."\n'
    "directory:\n"
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
    "directory block is publish + description only, no URL",
    net_catalog.get("directory")
    == {
        "publish": True,
        "description": "Books, law, and the quiet parts of the news.",
    },
    detail=str(net_catalog.get("directory")),
)

# A press that opts out emits only publish:false.
out_repo = pathlib.Path(tempfile.mkdtemp()) / "repo"
shutil.copytree(TESTREPO, out_repo)
pathlib.Path(out_repo, "press", "site.yaml").write_text(
    "directory:\n  publish: false\n"
)
out_catalog = B.build(
    out_repo,
    make_full_library(),
    out=tempfile.mkdtemp(),
    base_url="https://x.github.io/y",
    now=NOW,
)
check(
    "opt-out emits only publish:false",
    out_catalog.get("directory") == {"publish": False},
    detail=str(out_catalog.get("directory")),
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
# the canonical repo; the directory build carries both.
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
    "hamburger links to the directory directory",
    f'href="{B.DIRECTORY_URL}" target="_blank" '
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
    "sections page lists series",
    'class="nb-series' in sections_page and "Semiconductors" in sections_page,
)
check(
    "sections page shows collection published count",
    "1 published" in sections_page and "1 of 5" not in sections_page,
    haystack=sections_page,
    needle="1 published",
)
check("build archive groups by month", "July 2026" in read(out, "builds", "index.html"))

series_page = read(out, "series", "semiconductors", "index.html")
check("collection page shows published card", "Micron Technology" in series_page)
check(
    "collection page renders no placeholder for unpublished items",
    series_page.count("coming") == 0 and "commissioned" not in series_page,
    haystack=series_page,
    needle="coming",
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
check(
    "sequence page numbers published items in config order",
    ">01<" in seq_page and ">05<" not in seq_page,
    haystack=seq_page,
    needle=">01<",
)
check(
    "sequence page renders no placeholder for unpublished items",
    "nb-seq-unpub" not in seq_page
    and "continue here" not in seq_page
    and "nb-progress-wide" not in seq_page,
    haystack=seq_page,
    needle="nb-seq-unpub",
)
check(
    "sequence sections page shows published count, not progress",
    "1 published" in (secs := read(seq_out, "series", "index.html"))
    and "1 of 5" not in secs,
    haystack=secs,
    needle="1 published",
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
    "open series renders no placeholder for a pending commission",
    "On Commission" not in open_page and "commissioned" not in open_page,
    haystack=open_page,
    needle="On Commission",
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
    'class="nb-series' in read(empty_out, "series", "index.html"),
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

print("== nb-meta reader requires the typed block ==")
# The proof only recognizes <script type="application/json" id="nb-meta">;
# the builder must read the same block, so an untyped decoy placed first
# (invisible to check.py) can never override title/date/series/slug.
decoy_dir = pathlib.Path(tempfile.mkdtemp())
decoy_file = decoy_dir / "decoy.html"
decoy_file.write_text(
    "<!DOCTYPE html><html><head>"
    '<script id="nb-meta">{"series":"EVIL","slug":"evil"}</script>'
    '<script type="application/json" id="nb-meta">'
    '{"series":"semiconductors","slug":"micron","date":"2026-07-06"}'
    "</script></head><body></body></html>"
)
decoy_meta = B.read_meta(str(decoy_file))
check(
    "read_meta ignores an untyped decoy and reads the typed block",
    decoy_meta is not None and decoy_meta.get("series") == "semiconductors",
    detail=str(decoy_meta),
)

print("== theme edit busts the asset stamp ==")
# The ?v= stamp must change when the resolved theme.css changes, or a theme
# swap leaves returning readers on the cached old look.
theme_repo = pathlib.Path(tempfile.mkdtemp()) / "repo"
shutil.copytree(TESTREPO, theme_repo)
B.build(str(theme_repo), make_full_library(), out=(t1 := tempfile.mkdtemp()), now=NOW)
stamp_before = asset_stamp_of(read(t1, "index.html"))
theme_file = theme_repo / "engine" / "assets" / "themes" / "newspaper.css"
theme_file.write_text(theme_file.read_text() + "\n:root{--nb-test-token:1}\n")
B.build(str(theme_repo), make_full_library(), out=(t2 := tempfile.mkdtemp()), now=NOW)
stamp_after = asset_stamp_of(read(t2, "index.html"))
check(
    "a theme edit changes the cache-busting stamp",
    stamp_before != stamp_after,
    detail=f"{stamp_before} == {stamp_after}",
)

print("== furniture concatenates into theme.css and busts the stamp ==")
# copy_assets folds every CSS owner — the theme, shared press furniture, and each
# template's bespoke furniture.css — into the single assets/theme.css, and the
# stamp must fold in the same owners so a furniture edit reaches the reader.
furn_repo = pathlib.Path(tempfile.mkdtemp()) / "repo"
shutil.copytree(TESTREPO, furn_repo)
shared_css = furn_repo / "press" / "furniture" / "styles.css"
shared_css.parent.mkdir(parents=True)
shared_css.write_text(".rs-shared-furniture{color:rebeccapurple}\n")
tpl_css = furn_repo / "templates" / "article" / "furniture.css"
tpl_css.write_text(".rs-article-furniture{color:seagreen}\n")
furn_out = tempfile.mkdtemp()
B.build(str(furn_repo), make_full_library(), out=furn_out, now=NOW)
theme_out = read(furn_out, "assets", "theme.css")
check(
    "theme.css carries the base palette",
    "--bg" in theme_out,
    haystack=theme_out,
    needle="--bg",
)
check(
    "theme.css carries the shared press furniture",
    ".rs-shared-furniture" in theme_out,
    haystack=theme_out,
    needle=".rs-shared-furniture",
)
check(
    "theme.css carries the template's bespoke furniture",
    ".rs-article-furniture" in theme_out,
    haystack=theme_out,
    needle=".rs-article-furniture",
)
furn_stamp_before = asset_stamp_of(read(furn_out, "index.html"))
tpl_css.write_text(".rs-article-furniture{color:crimson}\n")
furn_out2 = tempfile.mkdtemp()
B.build(str(furn_repo), make_full_library(), out=furn_out2, now=NOW)
check(
    "editing a furniture.css changes the cache-busting stamp",
    furn_stamp_before != asset_stamp_of(read(furn_out2, "index.html")),
)

print("== dateless article does not blank the newsstand ==")
# A missing date must not win the 'latest' sort or leave the front page empty
# next to a real dated article; both bucket under the same 'unknown' sentinel.
dateless_lib = tempfile.mkdtemp()
write_article(
    dateless_lib, "semiconductors", slug="micron", html=make_fixtures.article()
)
undated = (
    make_fixtures.article()
    .replace('"slug": "micron"', '"slug": "tsmc"')
    .replace('"date": "2026-07-06", ', "")
    .replace("Micron Technology: The Scarcest Commodity in AI", "TSMC (undated draft)")
)
write_article(dateless_lib, "semiconductors", slug="tsmc", html=undated)
dl_out = tempfile.mkdtemp()
dl_catalog = B.build(TESTREPO, dateless_lib, out=dl_out, now=NOW)
dl_index = read(dl_out, "index.html")
check(
    "newsstand still leads with the real dated article",
    "Micron Technology" in dl_index and "No articles this night" not in dl_index,
)
check(
    "a real date wins 'latest' over the dateless bucket",
    sorted(dl_catalog["builds"], key=B.date_sort_key)[-1] == "2026-07-06",
    detail=str(list(dl_catalog["builds"])),
)
check(
    "the dateless article still gets its own build page",
    "TSMC (undated draft)" in read(dl_out, "builds", "unknown", "index.html"),
)

print("== atom feed ids are per-paper unique and carry an author ==")
# Two papers must never emit byte-identical feed/entry ids; RFC 4287 wants an
# author. xml.etree parsing here doubles as the well-formedness (xmllint) check.
feed_a = B.atom_feed(
    "https://alice.github.io/paper-a", "feed.xml", title="A", eds=[], generated=NOW
)
feed_b = B.atom_feed(
    "https://alice.github.io/paper-b", "feed.xml", title="B", eds=[], generated=NOW
)
root_a, root_b = ET.fromstring(feed_a), ET.fromstring(feed_b)
id_a, id_b = find_text(root_a, f"{NS}id"), find_text(root_b, f"{NS}id")
check(
    "two papers on one host get distinct feed ids",
    id_a != id_b and id_a.startswith("tag:alice.github.io,"),
    detail=f"{id_a} / {id_b}",
)
author_a = root_a.find(f"{NS}author/{NS}name")
check(
    "feed carries an author name from the site title",
    author_a is not None and author_a.text == "A",
)
pa_out, pb_out = tempfile.mkdtemp(), tempfile.mkdtemp()
B.build(
    TESTREPO, make_full_library(), out=pa_out, base_url="https://a.example", now=NOW
)
B.build(
    TESTREPO, make_full_library(), out=pb_out, base_url="https://b.example", now=NOW
)
entry_a = find_text(ET.fromstring(read(pa_out, "feed.xml")), f"{NS}entry/{NS}id")
entry_b = find_text(ET.fromstring(read(pb_out, "feed.xml")), f"{NS}entry/{NS}id")
check(
    "same series/slug on two papers get distinct entry ids",
    entry_a != entry_b and "a.example" in entry_a and "b.example" in entry_b,
    detail=f"{entry_a} / {entry_b}",
)

print("== hostile slug/series/tag are escaped or refused ==")
# series/slug flow raw from library dir/file names; a quote/ampersand/angle
# must not break an href attribute or the Atom <id> text.
hostile = {
    "series": 'a"&b',
    "slug": 'c"&d',
    "reading_minutes": 3,
    "meta": {"title": "T", "dek": "d", "sources": 2},
}
item_html, lead_html = B.story_item(hostile, {}), B.lead_cell(hostile, {})
check(
    "story_item escapes a hostile href",
    'library/a"&b/c"&d' not in item_html and "a&quot;&amp;b/c&quot;&amp;d" in item_html,
)
check(
    "lead_cell escapes a hostile href",
    'library/a"&b/c"&d' not in lead_html and "a&quot;&amp;b/c&quot;&amp;d" in lead_html,
)
hostile_dir = pathlib.Path(tempfile.mkdtemp())
(hostile_dir / "x.html").write_text("<html><body><p>hi</p></body></html>")
hostile_ed = {
    "series": 'a"&b',
    "slug": 'c"&d',
    "file": str(hostile_dir / "x.html"),
    "reading_minutes": 3,
    "meta": {"title": "T", "dek": "d", "date": "2026-07-06"},
}
hostile_feed = B.atom_feed("", "feed.xml", title="T", eds=[hostile_ed], generated=NOW)
hostile_id = find_text(ET.fromstring(hostile_feed), f"{NS}entry/{NS}id")
check(
    "atom entry id with a hostile slug/series stays well-formed",
    hostile_id == 'urn:nightly-build:library/a"&b/c"&d',
    detail=hostile_id,
)

# tag path traversal is refused; a nested tag renders at its true depth.
check("is_safe_tag rejects parent-traversal", not B.is_safe_tag("../../escape"))
check("is_safe_tag rejects an absolute path", not B.is_safe_tag("/etc/passwd"))
check("is_safe_tag rejects a backslash", not B.is_safe_tag("a\\b"))
check("is_safe_tag accepts a plain tag", B.is_safe_tag("equity"))
check("is_safe_tag accepts a nested tag", B.is_safe_tag("markets/equity"))
evil_lib = tempfile.mkdtemp()
write_article(
    evil_lib,
    "semiconductors",
    slug="micron",
    html=make_fixtures.article().replace(
        '"tags": ["equity"]', '"tags": ["../../pwned"]'
    ),
)
evil_out = pathlib.Path(tempfile.mkdtemp()) / "site"
evil_catalog = B.build(TESTREPO, evil_lib, out=str(evil_out), now=NOW)
check(
    "traversal tag dropped from the catalog", "../../pwned" not in evil_catalog["tags"]
)
check(
    "traversal tag created no directory outside --out",
    not (evil_out.parent / "pwned").exists(),
)
nested_lib = tempfile.mkdtemp()
write_article(
    nested_lib,
    "semiconductors",
    slug="micron",
    html=make_fixtures.article().replace(
        '"tags": ["equity"]', '"tags": ["markets/equity"]'
    ),
)
nested_out = tempfile.mkdtemp()
B.build(TESTREPO, nested_lib, out=nested_out, now=NOW)
nested_page = read(nested_out, "tags", "markets", "equity", "index.html")
check(
    "a nested tag page links assets at its true depth-3 path",
    "../../../assets/nb.css" in nested_page,
)

print("== email digest routes sources through source_label ==")
em = read(dl_out, "email-latest.html")
check("email shows a well-formed source count", "8 sources" in em)
bad_lib = tempfile.mkdtemp()
write_article(
    bad_lib,
    "semiconductors",
    slug="micron",
    html=make_fixtures.article().replace('"sources": 8,', '"sources": "<b>x</b>",'),
)
bad_out = tempfile.mkdtemp()
B.build(TESTREPO, bad_lib, out=bad_out, now=NOW)
check(
    "a non-int sources value never reaches the reader raw",
    "<b>x</b>" not in read(bad_out, "email-latest.html"),
)

print()
print(f"{PASS} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
