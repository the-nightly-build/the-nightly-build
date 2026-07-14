"""The dress rehearsal: two nights against a real git press.

The press is laid out exactly like production — main carries the engine and the
config, an orphan library branch carries what shipped. Each night shift branches
off library, adds one article, is proofed in PR mode with the identical
invocation check.yml makes, is gated by the autopublish helper, is squash-merged,
and the site is rebuilt from the merged library as publish.yml does.

Night 1 (2026-07-05): a collection article and a rolling brief.
Night 2 (2026-07-06): a rolling brief.

The cloud half — a real scheduled run on a fork, for two nights — stays a
human-run verification; see the phase 6 runbook.
"""

import dataclasses
import datetime as dt
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import build_site
import pytest
from press import REPO, article, brief, git, make_press

pytestmark = pytest.mark.slow

NS = "{http://www.w3.org/2005/Atom}"


class Press:
    """A real git press, and the night shift that runs against it."""

    def __init__(self) -> None:
        self.root = make_press()
        shutil.copytree(
            REPO / "engine",
            pathlib.Path(self.root) / "engine",
            ignore=shutil.ignore_patterns("__pycache__"),
            dirs_exist_ok=True,
        )
        shutil.copyfile(REPO / "PROTOCOL.md", pathlib.Path(self.root) / "PROTOCOL.md")
        git("init", "-q", "-b", "main", cwd=self.root)
        git("config", "user.email", "night@shift", cwd=self.root)
        git("config", "user.name", "night-shift", cwd=self.root)
        git("add", "-A", cwd=self.root)
        git("commit", "-qm", "engine", cwd=self.root)
        git("checkout", "-q", "--orphan", "library", cwd=self.root)
        git("rm", "-rfq", ".", cwd=self.root)
        pathlib.Path(self.root, "library").mkdir()
        pathlib.Path(self.root, "library", ".gitkeep").write_text("")
        git("add", "-A", cwd=self.root)
        git("commit", "-qm", "library: initialize the empty press", cwd=self.root)

        # scratch dirs live OUTSIDE the worktree, so a night's commit stays one file
        self.scratch = pathlib.Path(tempfile.mkdtemp())
        self.libdir = self.scratch / "libstate"
        self.maindir = self.scratch / "mainstate"
        self.sitedir = self.scratch / "site"
        self.libdir.mkdir()
        self.maindir.mkdir()
        self._archive("main", self.maindir)

    def _archive(self, ref: str, into: pathlib.Path) -> None:
        subprocess.run(
            f"git archive {ref} | tar -x -C {into}",
            shell=True,
            cwd=self.root,
            check=True,
        )

    def library_state(self) -> str:
        for child in self.libdir.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
        self._archive("library", self.libdir)
        return str(self.libdir)

    def rev(self, ref: str) -> str:
        return subprocess.run(
            ["git", "rev-parse", ref], cwd=self.root, capture_output=True, text=True
        ).stdout.strip()

    def night_shift_run(
        self,
        branch: str,
        series: str,
        *,
        slug: str,
        html: str,
        today: str,
        from_ref: str = "library",
    ) -> tuple[dict, str]:
        git("checkout", "-q", from_ref, cwd=self.root)
        git("checkout", "-qb", branch, cwd=self.root)
        d = pathlib.Path(self.root, "library", series)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{slug}.html").write_text(html)
        git("add", "-A", cwd=self.root)
        git("commit", "-qm", f"nb: {series}/{slug}", cwd=self.root)

        body = self.scratch / f"prbody-{branch.replace('/', '-')}.txt"
        meta = json.loads(html.split('id="nb-meta">')[1].split("</script>")[0])
        body.write_text(
            "Nightly article.\n\n```nb-meta\n"
            f"series: {series}\nslug: {slug}\nmode: {meta['mode']}\n"
            f'template: {meta["template"]}\ndate: "{meta["date"]}"\n'
            f'title: "{meta["title"]}"\norder: {meta["order"] or "null"}\n```\n'
        )

        # exactly the editor's invocation: engine and configs from the main
        # checkout, the git diff and the article file from the PR checkout
        proof = self._run(
            str(self.maindir / "engine" / "check.py"),
            "--pr",
            "--repo",
            self.root,
            "--main",
            str(self.maindir),
            "--base",
            "library",
            "--head",
            branch,
            "--library",
            self.library_state(),
            "--pr-body",
            str(body),
            "--today",
            today,
            "--no-check-links",  # the rehearsal runs offline and deterministic
            "--json",
        )
        autopublish = self._run(
            str(self.maindir / "engine" / "ci_helpers.py"),
            "autopublish",
            "--repo",
            str(self.maindir),
            "--diff-base",
            "library",
        ).strip()
        return json.loads(proof), autopublish

    def _run(self, script: str, *args: str) -> str:
        return subprocess.run(
            [sys.executable, script, *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        ).stdout

    def merge(self, branch: str) -> None:
        git("checkout", "-q", "library", cwd=self.root)
        git("merge", "-q", "--squash", branch, cwd=self.root)
        git("commit", "-qm", f"nb: merge {branch}", cwd=self.root)

    def publish(self, now_iso: str) -> dict:
        if self.sitedir.exists():
            shutil.rmtree(self.sitedir)
        return build_site.build(
            str(self.maindir),
            self.library_state(),
            out=str(self.sitedir),
            now=dt.datetime.fromisoformat(now_iso),
        )

    def site_text(self, *parts: str) -> str:
        return pathlib.Path(self.sitedir, *parts).read_text()


@dataclasses.dataclass(frozen=True)
class Rehearsal:
    """Everything the two nights produced, captured as they happened."""

    press: Press
    article_findings: dict
    autopublish: str
    brief_findings: dict
    catalog1: dict
    front1: str
    feed1: str
    rival_findings: dict
    night2_findings: dict
    catalog2: dict
    front2: str


@pytest.fixture(scope="module")
def rehearsal() -> Rehearsal:
    press = Press()

    article_findings, autopublish = press.night_shift_run(
        "nb/n1-micron",
        "semiconductors",
        slug="micron",
        html=article().replace("2026-07-06", "2026-07-05"),
        today="2026-07-05",
    )
    press.merge("nb/n1-micron")

    # the base a competing agent would have branched from, before the brief merged
    pre_merge_ref = press.rev("library")
    brief_findings, _ = press.night_shift_run(
        "nb/n1-brief",
        "ai-briefs",
        slug="2026-07-05",
        html=brief("2026-07-05"),
        today="2026-07-05",
    )
    press.merge("nb/n1-brief")

    catalog1 = press.publish("2026-07-05T09:00:00+00:00")
    front1 = press.site_text("index.html")
    feed1 = press.site_text("feed.xml")

    # a competing agent raced the same slug from the pre-merge base, and lost
    rival_findings, _ = press.night_shift_run(
        "nb/n1-dupe",
        "ai-briefs",
        slug="2026-07-05",
        html=brief("2026-07-05").replace(
            "Daily brief for 2026-07-05", "Rival brief for 2026-07-05"
        ),
        today="2026-07-05",
        from_ref=pre_merge_ref,
    )
    git("checkout", "-q", "library", cwd=press.root)

    night2_findings, _ = press.night_shift_run(
        "nb/n2-brief",
        "ai-briefs",
        slug="2026-07-06",
        html=brief("2026-07-06"),
        today="2026-07-06",
    )
    press.merge("nb/n2-brief")

    catalog2 = press.publish("2026-07-06T09:00:00+00:00")

    return Rehearsal(
        press=press,
        article_findings=article_findings,
        autopublish=autopublish,
        brief_findings=brief_findings,
        catalog1=catalog1,
        front1=front1,
        feed1=feed1,
        rival_findings=rival_findings,
        night2_findings=night2_findings,
        catalog2=catalog2,
        front2=press.site_text("index.html"),
    )


def entry_count(feed_xml: str) -> int:
    return len(ET.fromstring(feed_xml).findall(f"{NS}entry"))


def test_the_article_pr_validates_block_clean(rehearsal: Rehearsal) -> None:
    assert rehearsal.article_findings["block_count"] == 0, rehearsal.article_findings[
        "findings"
    ]


def test_the_autopublish_gate_says_true(rehearsal: Rehearsal) -> None:
    assert rehearsal.autopublish == "true"


def test_the_brief_pr_validates_block_clean(rehearsal: Rehearsal) -> None:
    assert rehearsal.brief_findings["block_count"] == 0, rehearsal.brief_findings[
        "findings"
    ]


def test_night_one_renders_a_multi_article_front_page(rehearsal: Rehearsal) -> None:
    assert "nb-lead-cell" in rehearsal.front1
    assert 'class="nb-grid"' in rehearsal.front1


def test_night_one_build_lists_both_articles(rehearsal: Rehearsal) -> None:
    assert rehearsal.catalog1["builds"]["2026-07-05"] == [
        "ai-briefs/2026-07-05",
        "semiconductors/micron",
    ]


def test_night_one_feed_has_both_entries(rehearsal: Rehearsal) -> None:
    assert entry_count(rehearsal.feed1) == 2


def test_a_losing_race_for_the_same_night_is_blocked(rehearsal: Rehearsal) -> None:
    findings = rehearsal.rival_findings["findings"]
    blocked = [f["code"] for f in findings if f["level"] == "BLOCK"]

    assert "B-MODE" in blocked, findings


def test_the_night_two_brief_validates_block_clean(rehearsal: Rehearsal) -> None:
    assert rehearsal.night2_findings["block_count"] == 0, rehearsal.night2_findings[
        "findings"
    ]


def test_the_front_page_rolls_over_to_night_two(rehearsal: Rehearsal) -> None:
    assert "July 6, 2026" in rehearsal.front2
    assert "2026-07-06" in json.dumps(rehearsal.catalog2["builds"])


def test_both_nights_are_preserved_in_the_archive(rehearsal: Rehearsal) -> None:
    assert list(rehearsal.catalog2["builds"]) == ["2026-07-06", "2026-07-05"]
    assert pathlib.Path(
        rehearsal.press.sitedir, "builds", "2026-07-05", "index.html"
    ).is_file()


def test_build_pages_link_across_nights(rehearsal: Rehearsal) -> None:
    page = rehearsal.press.site_text("builds", "2026-07-06", "index.html")

    assert 'href="../2026-07-05/"' in page


def test_the_feeds_update_after_night_two(rehearsal: Rehearsal) -> None:
    assert entry_count(rehearsal.press.site_text("feed.xml")) == 3
    assert (
        entry_count(rehearsal.press.site_text("series", "ai-briefs", "feed.xml")) == 2
    )


def test_the_sections_page_counts_published_not_progress(rehearsal: Rehearsal) -> None:
    page = rehearsal.press.site_text("series", "index.html")

    assert "1 published" in page
    assert "1 of 5" not in page
