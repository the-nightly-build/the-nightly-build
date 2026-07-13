#!/usr/bin/env python3
"""Test suite for the proof, with zero framework dependencies.

Strategy: build valid fixture articles, then derive each failure case by
mutating a valid one and asserting that the exact finding code appears.
Valid cases must stay BLOCK-clean, and PR mode runs against a real
throwaway git repository so the diff-shape rules face actual git output.

Run: python3 engine/tests/run_tests.py
"""

import contextlib
import io
import json
import pathlib
import re as _re
import shutil
import subprocess
import sys
import tempfile
import types

import _bootstrap
import check as C
import make_fixtures
import morning_gate as MG
import validate_config as V
import yaml

HERE = _bootstrap.HERE
REPO = _bootstrap.REPO

TODAY = "2026-07-06"
PASS, FAIL = 0, []
# tests never read the shipped series configs — forks clear those on setup
TESTREPO = make_fixtures.test_repo()


def run_local(
    html_text, series, *, slug=None, library=None, repo=None, today=TODAY, pr_body=None
):
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
    body_meta = None
    if pr_body is not None:
        bf = pathlib.Path(tmp) / "prbody.txt"
        bf.write_text(pr_body)
        body_meta = C.resolve_pr_body(str(bf), rep)
    C.check_article(
        str(f),
        series,
        repo=repo,
        library_dir=library,
        rep=rep,
        pr_body_meta=body_meta,
        today=C._dt.date.fromisoformat(today),
    )
    shutil.rmtree(tmp)
    return rep


def codes(rep):
    seen = {f.code for f in rep.findings}
    return sorted(seen)


def expect(name, rep, *, must_have=(), must_not=(), blocks=None):
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
        print(
            f"  FAIL {name}: codes={got} blocks={len(rep.blocks)} "
            f"(wanted +{list(must_have)} -{list(must_not)} blocks={blocks})"
        )
        for f in rep.findings:
            print(f"        {f.level} {f.code}: {f.message}")


def make_library(published):
    tmp = tempfile.mkdtemp()
    for series, slugs in published.items():
        d = pathlib.Path(tmp) / "library" / series
        d.mkdir(parents=True)
        for s in slugs:
            (d / f"{s}.html").write_text("<html></html>")
    return tmp


def seq_repo():
    tmp = tempfile.mkdtemp()
    for sub in ("press", "templates"):
        shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(tmp) / sub)
    y = pathlib.Path(tmp) / "press" / "series" / "semiconductors" / "series.yaml"
    y.write_text(y.read_text().replace("mode: collection", "mode: sequence"))
    return tmp


VALID = make_fixtures.article()
VALID_BRIEF = make_fixtures.brief(TODAY)


def mut(old, new, *, base=None):
    base = base or VALID
    assert old in base, f"mutation target not found: {old[:60]!r}"
    return base.replace(old, new)


print("== happy paths ==")
expect("valid article is BLOCK-clean", run_local(VALID, "semiconductors"), blocks=0)
expect(
    "valid article has zero warns too",
    run_local(VALID, "semiconductors"),
    must_not=["W-LENGTH-LOW", "W-SOURCES-MIN", "W-CITE-DENSITY"],
)
expect(
    "clean prose does not trip the banned-terms warn",
    run_local(VALID, "semiconductors"),
    must_not=["W-BANNED-TERM"],
)
expect(
    "em-dash overuse trips the soft W-BANNED-TERM warn (never a block)",
    run_local(
        mut(
            "<h2>Orientation</h2>",
            "<h2>Orientation</h2><p>" + "clause — " * 5 + "</p>",
        ),
        "semiconductors",
    ),
    must_have=["W-BANNED-TERM"],
    blocks=0,
)
expect(
    "valid brief is BLOCK-clean",
    run_local(VALID_BRIEF, "ai-briefs", slug=TODAY),
    blocks=0,
)
expect(
    "collection with library state, unpublished slug ok",
    run_local(
        VALID, "semiconductors", library=make_library({"semiconductors": ["tsmc"]})
    ),
    blocks=0,
)

print("== B-SERIES / B-SLUG / B-MODE ==")
expect("unknown series", run_local(VALID, "nope"), must_have=["B-SERIES"])
expect(
    "unconfigured slug",
    run_local(
        mut('"slug": "micron"', '"slug": "intel"'), "semiconductors", slug="intel"
    ),
    must_have=["B-SLUG"],
)
expect(
    "collection: already published",
    run_local(
        VALID, "semiconductors", library=make_library({"semiconductors": ["micron"]})
    ),
    must_have=["B-MODE"],
)
expect(
    "rolling: future date",
    run_local(VALID_BRIEF.replace(TODAY, "2027-01-01"), "ai-briefs", slug="2027-01-01"),
    must_have=["B-SLUG"],
)
expect(
    "rolling: not a real date",
    run_local(VALID_BRIEF.replace(TODAY, "2026-13-99"), "ai-briefs", slug="2026-13-99"),
    must_have=["B-SLUG"],
)
expect(
    "rolling: already published",
    run_local(
        VALID_BRIEF,
        "ai-briefs",
        slug=TODAY,
        library=make_library({"ai-briefs": [TODAY]}),
    ),
    must_have=["B-MODE"],
)

print("== sequence mode ==")
srepo = seq_repo()
SEQ_VALID = mut('"mode": "collection", "order": null', '"mode": "sequence", "order": 1')
expect(
    "sequence: first item, order 1, empty library",
    run_local(
        SEQ_VALID,
        "semiconductors",
        repo=srepo,
        library=make_library({"semiconductors": []}),
    ),
    blocks=0,
)
expect(
    "sequence: wrong next item",
    run_local(
        SEQ_VALID,
        "semiconductors",
        repo=srepo,
        library=make_library({"semiconductors": ["micron"]}),
    ),
    must_have=["B-MODE"],
)
expect(
    "sequence: wrong order number",
    run_local(
        mut('"order": 1', '"order": 3', base=SEQ_VALID),
        "semiconductors",
        repo=srepo,
        library=make_library({"semiconductors": []}),
    ),
    must_have=["B-MODE"],
)

print("== B-META-PARSE / B-META-MATCH ==")
expect(
    "missing nb-meta block",
    run_local(mut('id="nb-meta"', 'id="not-meta"'), "semiconductors"),
    must_have=["B-META-PARSE"],
)
expect(
    "nb-meta invalid json",
    run_local(mut('"protocol": "1.0",', '"protocol": "1.0"'), "semiconductors"),
    must_have=["B-META-PARSE"],
)
expect(
    "nb-meta missing field",
    run_local(
        mut(
            '"dek": "How a cyclical commodity maker became the AI era\'s bottleneck.",',
            "",
        ),
        "semiconductors",
    ),
    must_have=["B-META-PARSE"],
)
expect(
    "wrong protocol major",
    run_local(mut('"protocol": "1.0"', '"protocol": "2.0"'), "semiconductors"),
    must_have=["B-META-PARSE"],
)
expect(
    "path/meta slug mismatch",
    run_local(VALID, "semiconductors", slug="tsmc"),
    must_have=["B-META-MATCH"],
)
expect(
    "meta mode mismatch",
    run_local(mut('"mode": "collection"', '"mode": "rolling"'), "semiconductors"),
    must_have=["B-META-MATCH"],
)
expect(
    "meta template mismatch",
    run_local(mut('"template": "article"', '"template": "brief"'), "semiconductors"),
    must_have=["B-META-MATCH"],
)
expect(
    "slug-style tag is accepted",
    run_local(
        mut('"tags": ["equity"]', '"tags": ["equity", "memory-cycle"]'),
        "semiconductors",
    ),
    must_not=["B-META-PARSE"],
    blocks=0,
)
expect(
    "uppercase tag blocked (slug rule)",
    run_local(mut('"tags": ["equity"]', '"tags": ["Equity"]'), "semiconductors"),
    must_have=["B-META-PARSE"],
)
expect(
    "path-traversal tag blocked (slug rule)",
    run_local(
        mut('"tags": ["equity"]', '"tags": ["../../../escape"]'), "semiconductors"
    ),
    must_have=["B-META-PARSE"],
)
expect(
    "non-list tags blocked",
    run_local(mut('"tags": ["equity"]', '"tags": "equity"'), "semiconductors"),
    must_have=["B-META-PARSE"],
)

print("== B-HTML ==")
expect(
    "missing required section",
    run_local(
        mut('data-nb-section="orientation"', 'data-nb-section="intro"'),
        "semiconductors",
    ),
    must_have=["B-HTML"],
)
expect(
    "duplicated section",
    run_local(
        VALID.replace(
            '<section data-nb-section="bull-versus-bear">',
            '<section data-nb-section="orientation">',
            1,
        ),
        "semiconductors",
    ),
    must_have=["B-HTML"],
)

