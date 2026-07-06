#!/usr/bin/env python3
"""
Test suite for engine/check.py. Zero test-framework dependencies.

Strategy: generate valid fixtures, then derive each failure case by mutating the
valid edition, asserting the exact finding code appears (and that the valid cases
are BLOCK-clean). PR mode is tested against a real throwaway git repo.

Run: python3 engine/tests/run_tests.py
"""
import json
import pathlib
import re as _re
import shutil
import subprocess
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "engine"))

import check as C  # noqa: E402
import make_fixtures  # noqa: E402

TODAY = "2026-07-06"
PASS, FAIL = 0, []
# tests never read the shipped series configs — forks clear those on setup
TESTREPO = make_fixtures.test_repo()


def run_local(html_text, series, slug=None, library=None, repo=None, today=TODAY):
    """Write html to a temp file laid out as library/<series>/<slug>.html and check."""
    repo = repo or TESTREPO
    tmp = tempfile.mkdtemp()
    slug = slug or "micron"
    d = pathlib.Path(tmp) / "library" / series
    d.mkdir(parents=True)
    f = d / f"{slug}.html"
    f.write_text(html_text)
    rep = C.Report()
    cfg, _ = C.load_series(repo, series)
    rep.strict = bool(cfg and cfg.get("strict"))
    C.check_edition(str(f), series, repo, library, rep,
                    today=C._dt.date.fromisoformat(today))
    shutil.rmtree(tmp)
    return rep


def codes(rep):
    return sorted({f.code for f in rep.findings})


def expect(name, rep, must_have=(), must_not=(), blocks=None):
    global PASS
    got = codes(rep)
    ok = all(c in got for c in must_have) and all(c not in got for c in must_not)
    if blocks is not None:
        if isinstance(blocks, bool):
            ok = ok and ((len(rep.blocks) > 0) == blocks)
        else:
            ok = ok and (len(rep.blocks) == blocks)
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}: codes={got} blocks={len(rep.blocks)} "
              f"(wanted +{list(must_have)} -{list(must_not)} blocks={blocks})")
        for f in rep.findings:
            print(f"        {f.level} {f.code}: {f.message}")


def make_library(published):
    """published: dict series -> [slugs]. Returns temp dir shaped like a library checkout."""
    tmp = tempfile.mkdtemp()
    for series, slugs in published.items():
        d = pathlib.Path(tmp) / "library" / series
        d.mkdir(parents=True)
        for s in slugs:
            (d / f"{s}.html").write_text("<html></html>")
    return tmp


def seq_repo():
    """Copy the fixture repo, rewrite semiconductors as a sequence."""
    tmp = tempfile.mkdtemp()
    for sub in ("press", "templates"):
        shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(tmp) / sub)
    y = pathlib.Path(tmp) / "press" / "series" / "semiconductors" / "series.yaml"
    y.write_text(y.read_text().replace("mode: collection", "mode: sequence")
                              .replace("template: dossier", "template: chronicle"))
    # chronicle allows sequence; but our fixture is a dossier — instead keep dossier
    y.write_text(y.read_text().replace("template: chronicle", "template: dossier"))
    return tmp


VALID = make_fixtures.dossier()
VALID_BRIEF = make_fixtures.brief(TODAY)


def mut(old, new, base=None):
    base = base or VALID
    assert old in base, f"mutation target not found: {old[:60]!r}"
    return base.replace(old, new)


print("== happy paths ==")
expect("valid dossier is BLOCK-clean", run_local(VALID, "semiconductors"), blocks=0)
expect("valid dossier has zero warns too",
       run_local(VALID, "semiconductors"), must_not=["W-LENGTH-LOW", "W-SOURCES-MIN",
                                                     "W-CITE-DENSITY", "W-REQ-URL"])
expect("valid brief is BLOCK-clean",
       run_local(VALID_BRIEF, "ai-briefs", slug=TODAY), blocks=0)
expect("collection with library state, unpublished slug ok",
       run_local(VALID, "semiconductors",
                 library=make_library({"semiconductors": ["tsmc"]})), blocks=0)

print("== B-SERIES / B-SLUG / B-MODE ==")
expect("unknown series", run_local(VALID, "nope"), must_have=["B-SERIES"])
expect("unconfigured slug", run_local(
    mut('"slug": "micron"', '"slug": "intel"'), "semiconductors", slug="intel"),
    must_have=["B-SLUG"])
