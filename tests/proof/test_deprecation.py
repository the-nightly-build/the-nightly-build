"""A retired component renders the back-catalog but never a new article.

When a component leaves the live catalog its CSS stays in the sheet so frozen
articles keep rendering, and an `@deprecated` marker beside that CSS names its
replacement. The proof reads those markers and blocks a new article that reaches
for retired markup, so a stale shape cannot be copied forward out of the
library. The proof only ever runs on the article being authored, so the block
never touches what is already published.
"""

from collections.abc import Callable

import check
from findings import Findings
from nb.proof.structure import deprecated_classes
from press import REPO, mut


def test_a_retired_component_declares_its_replacement() -> None:
    rep = check.Report()
    check.check_deprecated(
        '<body class="nb-article"><div class="nb-verdict">x</div></body>',
        repo=str(REPO),
        rep=rep,
    )
    result = Findings(rep)

    assert "B-DEPRECATED" in result.blocks
    assert deprecated_classes(str(REPO))["nb-verdict"] == "nb-note"


def test_a_retired_subpart_blocks_as_deprecated() -> None:
    rep = check.Report()
    check.check_deprecated(
        '<body class="nb-article"><p class="nb-verdict-title">x</p></body>',
        repo=str(REPO),
        rep=rep,
    )

    assert "B-DEPRECATED" in Findings(rep).blocks


def test_a_retirement_can_declare_no_replacement() -> None:
    rep = check.Report()
    check.check_deprecated(
        '<body class="nb-article"><ul class="nb-paper-map">x</ul></body>',
        repo=str(REPO),
        rep=rep,
    )
    result = Findings(rep)

    assert "B-DEPRECATED" in result.blocks
    assert deprecated_classes(str(REPO))["nb-paper-map"] is None


def test_live_components_are_not_deprecated() -> None:
    rep = check.Report()
    check.check_deprecated(
        '<body class="nb-article">'
        '<section class="nb-bookend"><p class="nb-bookend-name">x</p></section>'
        '<div class="nb-note">y</div></body>',
        repo=str(REPO),
        rep=rep,
    )

    assert "B-DEPRECATED" not in Findings(rep).codes


def test_the_full_proof_blocks_an_article_reaching_for_retired_markup(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        mut("</article>", '<div class="nb-verdict">stale shape</div></article>'),
        "semiconductors",
    )

    assert "B-DEPRECATED" in result.blocks
