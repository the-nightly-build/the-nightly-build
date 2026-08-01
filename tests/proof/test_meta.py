"""The article says what it is, and the page agrees with it.

nb-meta is the article's only self-description: the proof reads it, refuses it
when it is malformed, and then holds the rendered page to it. Chrome is the
other half of the same question — the furniture the template declares must
survive the writing of the piece.
"""

import base64
import hashlib
import pathlib
from collections.abc import Callable

import pytest

import check
from findings import Findings
from press import REPO, TODAY, article, brief, mut

RENDERED_DEK = """<p class="nb-dekline">
  How a cyclical commodity maker became the AI era&#39;s<br>
  bottleneck.
</p>"""


def test_valid_article_is_block_clean(run_local: Callable[..., Findings]) -> None:
    result = run_local(article(), "semiconductors")

    assert not result.blocks


def test_valid_article_has_zero_warns_too(run_local: Callable[..., Findings]) -> None:
    result = run_local(article(), "semiconductors")

    assert "W-LENGTH-LOW" not in result.codes
    assert "W-SOURCES-MIN" not in result.codes
    assert "W-CITE-DENSITY" not in result.codes


def test_clean_prose_does_not_trip_the_banned_terms_warn(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(article(), "semiconductors")

    assert "W-BANNED-TERM" not in result.codes


def test_em_dash_overuse_warns_and_never_blocks(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        mut(
            "<h2>Orientation</h2>",
            "<h2>Orientation</h2><p>" + "clause — " * 5 + "</p>",
        ),
        "semiconductors",
    )

    assert "W-BANNED-TERM" in result.warns
    assert not result.blocks


def test_valid_brief_is_block_clean(run_local: Callable[..., Findings]) -> None:
    result = run_local(brief(TODAY), "ai-briefs", slug=TODAY)

    assert not result.blocks


def test_collection_with_library_state_and_an_unpublished_slug_is_clean(
    run_local: Callable[..., Findings],
    make_library: Callable[[dict[str, list[str]]], str],
) -> None:
    result = run_local(
        article(),
        "semiconductors",
        library=make_library({"semiconductors": ["tsmc"]}),
    )

    assert not result.blocks


@pytest.mark.parametrize(
    "_name,html",
    [
        ("missing nb-meta block", mut('id="nb-meta"', 'id="not-meta"')),
        ("invalid json", mut('"protocol": "1.0",', '"protocol": "1.0"')),
        (
            "missing field",
            mut(
                '"dek": "How a cyclical commodity maker became the AI era\'s bottleneck.",',
                "",
            ),
        ),
        ("wrong protocol major", mut('"protocol": "1.0"', '"protocol": "2.0"')),
    ],
)
def test_unreadable_meta_blocks(
    run_local: Callable[..., Findings], *, _name: str, html: str
) -> None:
    result = run_local(html, "semiconductors")

    assert "B-META-PARSE" in result.blocks


def test_path_and_meta_slug_must_match(run_local: Callable[..., Findings]) -> None:
    result = run_local(article(), "semiconductors", slug="tsmc")

    assert "B-META-MATCH" in result.blocks


@pytest.mark.parametrize(
    "_name,html",
    [
        ("mode", mut('"mode": "collection"', '"mode": "rolling"')),
        ("template", mut('"template": "article"', '"template": "brief"')),
    ],
)
def test_meta_disagreeing_with_the_series_blocks(
    run_local: Callable[..., Findings], *, _name: str, html: str
) -> None:
    result = run_local(html, "semiconductors")

    assert "B-META-MATCH" in result.blocks


def test_wrapped_escaped_tag_broken_dekline_agreeing_with_meta_is_clean(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(article(), "semiconductors")

    assert "B-META-MATCH" not in result.codes
    assert not result.blocks


def test_meta_dek_disagreeing_with_the_rendered_dekline_blocks(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        mut(RENDERED_DEK, '<p class="nb-dekline">A better sentence, body only.</p>'),
        "semiconductors",
    )

    assert "B-META-MATCH" in result.blocks


def test_an_article_with_no_dekline_is_not_held_to_the_meta_dek(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(mut(RENDERED_DEK, ""), "semiconductors")

    assert "B-META-MATCH" not in result.codes
    assert not result.blocks


def test_slug_style_tag_is_accepted(run_local: Callable[..., Findings]) -> None:
    result = run_local(
        mut('"tags": ["equity"]', '"tags": ["equity", "memory-cycle"]'),
        "semiconductors",
    )

    assert "B-META-PARSE" not in result.codes
    assert not result.blocks


def test_nested_tag_is_accepted(run_local: Callable[..., Findings]) -> None:
    result = run_local(
        mut('"tags": ["equity"]', '"tags": ["markets/equity"]'),
        "semiconductors",
    )

    assert "B-META-PARSE" not in result.codes
    assert not result.blocks


@pytest.mark.parametrize(
    "_name,tags",
    [
        ("uppercase", '"tags": ["Equity"]'),
        ("path traversal", '"tags": ["../../../escape"]'),
        ("not a list", '"tags": "equity"'),
    ],
)
def test_tags_that_are_not_slugs_block(
    run_local: Callable[..., Findings], *, _name: str, tags: str
) -> None:
    result = run_local(mut('"tags": ["equity"]', tags), "semiconductors")

    assert "B-META-PARSE" in result.blocks


CHROME = {"chrome": ['<body class="nb-article">', "<h2>Sources</h2>"]}


def test_intact_chrome_passes() -> None:
    rep = check.Report()
    check.check_chrome(
        '<body class="nb-article"><h2>Sources</h2></body>', treg=CHROME, rep=rep
    )

    assert not Findings(rep).blocks


def test_mutated_chrome_blocks() -> None:
    rep = check.Report()
    check.check_chrome(
        '<body class="nb-page"><h2>Sources →</h2></body>', treg=CHROME, rep=rep
    )

    assert "B-CHROME" in Findings(rep).blocks


def test_a_template_declaring_no_chrome_is_not_checked() -> None:
    rep = check.Report()
    check.check_chrome("<body></body>", treg={}, rep=rep)

    assert not Findings(rep).blocks


def test_a_typod_class_warns_as_dead() -> None:
    rep = check.Report()
    check.check_classes(
        '<body class="nb-article"><p class="nb-callout">x</p>'
        '<p class="nb-callot">y</p></body>',
        repo=str(REPO),
        rep=rep,
    )

    assert "W-DEAD-CLASS" in Findings(rep).warns


def test_defined_and_builtin_classes_pass() -> None:
    rep = check.Report()
    check.check_classes(
        '<body class="nb-article"><p class="nb-callout">x</p>'
        '<code class="language-python">y</code></body>',
        repo=str(REPO),
        rep=rep,
    )
    result = Findings(rep)

    assert not result.blocks
    assert "W-DEAD-CLASS" not in result.codes


def test_sri_pinned_stylesheet_classes_join_the_inventory(
    tmp_path: pathlib.Path,
) -> None:
    raw_css = b".external-chip { color: red; }"
    digest = base64.b64encode(hashlib.sha384(raw_css).digest()).decode()
    repo = tmp_path
    (repo / "press").mkdir()
    stylesheet = repo / "theme.css"
    stylesheet.write_bytes(raw_css)
    (repo / "press" / "site.yaml").write_text(
        "assets:\n  styles:\n"
        f"    - url: {stylesheet.as_uri()}\n      integrity: sha384-{digest}\n"
    )

    external = check.Report()
    check.check_classes('<p class="external-chip">x</p>', repo=str(repo), rep=external)
    assert "W-DEAD-CLASS" not in Findings(external).codes

    unknown = check.Report()
    check.check_classes(
        '<p class="hallucinated-chip">x</p>', repo=str(repo), rep=unknown
    )
    assert "W-DEAD-CLASS" in Findings(unknown).warns


def test_incomplete_external_stylesheet_suppresses_dead_class_warning(
    tmp_path: pathlib.Path,
) -> None:
    repo = tmp_path
    (repo / "press").mkdir()
    stylesheet = repo / "theme.css"
    stylesheet.write_bytes(b".valid { }")
    (repo / "press" / "site.yaml").write_text(
        "assets:\n  styles:\n"
        f"    - url: {stylesheet.as_uri()}\n      integrity: sha384-invalid\n"
    )

    rep = check.Report()
    check.check_classes('<p class="possibly-valid">x</p>', repo=str(repo), rep=rep)

    assert "W-DEAD-CLASS" not in Findings(rep).codes
    assert rep.notes