expect("collection: already published",
       run_local(VALID, "semiconductors",
                 library=make_library({"semiconductors": ["micron"]})),
       must_have=["B-MODE"])
expect("rolling: future date", run_local(
    VALID_BRIEF.replace(TODAY, "2027-01-01"), "ai-briefs", slug="2027-01-01"),
    must_have=["B-SLUG"])
expect("rolling: not a real date", run_local(
    VALID_BRIEF.replace(TODAY, "2026-13-99"), "ai-briefs", slug="2026-13-99"),
    must_have=["B-SLUG"])
expect("rolling: already published",
       run_local(VALID_BRIEF, "ai-briefs", slug=TODAY,
                 library=make_library({"ai-briefs": [TODAY]})),
       must_have=["B-MODE"])

print("== sequence mode ==")
srepo = seq_repo()
SEQ_VALID = mut('"mode": "collection", "order": null',
                '"mode": "sequence", "order": 1')
expect("sequence: first item, order 1, empty library",
       run_local(SEQ_VALID, "semiconductors", repo=srepo,
                 library=make_library({"semiconductors": []})), blocks=0)
expect("sequence: wrong next item",
       run_local(SEQ_VALID, "semiconductors", repo=srepo,
                 library=make_library({"semiconductors": ["micron"]})),
       must_have=["B-MODE"])
expect("sequence: wrong order number",
       run_local(mut('"order": 1', '"order": 3', base=SEQ_VALID),
                 "semiconductors", repo=srepo,
                 library=make_library({"semiconductors": []})),
       must_have=["B-MODE"])

print("== B-META-PARSE / B-META-MATCH ==")
expect("missing nb-meta block", run_local(
    mut('id="nb-meta"', 'id="not-meta"'), "semiconductors"),
    must_have=["B-META-PARSE"])
expect("nb-meta invalid json", run_local(
    mut('"protocol": "1.0",', '"protocol": "1.0"'), "semiconductors"),
    must_have=["B-META-PARSE"])
expect("nb-meta missing field", run_local(
    mut('"dek": "How a cyclical commodity maker became the AI era\'s bottleneck.",', ''),
    "semiconductors"), must_have=["B-META-PARSE"])
expect("wrong protocol major", run_local(
    mut('"protocol": "1.0"', '"protocol": "2.0"'), "semiconductors"),
    must_have=["B-META-PARSE"])
expect("path/meta slug mismatch", run_local(VALID, "semiconductors", slug="tsmc"),
       must_have=["B-META-MATCH"])
expect("meta mode mismatch", run_local(
    mut('"mode": "collection"', '"mode": "rolling"'), "semiconductors"),
    must_have=["B-META-MATCH"])
expect("meta template mismatch", run_local(
    mut('"template": "dossier"', '"template": "lesson"'), "semiconductors"),
    must_have=["B-META-MATCH"])

print("== B-HTML ==")
expect("missing required section", run_local(
    mut('data-nb-section="debate"', 'data-nb-section="argument"'), "semiconductors"),
    must_have=["B-HTML"])
expect("duplicated section", run_local(
    VALID.replace('<section data-nb-section="go-deeper">',
                  '<section data-nb-section="debate">', 1), "semiconductors"),
    must_have=["B-HTML"])

print("== B-SANDBOX ==")
expect("executable script", run_local(
    mut("</article>", "<script>alert(1)</script></article>"), "semiconductors"),
    must_have=["B-SANDBOX"])
expect("external script src", run_local(
    mut("</article>",
        '<script type="application/json" data-nb-chart '
        'src="https://evil.example/x.js"></script></article>'), "semiconductors"),
    must_have=["B-SANDBOX"])
expect("iframe", run_local(
    mut("</article>", '<iframe src="https://x.example"></iframe></article>'),
    "semiconductors"), must_have=["B-SANDBOX"])
expect("inline event handler", run_local(
    mut("<article>", '<article onclick="x()">'), "semiconductors"),
    must_have=["B-SANDBOX"])
expect("javascript: url", run_local(
    mut('href="https://example.org/src3"', 'href="javascript:alert(1)"'),
    "semiconductors"), must_have=["B-SANDBOX"])