print("== PR-body preflight (local --pr-body) ==")
MINIMAL_BODY = (
    "Autonomous night-shift article.\n\n"
    "```nb-meta\n"
    "series: semiconductors\n"
    "slug: micron\n"
    "mode: collection\n"
    "template: article\n"
    'date: "2026-07-06"\n'
    'title: "Micron Technology: The Scarcest Commodity in AI"\n'
    "order: null\n"
    "```\n"
)
# The canonical body carries the production record PROTOCOL step 8 defines.
GOOD_BODY = (
    MINIMAL_BODY + "\n## Process\n"
    "Coach studied two exemplars; one edit round, surgical fixes only.\n\n"
    "## Voice brief\n"
    "<details><summary>brief</summary>\n\n````markdown\ncalm, precise\n````\n\n"
    "</details>\n\n"
    "## Also consulted\n"
    "- https://example.org/background — context only, superseded by the filing\n"
)
expect(
    "preflight passes when the PR body matches the article",
    run_local(VALID, "semiconductors", pr_body=GOOD_BODY),
    blocks=0,
    must_not=["B-META-MATCH", "W-BODY-RECORD"],
)
expect(
    "preflight warns when the record sections are missing",
    run_local(VALID, "semiconductors", pr_body=MINIMAL_BODY),
    blocks=0,
    must_have=["W-BODY-RECORD"],
)
expect(
    "preflight catches a PR body with no nb-meta block",
    run_local(VALID, "semiconductors", pr_body="just a description, no metadata"),
    must_have=["B-META-MATCH"],
)
expect(
    "preflight catches a PR body that disagrees with the article",
    run_local(
        VALID, "semiconductors", pr_body=GOOD_BODY.replace("Micron Technology", "TSMC")
    ),
    must_have=["B-META-MATCH"],
)

