"""Scheduled publication across two UTC dates against a real Git press.

The press is laid out exactly like production — main carries the engine and the
config, and an orphan library branch carries what shipped. Each proposed
article branches from library, passes the same PR-mode proof that check.yml
invokes, passes the autopublish gate, is squash-merged, and then enters the site
build that publish.yml runs.

First date (2026-07-05): a collection article and a rolling brief.
Second date (2026-07-06): a rolling brief.

A real scheduled run on a fork remains a manual verification outside this
deterministic suite.
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

import pytest

import build_site
from press import REPO, article, brief, git, make_press, write_agent_artifacts

pytestmark = pytest.mark.slow

NS = "{http://www.w3.org/2005/Atom}"


class Press:
    """A real Git press whose helpers reproduce two publication dates.

    Main and library stay separate exactly as they do in production. Each
    method performs the actual Git, proof, merge, and build boundary so the
    test detects integration drift that unit fixtures cannot represent.
    """

    def __init__(self) -> None:
        self.root = make_press()
        shutil.copytree(
            REPO / "engine",
            pathlib.Path(self.root) / "engine",
            ignore=shutil.ignore_patterns("__pycache__"),
            dirs_exist_ok=True,
        )
        git("init", "-q", "-b", "main", cwd=self.root)
        git("config", "user.email", "scheduled@test.invalid", cwd=self.root)
        git("config", "user.name", "scheduled-runtime", cwd=self.root)
        git("add", "-A", cwd=self.root)
        git("commit", "-qm", "engine", cwd=self.root)
        git("checkout", "-q", "--orphan", "library", cwd=self.root)
        git("rm", "-rfq", ".", cwd=self.root)
        pathlib.Path(self.root, "library").mkdir()
        pathlib.Path(self.root, "library", ".gitkeep").write_text("")
        git("add", "-A", cwd=self.root)
        git("commit", "-qm", "library: initialize the empty press", cwd=self.root)

        # Scratch dirs live outside the worktree, so each article commit stays narrow.
        self.scratch = pathlib.Path(tempfile.mkdtemp())
        self.libdir = self.scratch / "libstate"
        self.maindir = self.scratch / "mainstate"
        self.sitedir = self.scratch / "site"
        self.libdir.mkdir()
        self.maindir.mkdir()
        self._archive("main", self.maindir)

    def _archive(self, ref: str, into: pathlib.Path) -> None:
        command = f"git archive {ref} | tar -x -C {into}"
        subprocess.run(
            command,
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
        command = ["git", "rev-parse", ref]
        completed = subprocess.run(
            command, cwd=self.root, capture_output=True, text=True
        )
        return completed.stdout.strip()

    def propose_article(
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
        write_agent_artifacts(self.root, series, slug=slug)
        git("add", "-A", cwd=self.root)
        git("commit", "-qm", f"nb: {series}/{slug}", cwd=self.root)

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
            "--today",
            today,
            "--no-check-links",  # This integration test is offline and deterministic.
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
        page = pathlib.Path(self.sitedir, *parts)
        return page.read_text()


@dataclasses.dataclass(frozen=True)
class PublicationScenario:
    press: Press
    article_findings: dict
    autopublish: str
    brief_findings: dict
    first_catalog: dict
    first_front: str
    first_feed: str
    rival_findings: dict
    second_findings: dict
    second_catalog: dict
    second_front: str


@pytest.fixture(scope="module")
def publication() -> PublicationScenario:
    press = Press()

    article_findings, autopublish = press.propose_article(
        "nb/first-micron",
        "semiconductors",
        slug="micron",
        html=article().replace("2026-07-06", "2026-07-05"),
        today="2026-07-05",
    )
    press.merge("nb/first-micron")

    # the base a competing agent would have branched from, before the brief merged
    pre_merge_ref = press.rev("library")
    brief_findings, _ = press.propose_article(
        "nb/first-brief",
        "ai-briefs",
        slug="2026-07-05",
        html=brief("2026-07-05"),
        today="2026-07-05",
    )
    press.merge("nb/first-brief")

    first_catalog = press.publish("2026-07-05T09:00:00+00:00")
    first_front = press.site_text("index.html")
    first_feed = press.site_text("feed.xml")

    # a competing agent raced the same slug from the pre-merge base, and lost
    rival_findings, _ = press.propose_article(
        "nb/first-duplicate",
        "ai-briefs",
        slug="2026-07-05",
        html=brief("2026-07-05").replace(
            "Daily brief for 2026-07-05", "Rival brief for 2026-07-05"
        ),
        today="2026-07-05",
        from_ref=pre_merge_ref,
    )
    git("checkout", "-q", "library", cwd=press.root)

    second_findings, _ = press.propose_article(
        "nb/second-brief",
        "ai-briefs",
        slug="2026-07-06",
        html=brief("2026-07-06"),
        today="2026-07-06",
    )
    press.merge("nb/second-brief")

    second_catalog = press.publish("2026-07-06T09:00:00+00:00")

    return PublicationScenario(
        press=press,
        article_findings=article_findings,
        autopublish=autopublish,
        brief_findings=brief_findings,
        first_catalog=first_catalog,
        first_front=first_front,
        first_feed=first_feed,
        rival_findings=rival_findings,
        second_findings=second_findings,
        second_catalog=second_catalog,
        second_front=press.site_text("index.html"),
    )


def entry_count(feed_xml: str) -> int:
    feed = ET.fromstring(feed_xml)
    return len(feed.findall(f"{NS}entry"))


def test_the_article_pr_validates_block_clean(publication: PublicationScenario) -> None:
    assert publication.article_findings["block_count"] == 0, (
        publication.article_findings["findings"]
    )


def test_the_autopublish_gate_says_true(publication: PublicationScenario) -> None:
    assert publication.autopublish == "true"


def test_the_brief_pr_validates_block_clean(publication: PublicationScenario) -> None:
    assert publication.brief_findings["block_count"] == 0, publication.brief_findings[
        "findings"
    ]


def test_first_date_renders_a_multi_article_front_page(
    publication: PublicationScenario,
) -> None:
    assert "nb-lead-cell" in publication.first_front
    assert 'class="nb-grid"' in publication.first_front


def test_first_date_build_lists_both_articles(publication: PublicationScenario) -> None:
    assert publication.first_catalog["builds"]["2026-07-05"] == [
        "ai-briefs/2026-07-05",
        "semiconductors/micron",
    ]


def test_first_date_feed_has_both_entries(publication: PublicationScenario) -> None:
    assert entry_count(publication.first_feed) == 2


def test_a_losing_race_for_the_same_article_is_blocked(
    publication: PublicationScenario,
) -> None:
    findings = publication.rival_findings["findings"]
    blocked = [f["code"] for f in findings if f["level"] == "BLOCK"]

    assert "B-MODE" in blocked, findings


def test_the_second_date_brief_validates_block_clean(
    publication: PublicationScenario,
) -> None:
    assert publication.second_findings["block_count"] == 0, publication.second_findings[
        "findings"
    ]


def test_the_front_page_rolls_over_to_the_second_date(
    publication: PublicationScenario,
) -> None:
    assert "July 6, 2026" in publication.second_front
    assert "2026-07-06" in json.dumps(publication.second_catalog["builds"])


def test_both_dates_are_preserved_in_the_archive(
    publication: PublicationScenario,
) -> None:
    assert list(publication.second_catalog["builds"]) == ["2026-07-06", "2026-07-05"]
    assert pathlib.Path(
        publication.press.sitedir, "builds", "2026-07-05", "index.html"
    ).is_file()


def test_build_pages_link_across_dates(publication: PublicationScenario) -> None:
    page = publication.press.site_text("builds", "2026-07-06", "index.html")

    assert 'href="../2026-07-05/"' in page


def test_the_feeds_update_after_the_second_date(
    publication: PublicationScenario,
) -> None:
    assert entry_count(publication.press.site_text("feed.xml")) == 3
    assert (
        entry_count(publication.press.site_text("series", "ai-briefs", "feed.xml")) == 2
    )


def test_the_sections_page_counts_published_not_progress(
    publication: PublicationScenario,
) -> None:
    page = publication.press.site_text("series", "index.html")

    assert "1 published" in page
    assert "1 of 5" not in page