expect("non-allowlisted stylesheet", run_local(
    mut("https://fonts.googleapis.com/css2?family=Newsreader&amp;display=swap",
        "https://cdn.evil.example/style.css"), "semiconductors"),
    must_have=["B-SANDBOX"])
expect("google fonts allowed", run_local(VALID, "semiconductors"),
       must_not=["B-SANDBOX"])
expect("malformed chart json", run_local(
    mut('"type":"bar"', '"type":"pie"'), "semiconductors"),
    must_have=["B-SANDBOX"])
expect("stray json script block", run_local(
    mut("</article>",
        '<script type="application/json">{"x":1}</script></article>'),
    "semiconductors"), must_have=["B-SANDBOX"])
expect("engine runtime script allowed", run_local(
    mut("</head>", '<script defer src="../../assets/nb.js"></script></head>'),
    "semiconductors"), must_not=["B-SANDBOX"], blocks=0)
expect("non-engine relative script blocked", run_local(
    mut("</head>", '<script src="../../assets/other.js"></script></head>'),
    "semiconductors"), must_have=["B-SANDBOX"])

print("== B-SOURCES-FORM / B-CITES-RESOLVE ==")
expect("no sources at all", run_local(
    VALID.replace("data-nb-source", "data-nb-src"), "semiconductors"),
    must_have=["B-SOURCES-FORM"])
expect("http (not https) source", run_local(
    mut('href="https://example.org/src4"', 'href="http://example.org/src4"'),
    "semiconductors"), must_have=["B-SOURCES-FORM"])
expect("dangling citation", run_local(
    mut('<a href="#s5">5</a>', '<a href="#s99">99</a>'), "semiconductors"),
    must_have=["B-CITES-RESOLVE"])
expect("citation to a non-source id", run_local(
    mut('<a href="#s5">5</a>', '<a href="#nb-meta">5</a>'), "semiconductors"),
    must_have=["B-CITES-RESOLVE"])

print("== WARN tier ==")
short = VALID
for _ in range(6):
    short = short.replace(make_fixtures.LOREM, "Short. ", 20)
expect("W-LENGTH-LOW", run_local(short, "semiconductors"),
       must_have=["W-LENGTH-LOW"], blocks=0)
expect("W-SOURCES-MIN", run_local(
    VALID.replace('<a data-nb-source href="https://example.org/src7">link</a>',
                  '<a href="https://example.org/src7">link</a>')
         .replace('<a data-nb-source href="https://example.org/src8">link</a>',
                  '<a href="https://example.org/src8">link</a>')
         .replace('<sup class="nb-cite"><a href="#s7">7</a></sup>', '')
         .replace('<sup class="nb-cite"><a href="#s8">8</a></sup>', ''),
    "semiconductors"), must_have=["W-SOURCES-MIN"], blocks=0)
# strip cites only inside debate section
m = _re.search(r'(<section data-nb-section="debate">.*?</section>)',
               VALID, _re.S)
assert m is not None
deb = m.group(1)
deb_stripped = _re.sub(r'<sup class="nb-cite">.*?</sup>', '', deb)
expect("W-CITE-DENSITY (per-section)", run_local(
    VALID.replace(deb, deb_stripped), "semiconductors"),
    must_have=["W-CITE-DENSITY"], blocks=0)
expect("W-WHY-MISSING + W-CITE-DENSITY (per-item)", run_local(
    VALID_BRIEF.replace('<p data-nb-why><b>Why it matters</b> — it moves the larger story we track.</p>', '', 1)
               .replace('<sup class="nb-cite"><a href="#s2">2</a></sup>', '', 1),
    "ai-briefs", slug=TODAY),
    must_have=["W-WHY-MISSING", "W-CITE-DENSITY"], blocks=0)
expect("W-LENGTH-LOW (brief item count)", run_local(
    _re.sub(r'<div data-nb-item>.*?</div>', '', VALID_BRIEF, count=2, flags=_re.S)
       .replace('<sup class="nb-cite"><a href="#s1">1</a></sup>', '')
       .replace('<sup class="nb-cite"><a href="#s2">2</a></sup>', ''),
    "ai-briefs", slug=TODAY), must_have=["W-LENGTH-LOW"], blocks=0)
