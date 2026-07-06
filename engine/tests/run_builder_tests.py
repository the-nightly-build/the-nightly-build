#!/usr/bin/env python3
"""
Test suite for engine/build_site.py. Zero test-framework dependencies.

Strategy: assemble temp library checkouts from the fixture editions, run the
builder, and assert on catalog.json and the rendered pages.

Run: python3 engine/tests/run_builder_tests.py
"""
import datetime as dt
import pathlib
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "engine"))

import build_site as B  # noqa: E402
import make_fixtures  # noqa: E402

NOW = dt.datetime(2026, 7, 6, 9, 0, tzinfo=dt.timezone.utc)
PASS, FAIL = 0, []
TESTREPO = make_fixtures.test_repo()


def check(name, condition, detail=""):
    global PASS
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name} {detail}")


def write_edition(root, series, slug, html):
    d = pathlib.Path(root) / "library" / series
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.html").write_text(html)


def brief_for(date):
    return make_fixtures.brief(date)


def make_full_library():
    lib = tempfile.mkdtemp()
    write_edition(lib, "semiconductors", "micron", make_fixtures.dossier())
    write_edition(lib, "ai-briefs", "2026-07-05", brief_for("2026-07-05"))
    write_edition(lib, "ai-briefs", "2026-07-06", brief_for("2026-07-06"))
    return lib


def read(out, *parts):
    return pathlib.Path(out, *parts).read_text()


print("== full build ==")
lib = make_full_library()
out = tempfile.mkdtemp()
catalog = B.build(TESTREPO, lib, out, now=NOW)

check("catalog site title", catalog["site_title"] == "The Nightly Build")
semis = next(s for s in catalog["series"] if s["id"] == "semiconductors")
briefs = next(s for s in catalog["series"] if s["id"] == "ai-briefs")
check("collection series count/total", semis["count"] == 1 and semis["total"] == 5)
check("rolling series count, no total", briefs["count"] == 2 and briefs["total"] is None)
check("editions carry path + position + reading time",
      all("path" in e and "position" in e and "reading_minutes" in e
          for e in catalog["editions"]))
check("editions newest-first",
      catalog["editions"][0]["date"] == "2026-07-06")
check("builds grouped by nb-meta date",
      catalog["builds"] == {"2026-07-06": ["ai-briefs/2026-07-06",
                                           "semiconductors/micron"],
                            "2026-07-05": ["ai-briefs/2026-07-05"]},
      detail=str(catalog["builds"]))
check("tags index", catalog["tags"].get("equity") == ["semiconductors/micron"])

newsstand = read(out, "index.html")
check("newsstand leads with the night's date",
      "Monday, July 6, 2026" in newsstand)
check("newsstand totals the night's reading",
      "min read</span>" in newsstand and "nb-editionline" in newsstand)
check("lead story is the longest read (dossier, 15 min)",
      '<article class="nb-lead"><a href="library/semiconductors/micron.html">'
      in newsstand, detail="lead selection")
check("newsstand has appearance toggle", 'class="nb-appearance"' in newsstand)
check("stories carry section kickers", 'class="nb-kicker"' in newsstand)
check("newsstand links the previous night", 'href="builds/2026-07-05/"' in newsstand)
check("no press-check banner on a real build", "Press check" not in newsstand)
check("menu says Today", ">Today</a>" in newsstand)

check("build page links the previous night",
      "← Sunday, July 5, 2026" in read(out, "builds", "2026-07-06", "index.html"))
check("older night links forward to the newsstand",
      'href="../../">Monday, July 6, 2026 →'
      in read(out, "builds", "2026-07-05", "index.html"))
sections_page = read(out, "series", "index.html")
check("sections page lists desks", 'class="nb-desk' in sections_page
      and "Semiconductors" in sections_page)
check("sections page shows collection progress", "1 of 5" in sections_page)
check("build archive groups by month",
      "July 2026" in read(out, "builds", "index.html"))

series_page = read(out, "series", "semiconductors", "index.html")
check("collection page shows published card", "Micron Technology" in series_page)
check("collection page greys unpublished items",
      series_page.count("coming") == 4, detail=f"count={series_page.count('coming')}")
