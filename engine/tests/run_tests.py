#!/usr/bin/env python3
"""
Test suite for engine/check.py. Zero test-framework dependencies.

Strategy: generate valid fixtures, then derive each failure case by mutating the
valid edition, asserting the exact finding code appears (and that the valid cases
are BLOCK-clean). PR mode is tested against a real throwaway git repo.

Run: python3 engine/tests/run_tests.py
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "engine"))

import check as C  # noqa: E402
import make_fixtures  # noqa: E402

TODAY = "2026-07-06"
PASS, FAIL = 0, []


def run_local(html_text, series, slug=None, library=None, repo=None, today=TODAY):
    """Write html to a temp file laid out as library/<series>/<slug>.html and check."""
    repo = repo or str(REPO)
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
    """Copy the repo's series into a temp repo, rewrite semiconductors as a sequence."""
    tmp = tempfile.mkdtemp()
    for sub in ("series", "templates"):
        shutil.copytree(REPO / sub, pathlib.Path(tmp) / sub)
    y = pathlib.Path(tmp) / "series" / "semiconductors" / "series.yaml"
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
no_cites_in_debate = VALID
for n in range(1, 9):
    no_cites_in_debate = no_cites_in_debate.replace(
        f'<section data-nb-section="debate"><h2>Bull versus bear</h2>',
        f'<section data-nb-section="debate"><h2>Bull versus bear</h2>', 1)
# strip cites only inside debate section
import re as _re
m = _re.search(r'(<section data-nb-section="debate">.*?</section>)',
               VALID, _re.S)
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
for sub in ("series", "templates"):
    shutil.copytree(REPO / sub, pathlib.Path(reqdoc_repo) / sub)
ry = pathlib.Path(reqdoc_repo) / "series" / "semiconductors" / "series.yaml"
ry.write_text(ry.read_text().replace(
    'prompt: "Emphasize the HBM supply-agreement structure and the memory-cycle debate."',
    'prompt: "Emphasize HBM."\n    required_docs:\n      - id: mu-10k-2025\n        path: sources/mu-10k-2025.txt'))
expect("W-REQ-DOC satisfied when attribute present",
       run_local(VALID, "semiconductors", repo=reqdoc_repo),
       must_not=["W-REQ-DOC"], blocks=0)
expect("W-REQ-DOC", run_local(
    mut(' data-nb-required="mu-10k-2025"', ''), "semiconductors", repo=reqdoc_repo),
    must_have=["W-REQ-DOC"], blocks=0)
expect("W-REQ-URL", run_local(
    mut("https://www.sec.gov/filings/mu-10k", "https://example.org/not-sec"),
    "semiconductors"), must_have=["W-REQ-URL"], blocks=0)
expect("W-SELF-COUNT", run_local(
    mut('"sources": 8', '"sources": 20'), "semiconductors"),
    must_have=["W-SELF-COUNT"], blocks=0)

print("== strict promotion ==")
strict_repo = tempfile.mkdtemp()
for sub in ("series", "templates"):
    shutil.copytree(REPO / sub, pathlib.Path(strict_repo) / sub)
sy = pathlib.Path(strict_repo) / "series" / "semiconductors" / "series.yaml"
sy.write_text(sy.read_text().replace("strict: false", "strict: true"))
expect("strict promotes WARN to BLOCK", run_local(
    mut('"sources": 8', '"sources": 20'), "semiconductors", repo=strict_repo),
    must_have=["W-SELF-COUNT"], blocks=True)

print("== PR mode (real git repo) ==")


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


prdir = tempfile.mkdtemp()
for sub in ("series", "templates", "engine"):
    shutil.copytree(REPO / sub, pathlib.Path(prdir) / sub)
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
    args = type("A", (), {})()
    args.repo = prdir
    args.base = "library"
    args.head = "claude/night-run"
    args.pr_body = str(extra_body or body)
    args.library = None
    args.today = TODAY
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

print()
print("== builder suite (run_builder_tests.py) ==")
builder = subprocess.run([sys.executable, str(HERE / "run_builder_tests.py")])
if builder.returncode != 0:
    FAIL.append("builder suite")

print()
print(f"{PASS} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