reqdoc_repo = tempfile.mkdtemp()
for sub in ("press", "templates"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(reqdoc_repo) / sub)
ry = pathlib.Path(reqdoc_repo) / "press" / "series" / "semiconductors" / "series.yaml"
ry.write_text(ry.read_text().replace(
    'prompt: "Emphasize the HBM supply-agreement structure and the memory-cycle debate."',
    'prompt: "Emphasize HBM."\n    required_docs:\n      - id: mu-10k-2025\n        path: sources/mu-10k-2025.txt'))
expect("W-REQ-DOC satisfied when attribute present",
       run_local(VALID, "semiconductors", repo=reqdoc_repo),
       must_not=["W-REQ-DOC"], blocks=0)
expect("W-REQ-DOC", run_local(
    mut(' data-nb-required="mu-10k-2025"', ''), "semiconductors", repo=reqdoc_repo),
    must_have=["W-REQ-DOC"], blocks=0)
expect("consult prefix without a citation is fine", run_local(
    mut("https://www.sec.gov/filings/mu-10k", "https://example.org/not-sec"),
    "semiconductors"), must_not=["W-REQ-URL", "B-SOURCES-EXCLUSIVE"], blocks=0)
expect("W-SELF-COUNT", run_local(
    mut('"sources": 8', '"sources": 20'), "semiconductors"),
    must_have=["W-SELF-COUNT"], blocks=0)

print("== sources_exclusive ==")
excl_repo = tempfile.mkdtemp()
for sub in ("press", "templates"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(excl_repo) / sub)
ey = pathlib.Path(excl_repo) / "press" / "series" / "semiconductors" / "series.yaml"
ey.write_text(ey.read_text().replace(
    "consult:\n  - https://www.sec.gov/",
    "sources_exclusive: true\nconsult:\n  - https://www.sec.gov/\n"
    "  - https://example.org/"))
expect("exclusive: all sources in the declared set",
       run_local(VALID, "semiconductors", repo=excl_repo),
       must_not=["B-SOURCES-EXCLUSIVE"], blocks=0)
expect("exclusive: outside source is a BLOCK", run_local(
    mut('href="https://example.org/src4"', 'href="https://other.example/x"'),
    "semiconductors", repo=excl_repo),
    must_have=["B-SOURCES-EXCLUSIVE"])
ey.write_text(ey.read_text().replace("  - https://example.org/\n", "")
              .replace(
    'prompt: "Emphasize the HBM supply-agreement structure and the memory-cycle debate."',
    'required_docs:\n      - id: mu-10k-2025\n        path: sources/mu-10k-2025.txt'))
# 8 sources: s1 exempt (declared doc), s2 exempt (sec.gov consult) — the
# remaining 6 example.org sources violate. blocks=6 proves both exemptions.
expect("exclusive: declared required-doc entries are exempt", run_local(
    VALID, "semiconductors", repo=excl_repo),
    must_have=["B-SOURCES-EXCLUSIVE"], must_not=["W-REQ-DOC"], blocks=6)

print("== strict promotion ==")
strict_repo = tempfile.mkdtemp()
for sub in ("press", "templates"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(strict_repo) / sub)
sy = pathlib.Path(strict_repo) / "press" / "series" / "semiconductors" / "series.yaml"
sy.write_text(sy.read_text().replace("strict: false", "strict: true"))
expect("strict promotes WARN to BLOCK", run_local(
    mut('"sources": 8', '"sources": 20'), "semiconductors", repo=strict_repo),
    must_have=["W-SELF-COUNT"], blocks=True)

print("== templates: sample editions pass the proof ==")
tpl_repo = tempfile.mkdtemp()
shutil.copytree(REPO / "templates", pathlib.Path(tpl_repo) / "templates")
TPL_SERIES = {
    "crypto": ("sequence", "lesson",
               "items:\n  - {slug: hashes, title: Hash Functions}\n"
               "  - {slug: signatures, title: Signatures}"),
    "papers": ("collection", "paper",
               "items:\n  - {slug: attention, title: Attention}"),
    "histories": ("collection", "chronicle",
                  "items:\n  - {slug: unix, title: Unix}"),
}
for sid, (mode, template, items) in TPL_SERIES.items():
    d = pathlib.Path(tpl_repo) / "press" / "series" / sid
    d.mkdir(parents=True)
    (d / "series.yaml").write_text(
        f"name: {sid}\nmode: {mode}\ntemplate: {template}\n"
        f"autopublish: true\nstrict: false\n{items}\n")
