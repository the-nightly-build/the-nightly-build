"""The proof as CI runs it: a PR body, and the diff a night shift actually pushed."""

import pathlib
from collections.abc import Callable

import pytest
from conftest import PR_BODY, PressRepo
from findings import Findings
from press import article

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

# The canonical body carries the production record PROTOCOL step 8 defines: every
# artifact the chain produced, including a voice brief that studied real writers.
STUDIED_VOICE = (
    "## Voice brief\n"
    "<details><summary>brief</summary>\n\n````markdown\n"
    '## Jane Reporter, "The Cycle That Ate Memory"\n'
    "Source: https://example.org/exemplar-1\n"
    "Craft: leads on the number, spends the second line on the caveat.\n\n"
    '## Sam Analyst, "What Fabs Cost"\n'
    "Source: https://example.org/exemplar-2\n"
    "Craft: every claim carries its denominator.\n\n"
    '## Lee Critic, "The Capex Mirage"\n'
    "Source: https://example.org/exemplar-3\n"
    "Craft: names the mechanism, never the adjective.\n"
    "````\n\n</details>\n\n"
)

GOOD_BODY = (
    MINIMAL_BODY + "\n## Task\n"
    "Commission: what Micron's cycle costs, for a public-market reader.\n\n"
    "## Process\n"
    "Coach studied three exemplars; one edit round, surgical fixes only.\n\n"
    + STUDIED_VOICE
    + "## Research\n"
    "Nine sources read; every number checked against the filing.\n\n"
    "## Also consulted\n"
    "- https://example.org/background — context only, superseded by the filing\n"
)

# The 2026-07-14 forgery: an orchestrator skipped the coach and wrote the brief
# itself. Six lines, two mastheads named, no writers, no sources, and it passed.
FORGED_VOICE_BODY = GOOD_BODY.replace(
    STUDIED_VOICE,
    "## Voice brief\n"
    "<details><summary>brief</summary>\n\n````markdown\n"
    "The best daily writers (Economist Espresso, FT's #techFT) lead with the\n"
    "number, then spend the second sentence on the caveat. No hype.\n"
    "````\n\n</details>\n\n",
)