rolling_page = read(out, "series", "ai-briefs", "index.html")
check("rolling page groups by month", "July 2026" in rolling_page)
check("rolling page reverse-chron",
      rolling_page.find("2026-07-06") < rolling_page.rfind("2026-07-05"))

check("tag page lists tagged edition",
      "Micron Technology" in read(out, "tags", "equity", "index.html"))

feed = ET.fromstring(read(out, "feed.xml"))
NS = "{http://www.w3.org/2005/Atom}"
check("global atom feed has all editions",
      len(feed.findall(f"{NS}entry")) == 3)
first_entry = feed.findall(f"{NS}entry")[0]
content_el = first_entry.find(f"{NS}content")
content_text = content_el.text or "" if content_el is not None else ""
check("newest entries carry full content", "Micron" in content_text)
check("feed content is script-free", "<script" not in content_text)
series_feed = ET.fromstring(read(out, "series", "ai-briefs", "feed.xml"))
check("series feed scoped to series",
      len(series_feed.findall(f"{NS}entry")) == 2)

check("assets copied", all(pathlib.Path(out, "assets", f).is_file()
                           for f in ("nb.js", "nb.css", "theme.css",
                                     "themes/newspaper.css")))
micron_copy = read(out, "library", "semiconductors", "micron.html")
stamp_m = re.search(r"nb\.css\?v=([0-9a-f]+)", micron_copy)
check("edition site copies get cache-busting asset stamps", bool(stamp_m))
stamp = stamp_m.group(1) if stamp_m else ""
check("edition content otherwise untouched",
      micron_copy.replace("?v=" + stamp, "") == make_fixtures.dossier())
check("chrome pages carry the same stamp",
      f"assets/nb.css?v={stamp}" in newsstand)

print("== email digest ==")
email = read(out, "email-latest.html")
check("email digest exists with edition titles",
      "Micron Technology" in email and "Daily brief for 2026-07-06" in email)
check("email digest is latest build only", "2026-07-05" not in email)
check("email digest is inline-only (no scripts, no engine assets)",
      "<script" not in email and "assets/" not in email)
check("email subject line",
      read(out, "email-latest-subject.txt").strip()
      == "The Nightly Build — 2026-07-06: 2 editions")
check("per-build digests are permanent",
      "Daily brief for 2026-07-05" in read(out, "builds", "2026-07-05", "email.html"))

print("== sequence series ==")
seq_repo = str(pathlib.Path(tempfile.mkdtemp()) / "repo")
shutil.copytree(TESTREPO, seq_repo)
sy = pathlib.Path(seq_repo) / "press" / "series" / "semiconductors" / "series.yaml"
sy.write_text(sy.read_text().replace("mode: collection", "mode: sequence"))
seq_lib = tempfile.mkdtemp()
seq_ed = make_fixtures.dossier().replace(
    '"mode": "collection", "order": null', '"mode": "sequence", "order": 1')
write_edition(seq_lib, "semiconductors", "micron", seq_ed)
seq_out = tempfile.mkdtemp()
B.build(seq_repo, seq_lib, seq_out, now=NOW)
seq_page = read(seq_out, "series", "semiconductors", "index.html")
check("sequence page has progress bar", "nb-progress-wide" in seq_page)
check("sequence page numbers items", ">01<" in seq_page and ">05<" in seq_page)
check("sequence page marks continue-here on next item",
      "continue here" in seq_page and seq_page.find("TSMC") < seq_page.find("continue here"))
check("sequence progress on the sections page",
      "1 of 5" in read(seq_out, "series", "index.html"))

print("== press check preview ==")
pc = tempfile.mkdtemp()
draft = (make_fixtures.dossier()
         .replace('"slug": "micron"', '"slug": "tsmc"')
         .replace("Micron Technology: The Scarcest Commodity in AI",
                  "TSMC: The Foundry at the Center of the World"))
write_edition(pc, "semiconductors", "tsmc", draft)
pv_out = tempfile.mkdtemp()
pv_catalog = B.build(TESTREPO, lib, pv_out, preview_root=pc, now=NOW)
pv_index = read(pv_out, "index.html")
check("preview renders identically to production (no banner)",
      "Press check" not in pv_index)