for name, fixture, sid, slug in [
        ("lesson", make_fixtures.lesson(), "crypto", "hashes"),
        ("paper", make_fixtures.paper(), "papers", "attention"),
        ("chronicle", make_fixtures.chronicle(), "histories", "unix")]:
    rep = run_local(fixture, sid, slug=slug, repo=tpl_repo)
    expect(f"sample {name} edition is BLOCK-clean and WARN-free",
           rep, blocks=0,
           must_not=["W-LENGTH-LOW", "W-LENGTH-HIGH", "W-SOURCES-MIN",
                     "W-CITE-DENSITY", "W-SELF-COUNT"])

print("== templates: structural lint of the template files ==")
registry = C.load_registry(str(REPO))
for template_id, treg in registry.items():
    src = (REPO / "templates" / f"{template_id}.html").read_text()
    tpl = C.Edition()
    tpl.feed(src)
    tpl.close()
    ok_sections = all(tpl.sections.count(s) == 1
                      for s in treg.get("sections") or [])
    try:
        json.loads(tpl.meta_raw or "")
        ok_meta = True
    except Exception:
        ok_meta = False
    ok_scripts = all(
        (a.get("type") or "").strip().lower() == "application/json"
        or C.ENGINE_SCRIPT_RE.match(a.get("src", ""))
        for a in tpl.script_tags)
    ok_sandbox = (not tpl.forbidden_tags and not tpl.bad_event_attrs
                  and not tpl.bad_js_urls and tpl.sources)
    ok = ok_sections and ok_meta and ok_scripts and ok_sandbox
    if ok:
        PASS += 1
        print(f"  ok   template {template_id}.html structure")
    else:
        FAIL.append(f"template {template_id}.html")
        print(f"  FAIL template {template_id}.html: sections={ok_sections} "
              f"meta={ok_meta} scripts={ok_scripts} sandbox={ok_sandbox}")

print("== user templates (press/templates overlay) ==")
ut_repo = tempfile.mkdtemp()
for sub in ("press", "templates", "engine"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(ut_repo) / sub)
ut_tpl = pathlib.Path(ut_repo) / "press" / "templates"
ut_tpl.mkdir()
(ut_tpl / "registry.yaml").write_text(
    "memo:\n  class: shortread\n  words: [200, 3000]\n"
    "  sections: [note, sources]\n  cite_rule: per-section\n"
    "  modes: [collection]\n")
(ut_tpl / "memo.html").write_text("<!DOCTYPE html><html><body>"
                                  '<section data-nb-section="note"></section>'
                                  '<section data-nb-section="sources"></section>'
                                  "</body></html>")
ut_series = pathlib.Path(ut_repo) / "press" / "series" / "memos"
ut_series.mkdir()
(ut_series / "series.yaml").write_text(
    "name: Memos\nmode: collection\ntemplate: memo\nautopublish: true\n"
    "strict: false\nitems:\n  - {slug: first, title: First Memo}\n")

MEMO = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>First Memo</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "memos", "slug": "first", "template": "memo",
  "title": "First Memo", "mode": "collection", "order": null,
  "date": "2026-07-06", "tags": [], "sources": 5, "words": 230,
  "reading_minutes": 1, "dek": "A memo.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body>
<section data-nb-section="note"><p>{make_fixtures.LOREM * 7}
<sup class="nb-cite"><a href="#s1">1</a></sup></p></section>
<section data-nb-section="sources"><ol>{"".join(
    f'<li id="s{i}"><a data-nb-source href="https://example.org/m{i}">x</a></li>'
    for i in range(1, 6))}</ol></section>