def test_preflight_passes_when_the_body_matches_the_article(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(article(), "semiconductors", pr_body=GOOD_BODY)

    assert not result.blocks
    assert "B-META-MATCH" not in result.codes
    assert "W-BODY-RECORD" not in result.codes


def test_preflight_warns_when_the_record_sections_are_missing(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(article(), "semiconductors", pr_body=MINIMAL_BODY)

    assert "W-BODY-RECORD" in result.warns
    assert not result.blocks


def test_a_voice_brief_naming_outlets_instead_of_writers_is_unstudied(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(article(), "semiconductors", pr_body=FORGED_VOICE_BODY)

    assert "W-VOICE-THIN" in result.warns
    assert "W-BODY-RECORD" not in result.codes
    assert not result.blocks


def test_a_brief_citing_three_studied_writers_passes(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(article(), "semiconductors", pr_body=GOOD_BODY)

    assert "W-VOICE-THIN" not in result.codes


def test_a_fenced_task_heading_does_not_hide_the_real_voice_brief(
    run_local: Callable[..., Findings],
) -> None:
    body = GOOD_BODY.replace(
        "Commission: what Micron's cycle costs, for a public-market reader.",
        "````text\n## Voice brief\n````\n\n"
        "Commission: what Micron's cycle costs, for a public-market reader.",
    )

    result = run_local(article(), "semiconductors", pr_body=body)

    assert "W-VOICE-THIN" not in result.codes


def test_the_commission_and_the_research_log_are_part_of_the_record(
    run_local: Callable[..., Findings],
) -> None:
    without_task_or_research = GOOD_BODY.replace("## Task\n", "## Notes\n").replace(
        "## Research\n", "## Notes\n"
    )
    result = run_local(article(), "semiconductors", pr_body=without_task_or_research)

    assert "W-BODY-RECORD" in result.warns


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("just a description, no metadata", id="no-nb-meta-block"),
        pytest.param(
            GOOD_BODY.replace("Micron Technology", "TSMC"), id="disagrees-with-article"
        ),
    ],
)
def test_preflight_catches_a_body_the_article_does_not_answer_to(
    run_local: Callable[..., Findings], body: str
) -> None:
    result = run_local(article(), "semiconductors", pr_body=body)

    assert "B-META-MATCH" in result.blocks


def test_pr_happy_path(pr_repo: PressRepo) -> None:
    result = pr_repo.run_pr(pr_body=pr_repo.body)

    assert not result.blocks


@pytest.mark.parametrize(
    "body_text",
    [
        pytest.param(
            PR_BODY.replace("slug: micron", "slug: tsmc"), id="disagrees-with-file"
        ),
        pytest.param("no metadata block here", id="missing-nb-meta-block"),
    ],
)
def test_pr_body_the_diff_does_not_answer_to(
    pr_repo: PressRepo, body_text: str
) -> None:
    result = pr_repo.run_pr(pr_body=pr_repo.body_file(body_text))

    assert "B-META-MATCH" in result.blocks


def test_pr_touching_two_files(pr_repo: PressRepo) -> None:
    pr_repo.write("library/semiconductors/extra.txt", "x")
    pr_repo.commit("extra")

    result = pr_repo.run_pr(pr_body=pr_repo.body)

    assert "B-DIFF-SHAPE" in result.blocks


def test_pr_accepts_matching_figure_assets(pr_repo: PressRepo) -> None:
    pr_repo.write("library/semiconductors/micron/figure-1.png", "image")
    pr_repo.commit("figure asset")

    result = pr_repo.run_pr(pr_body=pr_repo.body)

    assert "B-DIFF-SHAPE" not in result.codes


def test_pr_rejects_another_articles_figure_asset(pr_repo: PressRepo) -> None:
    pr_repo.write("library/semiconductors/tsmc/figure-1.png", "image")
    pr_repo.commit("wrong figure asset")

    result = pr_repo.run_pr(pr_body=pr_repo.body)

    assert "B-DIFF-SHAPE" in result.blocks


def test_pr_modifying_engine_code(pr_repo: PressRepo) -> None:
    check_py = pathlib.Path(pr_repo.path, "engine", "check.py")
    pr_repo.write("engine/check.py", check_py.read_text() + "\n# sneak\n")
    pr_repo.commit("sneak")

    result = pr_repo.run_pr(pr_body=pr_repo.body)

    assert "B-DIFF-SHAPE" in result.blocks


def retract_on_a_curation_branch(pr_repo: PressRepo) -> None:
    """The owner publishes a second article, then retracts it on their own branch."""
    pr_repo.checkout("library")
    pr_repo.write("library/semiconductors/tsmc.html", article())
    pr_repo.commit("published")
    pr_repo.checkout("owner/curation", new=True)
    pr_repo.git("rm", "-q", "library/semiconductors/tsmc.html")
    pr_repo.git("commit", "-qm", "retract")


def test_deletion_only_pr_without_the_owner_flag(pr_repo: PressRepo) -> None:
    retract_on_a_curation_branch(pr_repo)

    result = pr_repo.run_pr(head="owner/curation", deletions_by_owner=False)

    assert "B-DIFF-SHAPE" in result.blocks


def test_owner_curation_deletion_only_pr(pr_repo: PressRepo) -> None:
    retract_on_a_curation_branch(pr_repo)

    result = pr_repo.run_pr(head="owner/curation", deletions_by_owner=True)

    assert not result.blocks


def test_owner_curation_deleting_engine_files(pr_repo: PressRepo) -> None:
    retract_on_a_curation_branch(pr_repo)
    pr_repo.git("rm", "-q", "engine/duty.py")
    pr_repo.git("commit", "-qm", "stray deletion")

    result = pr_repo.run_pr(head="owner/curation", deletions_by_owner=True)

    assert "B-DIFF-SHAPE" in result.blocks
