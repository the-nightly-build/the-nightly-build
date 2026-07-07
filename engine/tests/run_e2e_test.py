#!/usr/bin/env python3
"""
End-to-end dress rehearsal for The Nightly Build (handoff §13.6, local half).

Simulates two nights against a REAL git repo laid out exactly like production:
main (engine + config) and an orphan library branch. Each "night shift run"
branches off library, adds one edition, is validated in PR mode (the identical
invocation check.yml makes), gated by the autopublish helper, squash-merged,
and the site is rebuilt from the merged library (as publish.yml does).

Night 1 (2026-07-05): collection edition + rolling brief  → multi-edition build
Night 2 (2026-07-06): rolling brief                       → feeds/pages update

The cloud half — a real scheduled run on a fork for two nights — is a human-run
verification; see the phase 6 runbook.

Run: python3 engine/tests/run_e2e_test.py
"""

import datetime as dt
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import _bootstrap
import build_site as B
import make_fixtures

REPO = _bootstrap.REPO

PASS, FAIL = 0, []
NS = "{http://www.w3.org/2005/Atom}"


def check(name, condition, *, detail=""):
    global PASS
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL {name} {detail}")


def git(*args, cwd):
    cmd = ["git", *args]
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def run(cmd, cwd=None):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc


# ---------------------------------------------------------------- the press
root = make_fixtures.test_repo()
shutil.copytree(
    REPO / "engine",
    pathlib.Path(root) / "engine",
    ignore=shutil.ignore_patterns("__pycache__", "fixtures"),
    dirs_exist_ok=True,
)
shutil.copytree(REPO / "spec", pathlib.Path(root) / "spec")
shutil.copyfile(REPO / "PROTOCOL.md", pathlib.Path(root) / "PROTOCOL.md")
git("init", "-q", "-b", "main", cwd=root)
git("config", "user.email", "night@shift", cwd=root)
git("config", "user.name", "night-shift", cwd=root)
git("add", "-A", cwd=root)
git("commit", "-qm", "engine", cwd=root)
git("checkout", "-q", "--orphan", "library", cwd=root)
git("rm", "-rfq", ".", cwd=root)
pathlib.Path(root, "library").mkdir()
pathlib.Path(root, "library", ".gitkeep").write_text("")
git("add", "-A", cwd=root)
git("commit", "-qm", "library: initialize the empty press", cwd=root)

# scratch dirs live OUTSIDE the git worktree so agent commits stay one-file
scratch = pathlib.Path(tempfile.mkdtemp())
libdir = str(scratch / "libstate")
maindir = str(scratch / "mainstate")
sitedir = scratch / "site"
pathlib.Path(libdir).mkdir()
pathlib.Path(maindir).mkdir()
subprocess.run(
    f"git archive main | tar -x -C {maindir}", shell=True, cwd=root, check=True
)


def library_state():
    # refresh a plain-dir snapshot of the library branch (what CI checks out)
    for child in pathlib.Path(libdir).iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    subprocess.run(
        f"git archive library | tar -x -C {libdir}", shell=True, cwd=root, check=True
    )
    return libdir


def night_shift_run(branch, series, *, slug, html, today, from_ref="library"):
    # one agent run: branch off library, add one edition, validate as CI does
    git("checkout", "-q", from_ref, cwd=root)
    git("checkout", "-qb", branch, cwd=root)
    d = pathlib.Path(root, "library", series)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.html").write_text(html)
    git("add", "-A", cwd=root)
    git("commit", "-qm", f"nb: {series}/{slug}", cwd=root)

    body = scratch / f"prbody-{branch.replace('/', '-')}.txt"
    meta = json.loads(html.split('id="nb-meta">')[1].split("</script>")[0])
    body.write_text(
        "Nightly edition.\n\n```nb-meta\n"
        f"series: {series}\nslug: {slug}\nmode: {meta['mode']}\n"
        f'template: {meta["template"]}\ndate: "{meta["date"]}"\n'
        f'title: "{meta["title"]}"\norder: {meta["order"] or "null"}\n```\n'
    )

    # exactly the editor's invocation: engine + configs from the main
    # checkout, git diff + edition file from the PR checkout
    proof = run(
        [
            sys.executable,
            str(pathlib.Path(maindir, "engine", "check.py")),
            "--pr",
            "--repo",
            root,
            "--main",
            maindir,
            "--base",
            "library",
            "--head",
            branch,
            "--library",
            library_state(),
            "--pr-body",
            str(body),
            "--today",
            today,
            "--json",
        ],
        cwd=root,
    )
    findings = json.loads(proof.stdout)
    auto = run(
        [
            sys.executable,
            str(pathlib.Path(maindir, "engine", "ci_helpers.py")),
            "autopublish",
            "--repo",
            maindir,
            "--diff-base",
            "library",
        ],
        cwd=root,
    ).stdout.strip()
    return findings, auto