check("preview merges draft with published library",
      "TSMC: The Foundry" in pv_index and "Micron Technology" in pv_index)
check("draft flagged in catalog",
      any(e.get("draft") for e in pv_catalog["editions"]
          if e["slug"] == "tsmc"))
check("published edition not flagged draft",
      not any(e.get("draft") for e in pv_catalog["editions"]
              if e["slug"] == "micron"))
check("draft edition file copied modulo the asset stamp",
      re.sub(r"\?v=[0-9a-f]+", "",
             read(pv_out, "library", "semiconductors", "tsmc.html")) == draft)
check("published edition file untouched",
      "Press check" not in read(pv_out, "library", "semiconductors", "micron.html"))

print("== open series ==")
open_repo = tempfile.mkdtemp()
for sub in ("press", "templates", "engine"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(open_repo) / sub)
wd = pathlib.Path(open_repo) / "press" / "series" / "wildcard"
wd.mkdir()
(wd / "series.yaml").write_text(
    "name: Wildcard\nmode: open\ntemplates: [dossier, chronicle]\n"
    "cadence: weekdays\nautopublish: true\nstrict: false\n"
    "items:\n  - {slug: commissioned-piece, title: On Commission}\n")
open_ed = (make_fixtures.dossier()
           .replace('"series": "semiconductors", "slug": "micron",',
                    '"series": "wildcard", "slug": "the-cuda-moat",')
           .replace('"mode": "collection"', '"mode": "open"'))
open_lib = tempfile.mkdtemp()
write_edition(open_lib, "wildcard", "the-cuda-moat", open_ed)
open_out = tempfile.mkdtemp()
open_catalog = B.build(open_repo, open_lib, open_out, now=NOW)
wc = next(s for s in open_catalog["series"] if s["id"] == "wildcard")
check("open series in catalog with choice list + cadence",
      wc["mode"] == "open" and wc["templates"] == ["dossier", "chronicle"]
      and wc["cadence"] == "weekdays" and wc["total"] is None)
open_page = read(open_out, "series", "wildcard", "index.html")
check("open series page renders reverse-chron with month label",
      "July 2026" in open_page and "the-cuda-moat" in open_page)
check("pending commission shows as coming",
      "On Commission" in open_page and "commissioned" in open_page)
check("open series page shows the template choice list",
      "dossier, chronicle" in open_page)

print("== stale newsstand ==")
stale_out = tempfile.mkdtemp()
B.build(TESTREPO, lib, stale_out,
        now=dt.datetime(2026, 7, 10, 9, 0, tzinfo=dt.timezone.utc))
check("a gap shows the build's true date",
      "Monday, July 6, 2026" in read(stale_out, "index.html"))

print("== theme token parity ==")
theme_css = (REPO / "engine" / "assets" / "themes" / "newspaper.css").read_text()
blocks = re.findall(r"(:root[^{]*|@media[^{]*\{\s*:root[^{]*)\{([^}]*)\}", theme_css)
tokens_per_block = [set(re.findall(r"--([a-z0-9-]+)\s*:", body)) for _, body in blocks]
NON_COLOR = {"serif", "sans", "mono", "radius"}
base_colors = tokens_per_block[0] - NON_COLOR
check("theme has 4 palette blocks", len(tokens_per_block) == 4,
      detail=f"found {len(tokens_per_block)}")
for i, toks in enumerate(tokens_per_block[1:], 1):
    missing = base_colors - toks
    check(f"palette block {i + 1} defines every color token", not missing,
          detail=f"missing {sorted(missing)}")

print("== empty library ==")
empty_out = tempfile.mkdtemp()
B.build(TESTREPO, tempfile.mkdtemp(), empty_out, now=NOW)
empty_index = read(empty_out, "index.html")
check("fresh-fork empty state", "The presses are ready" in empty_index)
check("empty build still renders a sections page",
      'class="nb-desk' in read(empty_out, "series", "index.html"))

print()
print(f"{PASS} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