</body></html>"""
expect("edition from a user-defined template passes the proof",
       run_local(MEMO, "memos", slug="first", repo=ut_repo), blocks=0)
expect("user template enforces its own sections", run_local(
    MEMO.replace('data-nb-section="note"', 'data-nb-section="body"'),
    "memos", slug="first", repo=ut_repo), must_have=["B-HTML"])
ut_rc = subprocess.run(
    [sys.executable, str(REPO / "engine" / "validate_config.py"),
     "--repo", ut_repo], capture_output=True)
if ut_rc.returncode == 0:
    PASS += 1
    print("  ok   validate_config accepts the overlay registry")
else:
    FAIL.append("validate_config overlay")
    print(f"  FAIL validate_config overlay: {ut_rc.stdout.decode()[-300:]}")
reg = C.load_registry(ut_repo)
if "memo" in reg and "dossier" in reg:
    PASS += 1
    print("  ok   merged registry keeps shipped + adds press templates")
else:
    FAIL.append("registry merge")
    print(f"  FAIL registry merge: keys={sorted(reg)}")
if C.find_template(ut_repo, "memo") and "press" in C.find_template(ut_repo, "memo") \
        and "press" not in (C.find_template(ut_repo, "dossier") or ""):
    PASS += 1
    print("  ok   template lookup: press shadows shipped")
else:
    FAIL.append("template lookup precedence")
    print("  FAIL template lookup precedence")

print("== rhythm & governance (cadence, paused, selection) ==")


def patched_repo(patch, series="semiconductors"):
    """Copy the fixture repo and append yaml to one series config."""
    tmp = tempfile.mkdtemp()
    for sub in ("press", "templates", "engine"):
        shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(tmp) / sub)
    y = pathlib.Path(tmp) / "press" / "series" / series / "series.yaml"
    y.write_text(y.read_text() + patch)
    return tmp


def vc_rc(repo):
    return subprocess.run(
        [sys.executable, str(REPO / "engine" / "validate_config.py"),
         "--repo", str(repo)], capture_output=True).returncode


expect("paused series blocks publication",
       run_local(VALID, "semiconductors", repo=patched_repo("paused: true\n")),
       must_have=["B-SERIES"])
for name, cond in [
    ("cadence weekdays validates", vc_rc(patched_repo("cadence: weekdays\n")) == 0),
    ("cadence day-list validates", vc_rc(patched_repo("cadence: [mon, thu]\n")) == 0),
    ("bogus cadence rejected", vc_rc(patched_repo("cadence: fortnightly\n")) == 1),
    ("selection random on a collection validates",
     vc_rc(patched_repo("selection: random\n")) == 0),
    ("selection on a rolling series rejected",
     vc_rc(patched_repo("selection: random\n", series="ai-briefs")) == 1),
    ("unknown series key (typo) rejected",
     vc_rc(patched_repo("cadance: daily\n")) == 1),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print("== open mode (the hands-off desk) ==")

OPEN_YAML = """name: Wildcard
mode: open
templates: [dossier, chronicle]
prompt: prompt.md
autopublish: true
strict: false
min_sources: 8
"""


def open_repo(series_yaml=OPEN_YAML):
    tmp = tempfile.mkdtemp()
    for sub in ("press", "templates", "engine"):
        shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(tmp) / sub)
    d = pathlib.Path(tmp) / "press" / "series" / "wildcard"
    d.mkdir()
    (d / "series.yaml").write_text(series_yaml)
    (d / "prompt.md").write_text("Anything about the AI stack.\n")
    return tmp


OPEN_ED = (VALID
           .replace('"series": "semiconductors", "slug": "micron",',
                    '"series": "wildcard", "slug": "the-cuda-moat",')
           .replace('"mode": "collection"', '"mode": "open"')
           .replace(' data-nb-required="mu-10k-2025"', ''))
orepo = open_repo()
olib = make_library({"wildcard": []})
expect("open freestyle pick is BLOCK-clean",
       run_local(OPEN_ED, "wildcard", slug="the-cuda-moat", repo=orepo,
                 library=olib), blocks=0)
expect("open duplicate slug blocked",
       run_local(OPEN_ED, "wildcard", slug="the-cuda-moat", repo=orepo,
                 library=make_library({"wildcard": ["the-cuda-moat"]})),
       must_have=["B-MODE"])
expect("open template outside the choice list blocked",
       run_local(OPEN_ED, "wildcard", slug="the-cuda-moat",
                 repo=open_repo(OPEN_YAML.replace(
                     "templates: [dossier, chronicle]",
                     "templates: [chronicle]")), library=olib),
       must_have=["B-META-MATCH"])

queue_repo = open_repo(OPEN_YAML + "items:\n"
                       "  - {slug: commissioned-piece, title: On Commission}\n")
expect("pending commission blocks a freestyle pick",
       run_local(OPEN_ED, "wildcard", slug="the-cuda-moat", repo=queue_repo,
                 library=olib), must_have=["B-MODE"])
expect("publishing the commissioned item is BLOCK-clean",
       run_local(OPEN_ED.replace("the-cuda-moat", "commissioned-piece"),
                 "wildcard", slug="commissioned-piece", repo=queue_repo,
                 library=olib), blocks=0)
for name, cond in [
    ("open series with a templates list validates", vc_rc(orepo) == 0),
    ("'templates' on a non-open series rejected",
     vc_rc(patched_repo("templates: [dossier]\n")) == 1),
    ("open mode without any template rejected",
     vc_rc(open_repo(OPEN_YAML.replace("templates: [dossier, chronicle]\n",
                                       ""))) == 1),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print("== duty.py (tonight's work list) ==")


def duty(repo, library, date=TODAY):
    out = subprocess.run(
        [sys.executable, str(REPO / "engine" / "duty.py"), "--repo", str(repo),
         "--library", str(library), "--date", date],
        capture_output=True, text=True)
    return json.loads(out.stdout)


def duty_of(report, sid):
    return next((e for e in report["due"] + report["idle"]
                 if e["series"] == sid), None)


empty_lib = make_library({"semiconductors": [], "ai-briefs": []})
d = duty(TESTREPO, empty_lib)
partial_lib = make_library({"semiconductors": ["micron"]})
d_partial = duty(TESTREPO, partial_lib)
d_random = duty(patched_repo("selection: random\n"), partial_lib)
d_paused = duty(patched_repo("paused: true\n"), empty_lib)
# 2026-07-06 is a Monday
d_cad_off = duty(patched_repo("cadence: [tue]\n", series="ai-briefs"), empty_lib)
d_open = duty(queue_repo, make_library({"wildcard": []}))
tonight_lib = make_library({"semiconductors": []})
(pathlib.Path(tonight_lib) / "library" / "semiconductors"
 / "micron.html").write_text(VALID)  # nb-meta date == TODAY
d_tonight = duty(TESTREPO, tonight_lib)

for name, cond in [
    ("rolling series due tonight with tonight's slug",
     duty_of(d, "ai-briefs") in d["due"]
     and duty_of(d, "ai-briefs")["slug"] == TODAY),
    ("rolling already-published tonight is idle",
     duty_of(duty(TESTREPO, make_library({"ai-briefs": [TODAY]})),
             "ai-briefs")["reason"] == "already published tonight"),
    ("collection in-order offers exactly the next item",
     duty_of(d_partial, "semiconductors")["candidates"] == ["tsmc"]),
    ("collection random offers every unpublished item",
     sorted(duty_of(d_random, "semiconductors")["candidates"])
     == ["asml", "nvidia", "sk-hynix", "tsmc"]),
    ("paused series is idle",
     duty_of(d_paused, "semiconductors")["reason"] == "paused"),
    ("cadence off-night is idle",
     duty_of(d_cad_off, "ai-briefs") in d_cad_off["idle"]),
    ("open desk with a queue lists commissions",
     duty_of(d_open, "wildcard")["commissions"] == ["commissioned-piece"]),
    ("an edition published tonight idles its series (rerun safety)",
     duty_of(d_tonight, "semiconductors")["reason"]
     == "already published tonight"),
    ("collection complete is idle",
     duty_of(duty(TESTREPO, make_library(
         {"semiconductors": ["micron", "tsmc", "asml", "sk-hynix", "nvidia"]})),
         "semiconductors")["reason"] == "complete"),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print("== PR mode (real git repo) ==")


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


prdir = tempfile.mkdtemp()
for sub in ("press", "templates"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(prdir) / sub)
shutil.copytree(REPO / "engine", pathlib.Path(prdir) / "engine",
                ignore=shutil.ignore_patterns("__pycache__", "fixtures"))
git("init", "-q", "-b", "main", cwd=prdir)
git("config", "user.email", "t@t", cwd=prdir)
git("config", "user.name", "t", cwd=prdir)
git("add", "-A", cwd=prdir)
git("commit", "-qm", "engine", cwd=prdir)
git("checkout", "-qb", "library", cwd=prdir)
pathlib.Path(prdir, "library").mkdir()
pathlib.Path(prdir, "library", ".gitkeep").write_text("")
git("add", "-A", cwd=prdir)
git("commit", "-qm", "library init", cwd=prdir)
git("checkout", "-qb", "claude/night-run", cwd=prdir)
ed = pathlib.Path(prdir, "library", "semiconductors")
ed.mkdir(parents=True)
(ed / "micron.html").write_text(VALID)
git("add", "-A", cwd=prdir)
git("commit", "-qm", "nb: semiconductors/micron", cwd=prdir)

body = pathlib.Path(prdir, "prbody.txt")
body.write_text("""Nightly edition.