def editor_merge(branch):
    git("checkout", "-q", "library", cwd=root)
    git("merge", "-q", "--squash", branch, cwd=root)
    git("commit", "-qm", f"nb: merge {branch}", cwd=root)


def press_run(now_iso):
    if sitedir.exists():
        shutil.rmtree(sitedir)
    return B.build(
        maindir,
        library_state(),
        out=str(sitedir),
        now=dt.datetime.fromisoformat(now_iso),
    )


# ------------------------------------------------------------------ night 1
print("== night 1: collection article + rolling brief (2026-07-05) ==")
article_ed = make_fixtures.article().replace("2026-07-06", "2026-07-05")
findings, auto = night_shift_run(
    "nb/n1-micron", "semiconductors", slug="micron", html=article_ed, today="2026-07-05"
)
check(
    "article PR validates BLOCK-clean in CI mode",
    findings["block_count"] == 0,
    detail=str(findings["findings"]),
)
check("autopublish gate says true", auto == "true")
editor_merge("nb/n1-micron")

brief1 = make_fixtures.brief("2026-07-05")
pre_merge_ref = subprocess.run(
    ["git", "rev-parse", "library"], cwd=root, capture_output=True, text=True
).stdout.strip()
findings, auto = night_shift_run(
    "nb/n1-brief", "ai-briefs", slug="2026-07-05", html=brief1, today="2026-07-05"
)
check(
    "brief PR validates BLOCK-clean in CI mode",
    findings["block_count"] == 0,
    detail=str(findings["findings"]),
)
editor_merge("nb/n1-brief")

catalog1 = press_run("2026-07-05T09:00:00+00:00")
front1 = (sitedir / "index.html").read_text()
check(
    "front page shows a multi-edition build",
    "nb-lead-cell" in front1 and 'class="nb-grid"' in front1,
)
check(
    "night 1 build page lists both editions",
    catalog1["builds"]["2026-07-05"]
    == ["ai-briefs/2026-07-05", "semiconductors/micron"],
)
feed1 = ET.fromstring((sitedir / "feed.xml").read_text())
check("feed has night 1 entries", len(feed1.findall(f"{NS}entry")) == 2)

# ------------------------------------------------------- duplicate-night guard
# a competing agent raced the same slug from the pre-merge base and lost
print("== rolling race: losing PR for the same night is refused ==")
rival = brief1.replace("Daily brief for 2026-07-05", "Rival brief for 2026-07-05")
findings, _ = night_shift_run(
    "nb/n1-dupe",
    "ai-briefs",
    slug="2026-07-05",
    html=rival,
    today="2026-07-05",
    from_ref=pre_merge_ref,
)
check(
    "already-published brief is BLOCKed (B-MODE)",
    any(f["code"] == "B-MODE" for f in findings["findings"]),
    detail=str(findings["findings"]),
)
git("checkout", "-q", "library", cwd=root)

# ------------------------------------------------------------------ night 2
print("== night 2: rolling brief (2026-07-06) ==")
brief2 = make_fixtures.brief("2026-07-06")
findings, auto = night_shift_run(
    "nb/n2-brief", "ai-briefs", slug="2026-07-06", html=brief2, today="2026-07-06"
)
check(
    "night 2 brief validates BLOCK-clean",
    findings["block_count"] == 0,
    detail=str(findings["findings"]),
)
editor_merge("nb/n2-brief")

catalog2 = press_run("2026-07-06T09:00:00+00:00")
front2 = (sitedir / "index.html").read_text()
check(
    "front page rolled over to night 2",
    "July 6, 2026" in front2 and "2026-07-06" in json.dumps(catalog2["builds"]),
)
check(
    "both nights preserved in the archive",
    list(catalog2["builds"]) == ["2026-07-06", "2026-07-05"],
)
check(
    "night 1 build page still exists",
    (sitedir / "builds" / "2026-07-05" / "index.html").is_file(),
)
check(
    "build pages link prev/next across nights",
    'href="../2026-07-05/"'
    in (sitedir / "builds" / "2026-07-06" / "index.html").read_text(),
)
feed2 = ET.fromstring((sitedir / "feed.xml").read_text())
check("global feed updated to 3 entries", len(feed2.findall(f"{NS}entry")) == 3)
series_feed = ET.fromstring((sitedir / "series" / "ai-briefs" / "feed.xml").read_text())
check("series feed updated to 2 entries", len(series_feed.findall(f"{NS}entry")) == 2)
check(
    "sections page shows collection progress 1 of 5",
    "1 of 5" in (sitedir / "series" / "index.html").read_text(),
)

print()
print(f"{PASS} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
