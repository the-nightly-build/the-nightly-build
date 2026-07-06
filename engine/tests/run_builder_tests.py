#!/usr/bin/env python3
"""
Test suite for engine/build_site.py. Zero test-framework dependencies.

Strategy: assemble temp library checkouts from the fixture editions, run the
builder, and assert on catalog.json and the rendered pages.

Run: python3 engine/tests/run_builder_tests.py
"""
import datetime as dt
import pathlib
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
catalog = B.build(str(REPO), lib, out, now=NOW)

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
check("newsstand says tonight", "Tonight’s build" in newsstand)
check("newsstand counts tonight's editions", "2 editions" in newsstand)
check("lead card is the longest read (dossier, 15 min)",
      'nb-card nb-card-lead" href="library/semiconductors/micron.html"' in newsstand,
      detail="lead selection")
check("newsstand has appearance toggle", 'class="nb-appearance"' in newsstand)
check("newsstand has series strips", 'class="nb-strip"' in newsstand)
check("newsstand has date navigator", 'href="builds/2026-07-05/"' in newsstand)
check("no press-check banner on a real build", "Press check" not in newsstand)

check("build page exists with prev pager",
      'href="../2026-07-05/">← 2026-07-05' in read(out, "builds", "2026-07-06", "index.html"))
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
series_feed = ET.fromstring(read(out, "series", "ai-briefs", "feed.xml"))
check("series feed scoped to series",
      len(series_feed.findall(f"{NS}entry")) == 2)

check("assets copied", all(pathlib.Path(out, "assets", f).is_file()
                           for f in ("nb.js", "nb.css", "theme.css",
                                     "themes/newspaper.css")))
check("editions copied verbatim",
      read(out, "library", "semiconductors", "micron.html")
      == make_fixtures.dossier())

print("== sequence series ==")
seq_repo = tempfile.mkdtemp()
for sub in ("series", "templates"):
    shutil.copytree(REPO / sub, pathlib.Path(seq_repo) / sub)
shutil.copytree(REPO / "engine" / "assets",
                pathlib.Path(seq_repo) / "engine" / "assets")
shutil.copyfile(REPO / "site.yaml", pathlib.Path(seq_repo) / "site.yaml")
sy = pathlib.Path(seq_repo) / "series" / "semiconductors" / "series.yaml"
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
check("newsstand strip shows continue target",
      "continue: TSMC" in read(seq_out, "index.html"))

print("== press check preview ==")
pc = tempfile.mkdtemp()
draft = (make_fixtures.dossier()
         .replace('"slug": "micron"', '"slug": "tsmc"')
         .replace("Micron Technology: The Scarcest Commodity in AI",
                  "TSMC: The Foundry at the Center of the World"))
write_edition(pc, "semiconductors", "tsmc", draft)
pv_out = tempfile.mkdtemp()
pv_catalog = B.build(str(REPO), lib, pv_out, preview_root=pc, now=NOW)
pv_index = read(pv_out, "index.html")
check("preview banners the site", "Press check" in pv_index)
check("preview merges draft with published library",
      "TSMC: The Foundry" in pv_index and "Micron Technology" in pv_index)
check("draft flagged in catalog",
      any(e.get("draft") for e in pv_catalog["editions"]
          if e["slug"] == "tsmc"))
check("published edition not flagged draft",
      not any(e.get("draft") for e in pv_catalog["editions"]
              if e["slug"] == "micron"))
check("draft edition file carries the banner",
      "Press check" in read(pv_out, "library", "semiconductors", "tsmc.html"))
check("published edition file untouched",
      "Press check" not in read(pv_out, "library", "semiconductors", "micron.html"))

print("== empty library ==")
empty_out = tempfile.mkdtemp()
B.build(str(REPO), tempfile.mkdtemp(), empty_out, now=NOW)
empty_index = read(empty_out, "index.html")
check("fresh-fork empty state", "The presses are ready" in empty_index)
check("empty state still lists configured series", "nb-strip" in empty_index)

print()
print(f"{PASS} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