```nb-meta
series: semiconductors
slug: micron
mode: collection
template: dossier
date: "2026-07-06"
title: "Micron Technology: The Scarcest Commodity in AI"
order: null
```
""")


def run_pr(extra_body=None, mutate=None):
    if mutate:
        mutate()
    rep = C.Report()
    args = types.SimpleNamespace(
        repo=prdir, main=None, base="library", head="claude/night-run",
        pr_body=str(extra_body or body), library=None, today=TODAY)
    C.run_pr_mode(args, rep)
    return rep


expect("PR happy path", run_pr(), blocks=0)

badbody = pathlib.Path(prdir, "prbody-bad.txt")
badbody.write_text(body.read_text().replace("slug: micron", "slug: tsmc"))
expect("PR body disagrees with file", run_pr(extra_body=badbody),
       must_have=["B-META-MATCH"])

nobody = pathlib.Path(prdir, "prbody-none.txt")
nobody.write_text("no metadata block here")
expect("PR body missing nb-meta block", run_pr(extra_body=nobody),
       must_have=["B-META-MATCH"])


def add_second_file():
    p = pathlib.Path(prdir, "library", "semiconductors", "extra.txt")
    p.write_text("x")
    git("add", "-A", cwd=prdir)
    git("commit", "-qm", "extra", cwd=prdir)


expect("PR touching two files", run_pr(mutate=add_second_file),
       must_have=["B-DIFF-SHAPE"])

git("reset", "-q", "--hard", "HEAD~1", cwd=prdir)


def modify_engine():
    p = pathlib.Path(prdir, "engine", "check.py")
    p.write_text(p.read_text() + "\n# sneak\n")
    git("add", "-A", cwd=prdir)
    git("commit", "-qm", "sneak", cwd=prdir)


expect("PR modifying engine code", run_pr(mutate=modify_engine),
       must_have=["B-DIFF-SHAPE"])

print("== validate_config ==")
vc = REPO / "engine" / "validate_config.py"
# the shipped examples/ must validate when used as a press
ex_repo = pathlib.Path(tempfile.mkdtemp()) / "repo"
ex_repo.mkdir()
shutil.copytree(REPO / "templates", ex_repo / "templates")
shutil.copytree(REPO / "engine" / "assets", ex_repo / "engine" / "assets")
shutil.copytree(REPO / "examples", ex_repo / "press")
rc_good = subprocess.run([sys.executable, str(vc), "--repo", str(ex_repo)],
                         capture_output=True).returncode
broken = pathlib.Path(tempfile.mkdtemp()) / "repo"
shutil.copytree(TESTREPO, broken)
by = pathlib.Path(broken) / "press" / "series" / "semiconductors" / "series.yaml"
by.write_text(by.read_text().replace("mode: collection", "mode: rolling"))
rc_bad = subprocess.run([sys.executable, str(vc), "--repo", broken],
                        capture_output=True).returncode
for name, cond in [("shipped examples validate as a press", rc_good == 0),
                   ("illegal mode/template pairing fails", rc_bad == 1)]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print()
print("== builder suite (run_builder_tests.py) ==")
builder = subprocess.run([sys.executable, str(HERE / "run_builder_tests.py")])
if builder.returncode != 0:
    FAIL.append("builder suite")

print()
print("== end-to-end dress rehearsal (run_e2e_test.py) ==")
e2e = subprocess.run([sys.executable, str(HERE / "run_e2e_test.py")])
if e2e.returncode != 0:
    FAIL.append("e2e suite")

print()
print(f"{PASS} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