print("== B-SANDBOX ==")
expect(
    "executable script",
    run_local(
        mut("</article>", "<script>alert(1)</script></article>"), "semiconductors"
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "external script src",
    run_local(
        mut(
            "</article>",
            '<script type="application/json" data-nb-chart '
            'src="https://evil.example/x.js"></script></article>',
        ),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "iframe",
    run_local(
        mut("</article>", '<iframe src="https://x.example"></iframe></article>'),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "inline event handler",
    run_local(mut("<article>", '<article onclick="x()">'), "semiconductors"),
    must_have=["B-SANDBOX"],
)
expect(
    "javascript: url",
    run_local(
        mut('href="https://example.org/src3"', 'href="javascript:alert(1)"'),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "non-allowlisted stylesheet",
    run_local(
        mut(
            "https://fonts.googleapis.com/css2?family=Newsreader&amp;display=swap",
            "https://cdn.evil.example/style.css",
        ),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "google fonts allowed", run_local(VALID, "semiconductors"), must_not=["B-SANDBOX"]
)
expect(
    "font-host subdomain-suffix bypass blocked",
    run_local(
        mut(
            "https://fonts.googleapis.com/css2?family=Newsreader&amp;display=swap",
            "https://fonts.googleapis.com.evil.example/pwn.css",
        ),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "font-host userinfo bypass blocked",
    run_local(
        mut(
            "https://fonts.googleapis.com/css2?family=Newsreader&amp;display=swap",
            "https://fonts.googleapis.com@evil.example/pwn.css",
        ),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "font-host lookalike TLD suffix blocked",
    run_local(
        mut(
            "https://fonts.googleapis.com/css2?family=Newsreader&amp;display=swap",
            "https://fonts.googleapis.commmm/x.css",
        ),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "malformed chart json",
    run_local(mut('"type":"bar"', '"type":"pie"'), "semiconductors"),
    must_have=["B-SANDBOX"],
)
expect(
    "stray json script block",
    run_local(
        mut("</article>", '<script type="application/json">{"x":1}</script></article>'),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "engine runtime script allowed",
    run_local(
        mut("</head>", '<script defer src="../../assets/nb.js"></script></head>'),
        "semiconductors",
    ),
    must_not=["B-SANDBOX"],
    blocks=0,
)
expect(
    "non-engine relative script blocked",
    run_local(
        mut("</head>", '<script src="../../assets/other.js"></script></head>'),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)

expect(
    "protocol-relative stylesheet blocked",
    run_local(
        mut(
            "https://fonts.googleapis.com/css2?family=Newsreader&amp;display=swap",
            "//cdn.evil.example/style.css",
        ),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "backslash-obfuscated external ref blocked",
    run_local(
        mut(
            "https://fonts.googleapis.com/css2?family=Newsreader&amp;display=swap",
            "/\\cdn.evil.example/style.css",
        ),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "meta-refresh redirect blocked",
    run_local(
        mut(
            "</head>",
            '<meta http-equiv="refresh" content="0;url=//evil.example"></head>',
        ),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "form blocked",
    run_local(
        mut("</article>", '<form action="//evil.example"></form></article>'),
        "semiconductors",
    ),
    must_have=["B-SANDBOX"],
)
expect(
    "duplicate nb-meta blocked",
    run_local(
        mut(
            "</head>",
            '<script type="application/json" id="nb-meta">{"x":1}</script></head>',
        ),
        "semiconductors",
    ),
    must_have=["B-META-PARSE"],
)

print("== B-SOURCES-FORM / B-CITES-RESOLVE ==")
expect(
    "no sources at all",
    run_local(VALID.replace("data-nb-source", "data-nb-src"), "semiconductors"),
    must_have=["B-SOURCES-FORM"],
)
expect(
    "http (not https) source",
    run_local(
        mut('href="https://example.org/src4"', 'href="http://example.org/src4"'),
        "semiconductors",
    ),
    must_have=["B-SOURCES-FORM"],
)
expect(
    "data-nb-required source may cite a repo-relative local file (V6a)",
    run_local(
        mut('href="https://example.org/src1"', 'href="sources/mu-10k-2025.txt"'),
        "semiconductors",
    ),
    must_not=["B-SOURCES-FORM"],
    blocks=0,
)
expect(
    "non-required source still must be absolute https",
    run_local(
        mut('href="https://example.org/src4"', 'href="sources/local.txt"'),
        "semiconductors",
    ),
    must_have=["B-SOURCES-FORM"],
)
expect(
    "off-origin path even on a required source is rejected",
    run_local(
        mut('href="https://example.org/src1"', 'href="//evil.example/x.txt"'),
        "semiconductors",
    ),
    must_have=["B-SOURCES-FORM"],
)
expect(
    "dangling citation",
    run_local(mut('<a href="#s5">5</a>', '<a href="#s99">99</a>'), "semiconductors"),
    must_have=["B-CITES-RESOLVE"],
)
expect(
    "citation to a non-source id",
    run_local(mut('<a href="#s5">5</a>', '<a href="#nb-meta">5</a>'), "semiconductors"),
    must_have=["B-CITES-RESOLVE"],
)

print("== WARN tier ==")
short = VALID
for _ in range(9):
    short = short.replace(make_fixtures.LOREM, "Short. ", 20)
expect(
    "W-LENGTH-LOW",
    run_local(short, "semiconductors"),
    must_have=["W-LENGTH-LOW"],
    blocks=0,
)
expect(
    "W-SOURCES-MIN",
    run_local(
        VALID.replace(
            '<a data-nb-source href="https://example.org/src7">link</a>',
            '<a href="https://example.org/src7">link</a>',
        )
        .replace(
            '<a data-nb-source href="https://example.org/src8">link</a>',
            '<a href="https://example.org/src8">link</a>',
        )
        .replace('<sup class="nb-cite"><a href="#s7">7</a></sup>', "")
        .replace('<sup class="nb-cite"><a href="#s8">8</a></sup>', ""),
        "semiconductors",
    ),
    must_have=["W-SOURCES-MIN"],
    blocks=0,
)
# strip cites only inside debate section
m = _re.search(
    r'(<section data-nb-section="bull-versus-bear">.*?</section>)', VALID, _re.S
)
assert m is not None
deb = m.group(1)
deb_stripped = _re.sub(r'<sup class="nb-cite">.*?</sup>', "", deb)
expect(
    "W-CITE-DENSITY (per-section)",
    run_local(VALID.replace(deb, deb_stripped), "semiconductors"),
    must_have=["W-CITE-DENSITY"],
    blocks=0,
)
expect(
    "W-WHY-MISSING + W-CITE-DENSITY (per-item)",
    run_local(
        VALID_BRIEF.replace(
            "<p data-nb-why><b>Why it matters</b>: it moves the larger story we track.</p>",
            "",
            1,
        ).replace('<sup class="nb-cite"><a href="#s2">2</a></sup>', "", 1),
        "ai-briefs",
        slug=TODAY,
    ),
    must_have=["W-WHY-MISSING", "W-CITE-DENSITY"],
    blocks=0,
)
expect(
    "W-LENGTH-LOW (brief item count)",
    run_local(
        _re.sub(r"<div data-nb-item>.*?</div>", "", VALID_BRIEF, count=2, flags=_re.S)
        .replace('<sup class="nb-cite"><a href="#s1">1</a></sup>', "")
        .replace('<sup class="nb-cite"><a href="#s2">2</a></sup>', ""),
        "ai-briefs",
        slug=TODAY,
    ),
    must_have=["W-LENGTH-LOW"],
    blocks=0,
)
reqdoc_repo = tempfile.mkdtemp()
for sub in ("press", "templates"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(reqdoc_repo) / sub)
ry = pathlib.Path(reqdoc_repo) / "press" / "series" / "semiconductors" / "series.yaml"
ry.write_text(
    ry.read_text().replace(
        'prompt: "Emphasize the HBM supply-agreement structure and the memory-cycle debate."',
        'prompt: "Emphasize HBM."\n    required_docs:\n      - id: mu-10k-2025\n        path: sources/mu-10k-2025.txt',
    )
)
expect(
    "W-REQ-DOC satisfied when attribute present",
    run_local(VALID, "semiconductors", repo=reqdoc_repo),
    must_not=["W-REQ-DOC"],
    blocks=0,
)
expect(
    "W-REQ-DOC",
    run_local(
        mut(' data-nb-required="mu-10k-2025"', ""), "semiconductors", repo=reqdoc_repo
    ),
    must_have=["W-REQ-DOC"],
    blocks=0,
)
expect(
    "consult prefix without a citation is fine",
    run_local(
        mut("https://www.sec.gov/filings/mu-10k", "https://example.org/not-sec"),
        "semiconductors",
    ),
    must_not=["B-SOURCES-EXCLUSIVE"],
    blocks=0,
)
expect(
    "W-SELF-COUNT",
    run_local(mut('"sources": 8', '"sources": 20'), "semiconductors"),
    must_have=["W-SELF-COUNT"],
    blocks=0,
)

print("== sources_exclusive ==")
excl_repo = tempfile.mkdtemp()
for sub in ("press", "templates"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(excl_repo) / sub)
ey = pathlib.Path(excl_repo) / "press" / "series" / "semiconductors" / "series.yaml"
ey.write_text(
    ey.read_text().replace(
        "consult:\n  - https://www.sec.gov/",
        "sources_exclusive: true\nconsult:\n  - https://www.sec.gov/\n"
        "  - https://example.org/",
    )
)
expect(
    "exclusive: all sources in the declared set",
    run_local(VALID, "semiconductors", repo=excl_repo),
    must_not=["B-SOURCES-EXCLUSIVE"],
    blocks=0,
)
expect(
    "exclusive: outside source is a BLOCK",
    run_local(
        mut('href="https://example.org/src4"', 'href="https://other.example/x"'),
        "semiconductors",
        repo=excl_repo,
    ),
    must_have=["B-SOURCES-EXCLUSIVE"],
)
ey.write_text(
    ey.read_text()
    .replace("  - https://example.org/\n", "")
    .replace(
        'prompt: "Emphasize the HBM supply-agreement structure and the memory-cycle debate."',
        "required_docs:\n      - id: mu-10k-2025\n        path: sources/mu-10k-2025.txt",
    )
)
# 8 sources: s1 exempt (declared doc), s2 exempt (sec.gov consult) — the
# remaining 6 example.org sources violate. blocks=6 proves both exemptions.
expect(
    "exclusive: declared required-doc entries are exempt",
    run_local(VALID, "semiconductors", repo=excl_repo),
    must_have=["B-SOURCES-EXCLUSIVE"],
    must_not=["W-REQ-DOC"],
    blocks=6,
)

print("== strict promotion ==")
strict_repo = tempfile.mkdtemp()
for sub in ("press", "templates"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(strict_repo) / sub)
sy = pathlib.Path(strict_repo) / "press" / "series" / "semiconductors" / "series.yaml"
sy.write_text(sy.read_text().replace("strict: false", "strict: true"))
expect(
    "strict promotes WARN to BLOCK",
    run_local(mut('"sources": 8', '"sources": 20'), "semiconductors", repo=strict_repo),
    must_have=["W-SELF-COUNT"],
    blocks=True,
)

print("== templates: sample articles pass the proof ==")
tpl_repo = tempfile.mkdtemp()
shutil.copytree(REPO / "templates", pathlib.Path(tpl_repo) / "templates")
TPL_SERIES = {
    "histories": ("collection", "article", "items:\n  - {slug: unix, title: Unix}"),
}
for sid, (mode, template, items) in TPL_SERIES.items():
    d = pathlib.Path(tpl_repo) / "press" / "series" / sid
    d.mkdir(parents=True)
    (d / "series.yaml").write_text(
        f"name: {sid}\nmode: {mode}\ntemplate: {template}\n"
        f"autopublish: true\nstrict: false\n{items}\n"
    )
for name, fixture, sid, slug in [
    ("chronicle-shaped article", make_fixtures.chronicle(), "histories", "unix"),
]:
    rep = run_local(fixture, sid, slug=slug, repo=tpl_repo)
    expect(
        f"sample {name} article is BLOCK-clean and WARN-free",
        rep,
        blocks=0,
        must_not=[
            "W-LENGTH-LOW",
            "W-LENGTH-HIGH",
            "W-SOURCES-MIN",
            "W-CITE-DENSITY",
            "W-SELF-COUNT",
        ],
    )

print("== templates: structural lint of the template skeletons ==")
registry = C.load_registry(str(REPO))
for template_id, treg in registry.items():
    tpl_path = C.find_template(str(REPO), template_id)
    if tpl_path is None:
        FAIL.append(f"template {template_id}/skeleton.html")
        print(
            f"  FAIL template {template_id}: no skeleton.html in "
            "templates/ or press/templates/"
        )
        continue
    src = pathlib.Path(tpl_path).read_text()
    tpl = C.Article()
    tpl.feed(src)
    tpl.close()
    ok_sections = all(tpl.sections.count(s) == 1 for s in treg.get("sections") or [])
    try:
        json.loads(tpl.meta_raw or "")
        ok_meta = True
    except ValueError:
        ok_meta = False
    ok_scripts = all(
        (a.get("type") or "").strip().lower() == "application/json"
        or C.ENGINE_SCRIPT_RE.match(a.get("src", ""))
        for a in tpl.script_tags
    )
    ok_sandbox = (
        not tpl.forbidden_tags
        and not tpl.bad_event_attrs
        and not tpl.bad_js_urls
        and tpl.sources
    )
    ok = ok_sections and ok_meta and ok_scripts and ok_sandbox
    if ok:
        PASS += 1
        print(f"  ok   template {template_id}/skeleton.html structure")
    else:
        FAIL.append(f"template {template_id}/skeleton.html")
        print(
            f"  FAIL template {template_id}/skeleton.html: sections={ok_sections} "
            f"meta={ok_meta} scripts={ok_scripts} sandbox={ok_sandbox}"
        )

print("== user templates (press/templates overlay) ==")
ut_repo = tempfile.mkdtemp()
for sub in ("press", "templates", "engine"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(ut_repo) / sub)
ut_tpl = pathlib.Path(ut_repo) / "press" / "templates"


def user_template(tid, manifest, skeleton):
    folder = ut_tpl / tid
    folder.mkdir(parents=True)
    (folder / "manifest.yaml").write_text(manifest)
    (folder / "skeleton.html").write_text(skeleton)


def skeleton_of(*sections):
    return (
        "<!DOCTYPE html><html><body>"
        + "".join(f'<section data-nb-section="{s}"></section>' for s in sections)
        + "</body></html>"
    )


user_template(
    "memo",
    "class: shortread\nwords: [200, 3000]\n"
    "sections: [note, sources]\ncite_rule: per-section\nmodes: [collection]\n",
    skeleton_of("note", "sources"),
)
user_template(
    "fieldnotes",
    "class: shortread\nwords: [200, 3000]\n"
    "sections: [sources]\nflex_sections: [2, 3]\n"
    "cite_rule: per-section\ncite_exempt: [context]\nmodes: [collection]\n",
    skeleton_of("YOUR-LABEL", "sources"),
)
# the exact manifest from the docs/customization.md walkthrough, so the tutorial
# cannot drift from what the proof enforces
user_template(
    "lesson",
    "class: longread\nwords: [1500, 4000]\n"
    "sections: [objectives, recap, teach, check, bridge, sources]\n"
    "cite_rule: per-section\ncite_exempt: [objectives]\nmodes: [sequence]\n",
    skeleton_of("objectives", "recap", "teach", "check", "bridge", "sources"),
)
# a per-item template NOT named 'brief', to prove require_why is manifest-driven
# rather than hardcoded to the shipped brief template
user_template(
    "digest",
    "class: shortread\nitems: [2, 4]\n"
    "sections: [entries, sources]\ncite_rule: per-item\n"
    "require_why: true\nmodes: [collection]\n",
    skeleton_of("entries", "sources"),
)
ut_series = pathlib.Path(ut_repo) / "press" / "series" / "memos"
ut_series.mkdir()
(ut_series / "series.yaml").write_text(
    "name: Memos\nmode: collection\ntemplate: memo\nautopublish: true\n"
    "strict: false\nitems:\n  - {slug: first, title: First Memo}\n"
)
fn_series = pathlib.Path(ut_repo) / "press" / "series" / "notes"
fn_series.mkdir()
(fn_series / "series.yaml").write_text(
    "name: Field Notes\nmode: collection\ntemplate: fieldnotes\n"
    "items:\n  - {slug: first-notes, title: First Notes}\n"
)
dg_series = pathlib.Path(ut_repo) / "press" / "series" / "digests"
dg_series.mkdir()
(dg_series / "series.yaml").write_text(
    "name: Digests\nmode: collection\ntemplate: digest\n"
    "items:\n  - {slug: first-digest, title: First Digest}\n"
)
crypto_series = pathlib.Path(ut_repo) / "press" / "series" / "crypto"
crypto_series.mkdir()
(crypto_series / "series.yaml").write_text(
    "name: Cryptography\nmode: sequence\ntemplate: lesson\n"
    "items:\n  - {slug: hashes, title: Hash Functions}\n"
)

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
<section data-nb-section="sources"><ol>{
    "".join(
        f'<li id="s{i}"><a data-nb-source href="https://example.org/m{i}">x</a></li>'
        for i in range(1, 6)
    )
}</ol></section>
</body></html>"""
expect(
    "article from a user-defined template passes the proof",
    run_local(MEMO, "memos", slug="first", repo=ut_repo),
    blocks=0,
)
expect(
    "user template enforces its own sections",
    run_local(
        MEMO.replace('data-nb-section="note"', 'data-nb-section="body"'),
        "memos",
        slug="first",
        repo=ut_repo,
    ),
    must_have=["B-HTML"],
)

LESSON_SECTIONS = "".join(
    f'<section data-nb-section="{s}"><p>{make_fixtures.LOREM * 7}'
    f'<sup class="nb-cite"><a href="#s{i + 1}">{i + 1}</a></sup></p></section>'
    for i, s in enumerate(("objectives", "recap", "teach", "check", "bridge"))
)
LESSON = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Hash Functions</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "crypto", "slug": "hashes",
  "template": "lesson", "title": "Hash Functions",
  "mode": "sequence", "order": 1, "date": "2026-07-06", "tags": [],
  "sources": 5, "words": 1560, "reading_minutes": 7, "dek": "Hashes.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body>{LESSON_SECTIONS}
<section data-nb-section="sources"><ol>{
    "".join(
        f'<li id="s{i}"><a data-nb-source href="https://example.org/l{i}">x</a></li>'
        for i in range(1, 6)
    )
}</ol></section>
</body></html>"""
expect(
    "the docs walkthrough lesson template passes as a fixed user template",
    run_local(LESSON, "crypto", slug="hashes", repo=ut_repo),
    blocks=0,
)
expect(
    "fixed outline (no flex_sections): an undeclared extra section blocks (V6c)",
    run_local(
        LESSON.replace(
            '<section data-nb-section="sources">',
            '<section data-nb-section="rogue"><p>extra</p></section>'
            '<section data-nb-section="sources">',
        ),
        "crypto",
        slug="hashes",
        repo=ut_repo,
    ),
    must_have=["B-HTML"],
)

print("== flex sections (agent-named outline) ==")


def flex_article(sections):
    body = "".join(
        f'<section data-nb-section="{name}"><p>{make_fixtures.LOREM * 7}'
        f"{cite}</p></section>"
        for name, cite in sections
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>First Notes</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "notes", "slug": "first-notes",
  "template": "fieldnotes", "title": "First Notes", "mode": "collection",
  "order": null, "date": "2026-07-06", "tags": [], "sources": 5,
  "words": 460, "reading_minutes": 2, "dek": "Notes.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body>{body}
<section data-nb-section="sources"><ol>{
        "".join(
            f'<li id="s{i}"><a data-nb-source href="https://example.org/n{i}">x</a></li>'
            for i in range(1, 6)
        )
    }</ol></section>
</body></html>"""


CITE1 = '<sup class="nb-cite"><a href="#s1">1</a></sup>'
CITE2 = '<sup class="nb-cite"><a href="#s2">2</a></sup>'
CITE3 = '<sup class="nb-cite"><a href="#s3">3</a></sup>'
expect(
    "flex template passes with agent-named sections in band",
    run_local(
        flex_article([("the-lab", CITE1), ("the-bet", CITE2)]),
        "notes",
        slug="first-notes",
        repo=ut_repo,
    ),
    blocks=0,
)
expect(
    "too few flex sections blocks",
    run_local(
        flex_article([("only-one", CITE1)]),
        "notes",
        slug="first-notes",
        repo=ut_repo,
    ),
    must_have=["B-HTML"],
)
expect(
    "too many flex sections blocks",
    run_local(
        flex_article([("a1", CITE1), ("a2", CITE2), ("a3", CITE3), ("a4", CITE1)]),
        "notes",
        slug="first-notes",
        repo=ut_repo,
    ),
    must_have=["B-HTML"],
)
expect(
    "duplicate flex labels block",
    run_local(
        flex_article([("twice", CITE1), ("twice", CITE2)]),
        "notes",
        slug="first-notes",
        repo=ut_repo,
    ),
    must_have=["B-HTML"],
)
expect(
    "uncited flex section warns on cite density",
    run_local(
        flex_article([("cited", CITE1), ("uncited", "")]),
        "notes",
        slug="first-notes",
        repo=ut_repo,
    ),
    blocks=0,
    must_have=["W-CITE-DENSITY"],
)
expect(
    "cite_exempt exempts a registry-declared section (not just sources)",
    run_local(
        flex_article([("context", ""), ("the-bet", CITE2)]),
        "notes",
        slug="first-notes",
        repo=ut_repo,
    ),
    blocks=0,
    must_not=["W-CITE-DENSITY"],
)
expect(
    "W-CITE-ORDER: sources cited out of first-appearance order",
    run_local(
        flex_article([("the-lab", CITE2), ("the-bet", CITE1)]),
        "notes",
        slug="first-notes",
        repo=ut_repo,
    ),
    must_have=["W-CITE-ORDER"],
    blocks=0,
)
expect(
    "in-order citations do not warn",
    run_local(
        flex_article([("the-lab", CITE1), ("the-bet", CITE2)]),
        "notes",
        slug="first-notes",
        repo=ut_repo,
    ),
    must_not=["W-CITE-ORDER"],
    blocks=0,
)

print("== require_why is registry-driven, not tied to the 'brief' template ==")


def digest_article(withhold_why):
    items = "".join(
        f"<div data-nb-item><span>t{i}</span>"
        f'<h3>Item {i}<sup class="nb-cite"><a href="#s{i}">{i}</a></sup></h3>'
        f"<p>{make_fixtures.LOREM}</p>"
        + (
            ""
            if (withhold_why and i == 1)
            else "<p data-nb-why><b>Why</b> it matters.</p>"
        )
        + "</div>"
        for i in (1, 2)
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>First Digest</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "digests", "slug": "first-digest",
  "template": "digest", "title": "First Digest", "mode": "collection",
  "order": null, "date": "2026-07-06", "tags": [], "sources": 5, "words": 60,
  "reading_minutes": 1, "dek": "A digest.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body>
<section data-nb-section="entries">{items}</section>
<section data-nb-section="sources"><ol>{
        "".join(
            f'<li id="s{i}"><a data-nb-source href="https://example.org/d{i}">x</a></li>'
            for i in range(1, 6)
        )
    }</ol></section>
</body></html>"""


expect(
    "a full digest passes (require_why satisfied)",
    run_local(
        digest_article(withhold_why=False), "digests", slug="first-digest", repo=ut_repo
    ),
    blocks=0,
    must_not=["W-WHY-MISSING"],
)
expect(
    "require_why warns for a non-brief template missing a why line",
    run_local(
        digest_article(withhold_why=True), "digests", slug="first-digest", repo=ut_repo
    ),
    must_have=["W-WHY-MISSING"],
)

ut_rc = subprocess.run(
    [sys.executable, str(REPO / "engine" / "validate_config.py"), "--repo", ut_repo],
    capture_output=True,
)
if ut_rc.returncode == 0:
    PASS += 1
    print("  ok   validate_config accepts the overlay registry")
else:
    FAIL.append("validate_config overlay")
    print(f"  FAIL validate_config overlay: {ut_rc.stdout.decode()[-300:]}")
reg = C.load_registry(ut_repo)
if "memo" in reg and "article" in reg:
    PASS += 1
    print("  ok   merged registry keeps shipped + adds press templates")
else:
    FAIL.append("registry merge")
    print(f"  FAIL registry merge: keys={sorted(reg)}")
memo_tpl = C.find_template(ut_repo, "memo") or ""
article_tpl = C.find_template(ut_repo, "article") or ""
if (
    memo_tpl.endswith("memo/skeleton.html")
    and "press" in memo_tpl
    and article_tpl.endswith("article/skeleton.html")
    and "press" not in article_tpl
):
    PASS += 1
    print("  ok   template lookup: press shadows shipped")
else:
    FAIL.append("template lookup precedence")
    print("  FAIL template lookup precedence")

print("== rhythm & governance (cadence, paused, selection) ==")


def patched_repo(patch, series="semiconductors"):
    tmp = tempfile.mkdtemp()
    for sub in ("press", "templates", "engine"):
        shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(tmp) / sub)
    y = pathlib.Path(tmp) / "press" / "series" / series / "series.yaml"
    y.write_text(y.read_text() + patch)
    return tmp


def vc_rc(repo):
    return subprocess.run(
        [
            sys.executable,
            str(REPO / "engine" / "validate_config.py"),
            "--repo",
            str(repo),
        ],
        capture_output=True,
    ).returncode


expect(
    "paused series blocks publication",
    run_local(VALID, "semiconductors", repo=patched_repo("paused: true\n")),
    must_have=["B-SERIES"],
)
for name, cond in [
    ("cadence weekdays validates", vc_rc(patched_repo("cadence: weekdays\n")) == 0),
    ("cadence day-list validates", vc_rc(patched_repo("cadence: [mon, thu]\n")) == 0),
    ("bogus cadence rejected", vc_rc(patched_repo("cadence: fortnightly\n")) == 1),
    (
        "selection random on a collection validates",
        vc_rc(patched_repo("selection: random\n")) == 0,
    ),
    (
        "selection on a rolling series rejected",
        vc_rc(patched_repo("selection: random\n", series="ai-briefs")) == 1,
    ),
    (
        "unknown series key (typo) rejected",
        vc_rc(patched_repo("cadance: daily\n")) == 1,
    ),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print("== banned terms (spec list, press overrides) ==")


def banned_repo(press_yaml=None):
    tmp = tempfile.mkdtemp()
    for sub in ("press", "templates", "spec", "engine"):
        shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(tmp) / sub)
    if press_yaml is not None:
        (pathlib.Path(tmp) / "press" / "banned-terms.yaml").write_text(press_yaml)
    return tmp


LEVERAGE_HEADING = mut("<h2>Orientation</h2>", "<h2>Leverage on leverage</h2>")
expect(
    "a banned term is counted in headings, case-insensitively",
    run_local(LEVERAGE_HEADING, "semiconductors"),
    must_have=["W-BANNED-TERM"],
    blocks=0,
)
expect(
    "a use within the limit passes",
    run_local(
        mut("<h2>Orientation</h2>", "<h2>Leverage economics</h2>"), "semiconductors"
    ),
    must_not=["W-BANNED-TERM"],
)
expect(
    "a zero-limit term trips on first use, spaced variant included",
    run_local(
        mut("<h2>Orientation</h2>", "<h2>The load bearing wall</h2>"),
        "semiconductors",
    ),
    must_have=["W-BANNED-TERM"],
)
expect(
    "press override raises an engine limit",
    run_local(
        LEVERAGE_HEADING,
        "semiconductors",
        repo=banned_repo("- id: leverage\n  max: 5\n"),
    ),
    must_not=["W-BANNED-TERM"],
)
expect(
    "press disables an engine entry",
    run_local(
        mut("<h2>Orientation</h2>", "<h2>The load bearing wall</h2>"),
        "semiconductors",
        repo=banned_repo("- id: load-bearing\n  enabled: false\n"),
    ),
    must_not=["W-BANNED-TERM"],
)
expect(
    "press adds its own ban",
    run_local(
        mut("<h2>Orientation</h2>", "<h2>Synergy in memory</h2>"),
        "semiconductors",
        repo=banned_repo(
            "- id: synergy\n  terms: [synergy]\n  max: 0\n"
            "  suggestion: name the mechanism\n"
        ),
    ),
    must_have=["W-BANNED-TERM"],
)
for name, cond in [
    (
        "press partial override validates",
        vc_rc(banned_repo("- id: em-dash\n  max: 8\n")) == 0,
    ),
    (
        "press new ban missing its suggestion rejected",
        vc_rc(banned_repo("- id: synergy\n  terms: [synergy]\n  max: 0\n")) == 1,
    ),
    (
        "banned-terms unknown key rejected",
        vc_rc(banned_repo("- id: em-dash\n  maximum: 8\n")) == 1,
    ),
    (
        "banned-terms negative max rejected",
        vc_rc(
            banned_repo(
                "- id: synergy\n  terms: [synergy]\n  max: -1\n  suggestion: s\n"
            )
        )
        == 1,
    ),
    (
        "banned-terms duplicate id rejected",
        vc_rc(banned_repo("- id: em-dash\n  max: 8\n- id: em-dash\n  max: 9\n")) == 1,
    ),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print("== placeholder leftovers (caps runs) ==")

expect(
    "clean article carries no placeholder warn",
    run_local(VALID, "semiconductors"),
    must_not=["W-PLACEHOLDER"],
)
expect(
    "a lifted skeleton placeholder trips W-PLACEHOLDER (never a block)",
    run_local(
        mut(
            "<h2>Orientation</h2>",
            "<h2>Orientation</h2>"
            "<p>OPENING PARAGRAPH WITH A CONCRETE, CITED ANCHOR CLAIM.</p>",
        ),
        "semiconductors",
    ),
    must_have=["W-PLACEHOLDER"],
    blocks=0,
)
expect(
    "a long caps run trips it even off-skeleton",
    run_local(
        mut(
            "<h2>Orientation</h2>",
            "<h2>Orientation</h2><p>REPLACE THIS ENTIRE SENTENCE TONIGHT.</p>",
        ),
        "semiconductors",
    ),
    must_have=["W-PLACEHOLDER"],
)
expect(
    "a lone skeleton placeholder word trips it",
    run_local(
        mut("<h2>Orientation</h2>", "<h2>Orientation</h2><p>TITLE goes here.</p>"),
        "semiconductors",
    ),
    must_have=["W-PLACEHOLDER"],
)
expect(
    "acronym runs shorter than the generic bar stay clean",
    run_local(
        mut(
            "<h2>Orientation</h2>",
            "<h2>Orientation</h2><p>Pricing spans HBM DRAM NAND lines.</p>",
        ),
        "semiconductors",
    ),
    must_not=["W-PLACEHOLDER"],
)

print("== open mode (the hands-off series) ==")

OPEN_YAML = """name: Wildcard
mode: open
templates: [article, brief]
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


OPEN_ED = (
    VALID.replace(
        '"series": "semiconductors", "slug": "micron",',
        '"series": "wildcard", "slug": "the-cuda-moat",',
    )
    .replace('"mode": "collection"', '"mode": "open"')
    .replace(' data-nb-required="mu-10k-2025"', "")
)
orepo = open_repo()
olib = make_library({"wildcard": []})
expect(
    "open freestyle pick is BLOCK-clean",
    run_local(OPEN_ED, "wildcard", slug="the-cuda-moat", repo=orepo, library=olib),
    blocks=0,
)
expect(
    "open duplicate slug blocked",
    run_local(
        OPEN_ED,
        "wildcard",
        slug="the-cuda-moat",
        repo=orepo,
        library=make_library({"wildcard": ["the-cuda-moat"]}),
    ),
    must_have=["B-MODE"],
)
expect(
    "open template outside the choice list blocked",
    run_local(
        OPEN_ED,
        "wildcard",
        slug="the-cuda-moat",
        repo=open_repo(
            OPEN_YAML.replace("templates: [article, brief]", "templates: [brief]")
        ),
        library=olib,
    ),
    must_have=["B-META-MATCH"],
)

queue_repo = open_repo(
    OPEN_YAML + "items:\n  - {slug: commissioned-piece, title: On Commission}\n"
)
expect(
    "pending commission blocks a freestyle pick",
    run_local(OPEN_ED, "wildcard", slug="the-cuda-moat", repo=queue_repo, library=olib),
    must_have=["B-MODE"],
)
expect(
    "publishing the commissioned item is BLOCK-clean",
    run_local(
        OPEN_ED.replace("the-cuda-moat", "commissioned-piece"),
        "wildcard",
        slug="commissioned-piece",
        repo=queue_repo,
        library=olib,
    ),
    blocks=0,
)
for name, cond in [
    ("open series with a templates list validates", vc_rc(orepo) == 0),
    (
        "'templates' on a non-open series rejected",
        vc_rc(patched_repo("templates: [article]\n")) == 1,
    ),
    (
        "open mode without any template rejected",
        vc_rc(open_repo(OPEN_YAML.replace("templates: [article, brief]\n", ""))) == 1,
    ),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print("== duty.py (tonight's work list) ==")


def duty(repo, library, *, date=TODAY):
    out = subprocess.run(
        [
            sys.executable,
            str(REPO / "engine" / "duty.py"),
            "--repo",
            str(repo),
            "--library",
            str(library),
            "--date",
            date,
        ],
        capture_output=True,
        text=True,
    )
    return json.loads(out.stdout)


def duty_of(report, sid):
    entries = report["due"] + report["idle"]
    return next((e for e in entries if e["series"] == sid), None)


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
(pathlib.Path(tonight_lib) / "library" / "semiconductors" / "micron.html").write_text(
    VALID
)  # nb-meta date == TODAY
d_tonight = duty(TESTREPO, tonight_lib)

for name, cond in [
    (
        "rolling series due tonight with tonight's slug",
        duty_of(d, "ai-briefs") in d["due"]
        and duty_of(d, "ai-briefs")["slug"] == TODAY,
    ),
    (
        "rolling already-published tonight is idle",
        duty_of(duty(TESTREPO, make_library({"ai-briefs": [TODAY]})), "ai-briefs")[
            "reason"
        ]
        == "already published tonight",
    ),
    (
        "collection in-order offers exactly the next item",
        duty_of(d_partial, "semiconductors")["candidates"] == ["tsmc"],
    ),
    (
        "collection random offers every unpublished item",
        sorted(duty_of(d_random, "semiconductors")["candidates"])
        == ["asml", "nvidia", "sk-hynix", "tsmc"],
    ),
    (
        "paused series is idle",
        duty_of(d_paused, "semiconductors")["reason"] == "paused",
    ),
    ("cadence off-night is idle", duty_of(d_cad_off, "ai-briefs") in d_cad_off["idle"]),
    (
        "open series with a queue lists commissions",
        duty_of(d_open, "wildcard")["commissions"] == ["commissioned-piece"],
    ),
    (
        "an article published tonight idles its series (rerun safety)",
        duty_of(d_tonight, "semiconductors")["reason"] == "already published tonight",
    ),
    (
        "collection complete is idle",
        duty_of(
            duty(
                TESTREPO,
                make_library(
                    {"semiconductors": ["micron", "tsmc", "asml", "sk-hynix", "nvidia"]}
                ),
            ),
            "semiconductors",
        )["reason"]
        == "complete",
    ),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print("== duty.py degrades gracefully on malformed input ==")


def overwrite_series(body, series="ai-briefs"):
    tmp = patched_repo("", series=series)
    y = pathlib.Path(tmp) / "press" / "series" / series / "series.yaml"
    # Replace the series.yaml wholesale so tests can hand duty a config shape
    # validate_config would never let through.
    y.write_text(body)
    return tmp


COLLECTION_MISSING_SLUG = (
    "name: Test\nmode: collection\ntemplate: article\n"
    "items:\n  - {slug: alpha}\n  - {title: no-slug-here}\n  - {slug: beta}\n"
)
d_missing_slug = duty(
    overwrite_series(COLLECTION_MISSING_SLUG), make_library({"ai-briefs": []})
)
d_bare_string = duty(overwrite_series("just a bare string\n"), empty_lib)
d_unparseable = duty(overwrite_series("a: b: c\n"), empty_lib)

bad_meta_lib = make_library({"semiconductors": []})
(pathlib.Path(bad_meta_lib) / "library" / "semiconductors" / "micron.html").write_text(
    '<script type="application/json" id="nb-meta">[1, 2, 3]</script>'
)
d_bad_meta = duty(TESTREPO, bad_meta_lib)

# 2026-07-06 is a Monday; a list cadence should match case-insensitively and
# fail open (treat as due) when no entry is a recognized day name.
d_cad_upper = duty(patched_repo("cadence: [Mon]\n"), empty_lib)
d_cad_unknown = duty(patched_repo("cadence: [Fortnight]\n"), empty_lib)

seq_extra_lib = make_library({"semiconductors": ["micron", "hand-extra"]})
d_seq_extra = duty(seq_repo(), seq_extra_lib)

for name, cond in [
    (
        "a dict item without a slug is dropped, not crashed on",
        duty_of(d_missing_slug, "ai-briefs")["candidates"] == ["alpha"],
    ),
    (
        "a non-dict series.yaml idles that one series with a reason",
        duty_of(d_bare_string, "ai-briefs")["reason"] == "series.yaml is not a mapping"
        and duty_of(d_bare_string, "ai-briefs") in d_bare_string["idle"],
    ),
    (
        "one bad series never takes down the others",
        duty_of(d_bare_string, "semiconductors") is not None,
    ),
    (
        "unparseable series.yaml idles rather than aborting the run",
        duty_of(d_unparseable, "ai-briefs")["reason"] == "series.yaml is not a mapping",
    ),
    (
        "a non-dict nb-meta payload does not crash published_state",
        duty_of(d_bad_meta, "semiconductors")["candidates"] == ["tsmc"],
    ),
    (
        "list cadence matches case-insensitively (Mon on a Monday is due)",
        duty_of(d_cad_upper, "semiconductors") in d_cad_upper["due"],
    ),
    (
        "list cadence with no recognized day fails open (due)",
        duty_of(d_cad_unknown, "semiconductors") in d_cad_unknown["due"],
    ),
    (
        "sequence progress counts syllabus items, not library extras",
        duty_of(d_seq_extra, "semiconductors")["reason"].startswith("1 of 5 published"),
    ),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print("== morning gate (the mail's decision, out of the workflow) ==")


def gate_out(**kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.suppress(SystemExit):
        MG.out(**kwargs)
    return buf.getvalue()


notice = MG.quiet_notice(
    "The Test Build", missed="the-wire, the-world", latest="2026-07-10", age=3
)
for name, cond in [
    (
        "latest build is the newest date, never the dateless bucket",
        MG.latest_build(["unknown", "2026-07-10", "2026-07-12"]) == "2026-07-12",
    ),
    (
        "a library of only dateless articles has no latest build",
        MG.latest_build(["unknown"]) is None and MG.latest_build([]) is None,
    ),
    (
        "quiet notice names the missed series and the staleness",
        "the-wire, the-world" in notice and "2026-07-10 (3 nights ago)" in notice,
    ),
    (
        "out() speaks the workflow's four-output contract",
        gate_out(send=True, why="w", body="b.html", subject="s")
        == "send=true\nwhy=w\nbody=b.html\nsubject=s\n",
    ),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print("== PR mode (real git repo) ==")


def git(*args, cwd):
    cmd = ["git", *args]
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


prdir = tempfile.mkdtemp()
for sub in ("press", "templates"):
    shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(prdir) / sub)
shutil.copytree(
    REPO / "engine",
    pathlib.Path(prdir) / "engine",
    ignore=shutil.ignore_patterns("__pycache__", "fixtures"),
)
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
body.write_text("""Nightly article.

```nb-meta
series: semiconductors
slug: micron
mode: collection
template: article
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
        repo=prdir,
        main=None,
        base="library",
        head="claude/night-run",
        pr_body=str(extra_body or body),
        library=None,
        today=TODAY,
        check_links=False,
    )
    C.run_pr_mode(args, rep)
    return rep


expect("PR happy path", run_pr(), blocks=0)

badbody = pathlib.Path(prdir, "prbody-bad.txt")
badbody.write_text(body.read_text().replace("slug: micron", "slug: tsmc"))
expect(
    "PR body disagrees with file",
    run_pr(extra_body=badbody),
    must_have=["B-META-MATCH"],
)

nobody = pathlib.Path(prdir, "prbody-none.txt")
nobody.write_text("no metadata block here")
expect(
    "PR body missing nb-meta block",
    run_pr(extra_body=nobody),
    must_have=["B-META-MATCH"],
)


def add_second_file():
    p = pathlib.Path(prdir, "library", "semiconductors", "extra.txt")
    p.write_text("x")
    git("add", "-A", cwd=prdir)
    git("commit", "-qm", "extra", cwd=prdir)


expect(
    "PR touching two files", run_pr(mutate=add_second_file), must_have=["B-DIFF-SHAPE"]
)

git("reset", "-q", "--hard", "HEAD~1", cwd=prdir)


def modify_engine():
    p = pathlib.Path(prdir, "engine", "check.py")
    p.write_text(p.read_text() + "\n# sneak\n")
    git("add", "-A", cwd=prdir)
    git("commit", "-qm", "sneak", cwd=prdir)


expect(
    "PR modifying engine code", run_pr(mutate=modify_engine), must_have=["B-DIFF-SHAPE"]
)

git("reset", "-q", "--hard", "HEAD~1", cwd=prdir)

git("checkout", "-q", "library", cwd=prdir)
pub = pathlib.Path(prdir, "library", "semiconductors")
pub.mkdir(parents=True, exist_ok=True)
(pub / "tsmc.html").write_text(VALID)
git("add", "-A", cwd=prdir)
git("commit", "-qm", "published", cwd=prdir)
git("checkout", "-qb", "owner/curation", cwd=prdir)
git("rm", "-q", "library/semiconductors/tsmc.html", cwd=prdir)
git("commit", "-qm", "retract", cwd=prdir)


def run_curation(flag):
    rep = C.Report()
    args = types.SimpleNamespace(
        repo=prdir,
        main=None,
        base="library",
        head="owner/curation",
        pr_body=None,
        library=None,
        today=TODAY,
        check_links=False,
        deletions_by_owner=flag,
    )
    C.run_pr_mode(args, rep)
    return rep


expect(
    "deletion-only PR without the owner flag",
    run_curation(False),
    must_have=["B-DIFF-SHAPE"],
)
expect("owner curation deletion-only PR", run_curation(True), blocks=0)

git("rm", "-q", "engine/duty.py", cwd=prdir)
git("commit", "-qm", "stray deletion", cwd=prdir)
expect(
    "owner curation deleting engine files",
    run_curation(True),
    must_have=["B-DIFF-SHAPE"],
)

print("== chrome ==")

declared = {"chrome": ['<body class="nb-article">', "<b>Why it matters</b>:"]}
rep_ok = C.Report()
C.check_chrome(
    '<body class="nb-article"><b>Why it matters</b>: y</body>',
    treg=declared,
    rep=rep_ok,
)
expect("chrome intact passes", rep_ok, blocks=0)
rep_bad = C.Report()
C.check_chrome(
    '<body class="nb-edition"><b>Why it matters \u2192</b> y</body>',
    treg=declared,
    rep=rep_bad,
)
expect("mutated chrome blocks", rep_bad, must_have=["B-CHROME"])
rep_none = C.Report()
C.check_chrome("<body></body>", treg={}, rep=rep_none)
expect("no chrome declared, no check", rep_none, blocks=0)

rep_dc = C.Report()
C.check_classes(
    '<body class="nb-article"><p class="nb-callout">x</p><p class="nb-callot">y</p></body>',
    repo=str(REPO),
    rep=rep_dc,
)
expect("a typo'd class trips W-DEAD-CLASS", rep_dc, must_have=["W-DEAD-CLASS"])
rep_dc2 = C.Report()
C.check_classes(
    '<body class="nb-article"><p class="nb-callout">x</p><code class="language-python">y</code></body>',
    repo=str(REPO),
    rep=rep_dc2,
)
expect(
    "defined and allowlisted classes pass", rep_dc2, blocks=0, must_not=["W-DEAD-CLASS"]
)

print("== validate_config ==")
vc = REPO / "engine" / "validate_config.py"
# the shipped examples/ must validate when used as a press
ex_repo = pathlib.Path(tempfile.mkdtemp()) / "repo"
ex_repo.mkdir()
shutil.copytree(REPO / "templates", ex_repo / "templates")
shutil.copytree(REPO / "engine" / "assets", ex_repo / "engine" / "assets")
shutil.copytree(REPO / "examples", ex_repo / "press")
rc_good = subprocess.run(
    [sys.executable, str(vc), "--repo", str(ex_repo)], capture_output=True
).returncode
broken = pathlib.Path(tempfile.mkdtemp()) / "repo"
shutil.copytree(TESTREPO, broken)
by = pathlib.Path(broken) / "press" / "series" / "semiconductors" / "series.yaml"
by.write_text(by.read_text().replace("mode: collection", "mode: rolling"))
rc_bad = subprocess.run(
    [sys.executable, str(vc), "--repo", broken], capture_output=True
).returncode
for name, cond in [
    ("shipped examples validate as a press", rc_good == 0),
    ("illegal mode/template pairing fails", rc_bad == 1),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")


def vc_site_errors(yaml_text):
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "press").mkdir()
    (d / "press" / "site.yaml").write_text(yaml_text)
    errs = []
    V.check_site(str(d), errs)
    return errs


def vc_directory_errors(directory):
    errs = []
    V.check_site_directory(directory, errors=errs)
    return errs


for name, cond in [
    (
        "footer: a valid imprint passes",
        vc_site_errors('title: "x"\nfooter: "Filed."\n') == [],
    ),
    (
        "footer: over 80 chars fails",
        vc_site_errors(f'title: "x"\nfooter: "{"a" * 81}"\n') != [],
    ),
    ("footer: empty string fails", vc_site_errors('title: "x"\nfooter: ""\n') != []),
    (
        "directory: opted-in block validates",
        vc_directory_errors({"publish": True, "description": "hi"}) == [],
    ),
    (
        "directory: opt-out block validates",
        vc_directory_errors({"publish": False}) == [],
    ),
    (
        "directory: listed with no description validates (opt-out default)",
        vc_directory_errors({}) == [] and vc_directory_errors({"publish": True}) == [],
    ),
    (
        "directory: a url key is rejected as redundant",
        vc_directory_errors({"publish": True, "description": "hi", "url": "x"}) != [],
    ),
    (
        "directory: non-bool publish fails",
        vc_directory_errors({"publish": "yes", "description": "hi"}) != [],
    ),
    (
        "directory: description over 280 chars fails",
        vc_directory_errors({"publish": True, "description": "a" * 281}) != [],
    ),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print()
print("== validate_config catches malformed series before an unattended run ==")


def vc_output(repo):
    r = subprocess.run(
        [sys.executable, str(vc), "--repo", str(repo)],
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stdout, r.stderr


REQ_DOCS_NOT_LIST = "name: X\nmode: rolling\ntemplate: brief\nrequired_docs: nope\n"
REQ_DOC_NOT_MAP = (
    "name: X\nmode: collection\ntemplate: article\n"
    "items:\n  - {slug: alpha, required_docs: [oops]}\n"
)
TWO_SLUGLESS = (
    "name: X\nmode: collection\ntemplate: article\n"
    "items:\n  - {title: one}\n  - {title: two}\n"
)
DUP_SLUG = (
    "name: X\nmode: collection\ntemplate: article\n"
    "items:\n  - {slug: alpha}\n  - {slug: alpha}\n"
)


def manifest_patched_repo(patch, template="article"):
    tmp = tempfile.mkdtemp()
    for sub in ("press", "templates", "engine"):
        shutil.copytree(pathlib.Path(TESTREPO) / sub, pathlib.Path(tmp) / sub)
    m = pathlib.Path(tmp) / "templates" / template / "manifest.yaml"
    # A repeated key is fine here: yaml keeps the last one, the patch.
    m.write_text(m.read_text() + patch)
    return tmp


rc_unparseable, out_unparseable, err_unparseable = vc_output(
    overwrite_series("a: b: c\n")
)
rc_nonmap, out_nonmap, err_nonmap = vc_output(overwrite_series("just a bare string\n"))
_, out_reqlist, _ = vc_output(overwrite_series(REQ_DOCS_NOT_LIST))
_, out_reqmap, _ = vc_output(overwrite_series(REQ_DOC_NOT_MAP))
_, out_slugless, _ = vc_output(overwrite_series(TWO_SLUGLESS))
_, out_dup, _ = vc_output(overwrite_series(DUP_SLUG))

for name, cond in [
    (
        "autopublish: 'false' (a truthy string) is a validation error",
        vc_rc(patched_repo("autopublish: 'false'\n")) == 1,
    ),
    (
        "strict: 'no' (a truthy string) is a validation error",
        vc_rc(patched_repo("strict: 'no'\n")) == 1,
    ),
    (
        "min_sources: lots (a string) is a validation error",
        vc_rc(patched_repo("min_sources: lots\n")) == 1,
    ),
    (
        "a well-typed min_sources still validates",
        vc_rc(patched_repo("min_sources: 12\n")) == 0,
    ),
    (
        "unparseable series.yaml is a readable error, not a traceback",
        rc_unparseable == 1
        and "not valid YAML" in out_unparseable
        and "Traceback" not in err_unparseable,
    ),
    (
        "a non-dict series.yaml is a readable error, not a traceback",
        rc_nonmap == 1
        and "must be a mapping" in out_nonmap
        and "Traceback" not in err_nonmap,
    ),
    (
        "series-level required_docs must be a list",
        "'required_docs' must be a list" in out_reqlist,
    ),
    (
        "a required_docs entry must be a mapping",
        "required_docs entry must be a mapping" in out_reqmap,
    ),
    (
        "two slugless items report two slug errors, never a false duplicate",
        "duplicate item slug" not in out_slugless,
    ),
    (
        "a genuine duplicate slug is still caught",
        "duplicate item slug 'alpha'" in out_dup,
    ),
    (
        "chrome quoting the skeleton verbatim validates",
        vc_rc(manifest_patched_repo("chrome: ['<body class=\"nb-article\">']\n")) == 0,
    ),
    (
        "chrome the skeleton does not contain is the author's error",
        vc_rc(manifest_patched_repo("chrome: ['<body class=\"nb-elsewhere\">']\n"))
        == 1,
    ),
    (
        "a scalar chrome is a validation error, never a vacuous pass",
        vc_rc(manifest_patched_repo('chrome: "<h2>Sources</h2>"\n')) == 1,
    ),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print()
print("== ci_helpers (the workflow's facts) ==")


def ci_helper(cmd, series_yaml):
    repo = tempfile.mkdtemp()
    sd = pathlib.Path(repo) / "press" / "series" / "foo"
    sd.mkdir(parents=True)
    (sd / "series.yaml").write_text(series_yaml)
    git("init", "-q", "-b", "main", cwd=repo)
    git("config", "user.email", "t@t", cwd=repo)
    git("config", "user.name", "t", cwd=repo)
    git("add", "-A", cwd=repo)
    git("commit", "-qm", "config", cwd=repo)
    git("checkout", "-qb", "night", cwd=repo)
    lib = pathlib.Path(repo) / "library" / "foo"
    lib.mkdir(parents=True)
    (lib / "story.html").write_text("<html></html>")
    git("add", "-A", cwd=repo)
    git("commit", "-qm", "nb: foo/story", cwd=repo)
    # ci_helpers reads the diff from the current working directory (check.yml
    # runs it inside the checkout), so drive it with cwd set to the repo.
    return subprocess.run(
        [
            sys.executable,
            str(REPO / "engine" / "ci_helpers.py"),
            cmd,
            "--repo",
            repo,
            "--diff-base",
            "main",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout.strip()


for name, cond in [
    (
        "autopublish: true enables auto-merge",
        ci_helper("autopublish", "autopublish: true\n") == "true",
    ),
    (
        "autopublish: false disables it",
        ci_helper("autopublish", "autopublish: false\n") == "false",
    ),
    (
        "autopublish absent disables it",
        ci_helper("autopublish", "mode: rolling\n") == "false",
    ),
    (
        "autopublish: 'false' (string) never auto-merges",
        ci_helper("autopublish", "autopublish: 'false'\n") == "false",
    ),
    (
        "autopublish: 'true' (string) never auto-merges",
        ci_helper("autopublish", "autopublish: 'true'\n") == "false",
    ),
    (
        "autopublish: 1 (int) never auto-merges",
        ci_helper("autopublish", "autopublish: 1\n") == "false",
    ),
    (
        "article-path prints the PR's one added article",
        ci_helper("article-path", "autopublish: true\n") == "library/foo/story.html",
    ),
]:
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print()
print("== source link resolution classifier ==")
# B-SOURCE-DEAD blocks only on definitive death; everything ambiguous passes,
# so a real-but-restricted source (or an offline runner) never false-blocks.
link_cases = [
    ("404 is dead", C.classify_link(404, None) == "dead"),
    ("410 is dead", C.classify_link(410, None) == "dead"),
    ("domain that does not resolve is dead", C.classify_link(None, "dns") == "dead"),
    ("200 exists", C.classify_link(200, None) == "ok"),
    ("403 bot-block is not dead", C.classify_link(403, None) == "ok"),
    ("500 is not dead", C.classify_link(500, None) == "ok"),
    ("timeout is unverified, never dead", C.classify_link(None, "net") == "unverified"),
    ("no links to probe returns empty", C.dead_source_links([]) == []),
]
for name, ok in link_cases:
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print()
print("== rehearsal honors --check-links (parity with CI) ==")


# 1.5: the local (rehearsal) branch of main() must forward --check-links, or a
# dead citation passes the press check yet fails B-SOURCE-DEAD in CI. Every source
# points at the reserved `.invalid` TLD (RFC 6761), which never resolves — so the
# probe classifies it dead offline or online, making this deterministic without a
# real network round-trip. The assertion is purely about whether main() wires the
# flag through: links-on must surface B-SOURCE-DEAD, --no-check-links must not.
def run_main_json(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        C.main(argv)
    return json.loads(buf.getvalue())


_dead_article = VALID.replace(
    "https://example.org/", "https://nb-dead.invalid/"
).replace("https://www.sec.gov/filings/mu-10k", "https://nb-dead.invalid/sec")
_link_tmp = tempfile.mkdtemp()
_art = pathlib.Path(_link_tmp) / "library" / "semiconductors" / "micron.html"
_art.parent.mkdir(parents=True)
_art.write_text(_dead_article)
_common = [
    str(_art),
    "--series",
    "semiconductors",
    "--repo",
    TESTREPO,
    "--today",
    TODAY,
    "--json",
]
links_on = run_main_json(_common)
links_off = run_main_json([*_common, "--no-check-links"])
shutil.rmtree(_link_tmp)
on_codes = {f["code"] for f in links_on["findings"]}
off_codes = {f["code"] for f in links_off["findings"]}
link_flag_cases = [
    ("local mode probes links by default", "B-SOURCE-DEAD" in on_codes),
    ("--no-check-links suppresses probing locally", "B-SOURCE-DEAD" not in off_codes),
]
for name, ok in link_flag_cases:
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")

print()
print("== workflow trigger safety (fork-token guarantee) ==")
# The editor auto-merges article PRs, so the only thing stopping a stranger from
# force-publishing to a fork is GitHub's rule that a pull_request run from a fork
# gets a read-only token. That holds only while check.yml uses `pull_request`;
# `pull_request_target` would hand fork PRs a writable token and break it. Lock
# the trigger so a future edit cannot silently regress the guarantee.
check_yml_text = (REPO / ".github" / "workflows" / "check.yml").read_text()
check_yml_on = yaml.safe_load(check_yml_text)
# PyYAML parses the bare key `on` as the boolean True (YAML 1.1); accept either.
check_yml_triggers = check_yml_on.get("on", check_yml_on.get(True)) or {}
trigger_names = (
    set(check_yml_triggers)
    if isinstance(check_yml_triggers, dict)
    else {check_yml_triggers}
)
wf_cases = [
    ("check.yml triggers on pull_request", "pull_request" in trigger_names),
    (
        "check.yml never uses pull_request_target",
        "pull_request_target" not in trigger_names,
    ),
]
for name, ok in wf_cases:
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name}")


def run_suite(script, label):
    global PASS
    print(f"== {label} ({script}) ==")
    proc = subprocess.run(
        [sys.executable, str(HERE / script)], capture_output=True, text=True
    )
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    # Fold the subprocess suite's own assertion counts into this runner's totals,
    # so the summary reports real coverage instead of dropping the builder and
    # e2e assertions.
    m = _re.search(r"(\d+) passed, (\d+) failed", proc.stdout)
    if m:
        PASS += int(m.group(1))
    if proc.returncode != 0:
        FAIL.append(f"{label} ({m.group(2) if m else '?'} failed)")


print()
run_suite("run_builder_tests.py", "builder suite")
print()
run_suite("run_e2e_test.py", "end-to-end dress rehearsal")

print()
print(f"{PASS} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
