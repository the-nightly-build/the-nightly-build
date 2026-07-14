"""The fixtures work: a valid article passes, a broken one blocks at the right tier."""

from collections.abc import Callable

import check
from findings import Findings, findings_of
from press import TODAY, article, brief, mut


def test_valid_article_is_block_clean(run_local: Callable[..., Findings]) -> None:
    result = run_local(article(), "semiconductors")

    assert not result.blocks
    assert not result.warns


def test_valid_brief_is_block_clean(run_local: Callable[..., Findings]) -> None:
    result = run_local(brief(TODAY), "ai-briefs", slug=TODAY)

    assert not result.blocks


def test_a_dangling_citation_blocks(run_local: Callable[..., Findings]) -> None:
    result = run_local(
        mut('<a href="#s5">5</a>', '<a href="#s99">99</a>'), "semiconductors"
    )

    assert "B-CITES-RESOLVE" in result.blocks


def test_an_overcounted_source_list_warns_without_blocking(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(mut('"sources": 8', '"sources": 20'), "semiconductors")

    assert "W-SELF-COUNT" in result.warns
    assert not result.blocks


def test_a_report_filled_by_hand_reads_the_same(
    run_local: Callable[..., Findings],
) -> None:
    rep = check.Report()
    check.check_chrome(
        '<body class="nb-edition"></body>',
        treg={"chrome": ['<body class="nb-article">']},
        rep=rep,
    )

    assert "B-CHROME" in findings_of(rep).blocks


def test_the_press_is_a_real_git_repo(pr_repo) -> None:
    result = pr_repo.run_pr(pr_body=pr_repo.body)

    assert not result.blocks
