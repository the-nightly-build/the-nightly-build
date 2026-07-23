"""This module tests the proof's prose findings.

The fixtures deliberately alter real repository-backed articles and series
configurations, because prose findings depend on both the rendered structure
and the policy selected by the series. This keeps the tests focused on the
author-facing warning and strict-mode contracts rather than private helpers.

A warn is advice; a block is a refusal. Which one a finding lands at is the
thing under test here — a series with `strict: true` turns every warn into a
block, and three of the daily desks run that way.
"""

import pathlib
import re
from collections.abc import Callable

import pytest

from findings import Findings
from press import LOREM, TODAY, article, brief, mut

HEADING = "<h2>Orientation</h2>"
DENSE_SENTENCE = (
    "Kaplan and colleagues had measured how a transformer's loss falls as three "
    "things grow, model size, data, and compute, and drawn a conclusion that "
    "decided how the largest models of the era were built: bigger models learn "
    "more from each token, so a fixed compute budget is best spent on a very "
    "large model fed a comparatively modest amount of data, stopped well before "
    "it has squeezed the data dry."
)
CITE_RE = re.compile(r'<sup class="nb-cite">.*?</sup>')
DEBATE_RE = re.compile(
    r'(<section data-nb-section="bull-versus-bear">.*?</section>)', re.S
)


def _short_article() -> str:
    short = article()
    for _ in range(9):
        short = short.replace(LOREM, "Short. ", 20)
    return short


def _thin_sources() -> str:
    return (
        article()
        .replace(
            '<a data-nb-source href="https://example.org/src7">link</a>',
            '<a href="https://example.org/src7">link</a>',
        )
        .replace(
            '<a data-nb-source href="https://example.org/src8">link</a>',
            '<a href="https://example.org/src8">link</a>',
        )
        .replace('<sup class="nb-cite"><a href="#s7">7</a></sup>', "")
        .replace('<sup class="nb-cite"><a href="#s8">8</a></sup>', "")
    )


def _uncited_debate() -> str:
    base = article()
    debate = DEBATE_RE.search(base)
    assert debate is not None
    return base.replace(debate.group(1), CITE_RE.sub("", debate.group(1)))


def _thin_brief() -> str:
    return (
        re.sub(r"<div data-nb-item>.*?</div>", "", brief(), count=2, flags=re.S)
        .replace('<sup class="nb-cite"><a href="#s1">1</a></sup>', "")
        .replace('<sup class="nb-cite"><a href="#s2">2</a></sup>', "")
    )


@pytest.fixture
def reqdoc_repo(clone_testrepo: Callable[..., str]) -> str:
    repo = clone_testrepo("press", "templates")
    y = pathlib.Path(repo) / "press" / "series" / "semiconductors" / "series.yaml"
    y.write_text(
        y.read_text().replace(
            'prompt: "Emphasize the HBM supply-agreement structure and the memory-cycle debate."',
            'prompt: "Emphasize HBM."\n    required_docs:\n'
            "      - id: mu-10k-2025\n        path: sources/mu-10k-2025.txt",
        )
    )
    return repo


def test_thin_prose_warns_on_length(run_local: Callable[..., Findings]) -> None:
    result = run_local(_short_article(), "semiconductors")
    assert "W-LENGTH-LOW" in result.warns
    assert not result.blocks


def test_too_few_sources_warns(run_local: Callable[..., Findings]) -> None:
    result = run_local(_thin_sources(), "semiconductors")
    assert "W-SOURCES-MIN" in result.warns
    assert not result.blocks


def test_uncited_section_warns_on_cite_density(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(_uncited_debate(), "semiconductors")
    assert "W-CITE-DENSITY" in result.warns
    assert not result.blocks


def test_dense_sentence_warns_but_does_not_block(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        mut(HEADING, f"{HEADING}<p>{DENSE_SENTENCE}</p>"),
        "semiconductors",
    )
    assert "W-SENTENCE-DENSITY" in result.warns
    assert any(
        finding.suggestion == "consider splitting it into multiple sentences"
        for finding in result.report.findings
        if finding.code == "W-SENTENCE-DENSITY"
    )
    assert not result.blocks


def test_dense_sentence_stays_a_warning_in_a_strict_series(
    run_local: Callable[..., Findings], clone_testrepo: Callable[..., str]
) -> None:
    repo = clone_testrepo("press", "templates")
    y = pathlib.Path(repo) / "press" / "series" / "semiconductors" / "series.yaml"
    y.write_text(y.read_text().replace("strict: false", "strict: true"))
    result = run_local(
        mut(HEADING, f"{HEADING}<p>{DENSE_SENTENCE}</p>"),
        "semiconductors",
        repo=repo,
    )
    assert "W-SENTENCE-DENSITY" in result.warns
    assert "W-SENTENCE-DENSITY" not in result.blocks


def test_split_sentences_stay_clean(
    run_local: Callable[..., Findings],
) -> None:
    split = (
        "Kaplan and colleagues measured how a transformer's loss falls as three "
        "things grow: model size, data, and compute. They drew a conclusion that "
        "decided how the largest models of the era were built. Bigger models learn "
        "more from each token. Under a fixed compute budget, the best strategy was "
        "to train a very large model on comparatively little data, stopping before "
        "it had squeezed that data dry."
    )
    result = run_local(mut(HEADING, f"{HEADING}<p>{split}</p>"), "semiconductors")
    assert "W-SENTENCE-DENSITY" not in result.codes


@pytest.mark.parametrize(
    "wrapped",
    [
        "<blockquote><p>{}</p></blockquote>",
        "<q>{}</q>",
        "<pre><code>{}</code></pre>",
    ],
)
def test_code_and_quoted_text_do_not_trigger_sentence_density(
    run_local: Callable[..., Findings], wrapped: str
) -> None:
    result = run_local(
        mut(HEADING, f"{HEADING}{wrapped.format(DENSE_SENTENCE)}"),
        "semiconductors",
    )
    assert "W-SENTENCE-DENSITY" not in result.codes


def test_uncited_brief_item_warns_on_cite_density(
    run_local: Callable[..., Findings],
) -> None:
    thin = brief().replace('<sup class="nb-cite"><a href="#s2">2</a></sup>', "", 1)
    result = run_local(thin, "ai-briefs", slug=TODAY)
    assert "W-CITE-DENSITY" in result.warns
    assert not result.blocks


def test_brief_with_too_few_items_warns_on_length(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(_thin_brief(), "ai-briefs", slug=TODAY)
    assert "W-LENGTH-LOW" in result.warns
    assert not result.blocks


def test_series_item_band_replaces_the_template_band(
    run_local: Callable[..., Findings], clone_testrepo: Callable[..., str]
) -> None:
    repo = clone_testrepo("press", "templates")
    y = pathlib.Path(repo) / "press" / "series" / "ai-briefs" / "series.yaml"
    y.write_text(y.read_text() + "bands:\n  items: [2, 4]\n")
    result = run_local(_thin_brief(), "ai-briefs", slug=TODAY, repo=repo)
    assert "W-LENGTH-LOW" not in result.codes
    assert not result.blocks


def test_open_series_item_band_applies_after_template_selection(
    run_local: Callable[..., Findings], clone_testrepo: Callable[..., str]
) -> None:
    repo = clone_testrepo("press", "templates")
    series = pathlib.Path(repo) / "press" / "series" / "wildcard"
    series.mkdir()
    (series / "series.yaml").write_text(
        "name: Wildcard\nmode: open\ntemplate: brief\nbands:\n  items: [2, 3]\n"
    )
    html = _thin_brief().replace('"series": "ai-briefs"', '"series": "wildcard"')
    html = html.replace('"mode": "rolling"', '"mode": "open"')
    html = html.replace('"slug": "2026-07-06"', '"slug": "preview"')
    result = run_local(html, "wildcard", slug="preview", repo=repo)
    assert "W-LENGTH-LOW" not in result.codes
    assert not result.blocks


def test_required_doc_satisfied_when_attribute_present(
    run_local: Callable[..., Findings], reqdoc_repo: str
) -> None:
    result = run_local(article(), "semiconductors", repo=reqdoc_repo)
    assert "W-REQ-DOC" not in result.codes
    assert not result.blocks


def test_missing_required_doc_warns(
    run_local: Callable[..., Findings], reqdoc_repo: str
) -> None:
    result = run_local(
        mut(' data-nb-required="mu-10k-2025"', ""),
        "semiconductors",
        repo=reqdoc_repo,
    )
    assert "W-REQ-DOC" in result.warns
    assert not result.blocks


def test_consult_prefix_without_a_citation_is_fine(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        mut("https://www.sec.gov/filings/mu-10k", "https://example.org/not-sec"),
        "semiconductors",
    )
    assert "B-SOURCES-EXCLUSIVE" not in result.codes
    assert not result.blocks


def test_overstated_source_count_warns(run_local: Callable[..., Findings]) -> None:
    result = run_local(mut('"sources": 8', '"sources": 20'), "semiconductors")
    assert "W-SELF-COUNT" in result.warns
    assert not result.blocks


def test_strict_promotes_warn_to_block(
    run_local: Callable[..., Findings], clone_testrepo: Callable[..., str]
) -> None:
    repo = clone_testrepo("press", "templates")
    y = pathlib.Path(repo) / "press" / "series" / "semiconductors" / "series.yaml"
    y.write_text(y.read_text().replace("strict: false", "strict: true"))
    result = run_local(
        mut('"sources": 8', '"sources": 20'), "semiconductors", repo=repo
    )
    assert "W-SELF-COUNT" in result.blocks
    assert not result.warns


@pytest.fixture
def banned_repo(clone_testrepo: Callable[..., str]) -> Callable[..., str]:
    def repo(press_yaml: str | None = None) -> str:
        tmp = clone_testrepo("press", "templates", "spec", "engine")
        if press_yaml is not None:
            (pathlib.Path(tmp) / "press" / "banned-terms.yaml").write_text(press_yaml)
        return tmp

    return repo


def test_banned_term_is_counted_in_headings(run_local: Callable[..., Findings]) -> None:
    result = run_local(mut(HEADING, "<h2>Leverage on leverage</h2>"), "semiconductors")
    assert "W-BANNED-TERM" in result.warns
    assert not result.blocks


def test_use_within_the_limit_passes(run_local: Callable[..., Findings]) -> None:
    result = run_local(mut(HEADING, "<h2>Leverage economics</h2>"), "semiconductors")
    assert "W-BANNED-TERM" not in result.codes


def test_zero_limit_term_trips_on_first_use(run_local: Callable[..., Findings]) -> None:
    result = run_local(mut(HEADING, "<h2>The load bearing wall</h2>"), "semiconductors")
    assert "W-BANNED-TERM" in result.warns


def test_press_override_raises_an_engine_limit(
    run_local: Callable[..., Findings], banned_repo: Callable[..., str]
) -> None:
    result = run_local(
        mut(HEADING, "<h2>Leverage on leverage</h2>"),
        "semiconductors",
        repo=banned_repo("- id: leverage\n  max: 5\n"),
    )
    assert "W-BANNED-TERM" not in result.codes


def test_press_disables_an_engine_entry(
    run_local: Callable[..., Findings], banned_repo: Callable[..., str]
) -> None:
    result = run_local(
        mut(HEADING, "<h2>The load bearing wall</h2>"),
        "semiconductors",
        repo=banned_repo("- id: load-bearing\n  enabled: false\n"),
    )
    assert "W-BANNED-TERM" not in result.codes


def test_press_adds_its_own_ban(
    run_local: Callable[..., Findings], banned_repo: Callable[..., str]
) -> None:
    result = run_local(
        mut(HEADING, "<h2>Synergy in memory</h2>"),
        "semiconductors",
        repo=banned_repo(
            "- id: synergy\n  terms: [synergy]\n  max: 0\n"
            "  suggestion: name the mechanism\n"
        ),
    )
    assert "W-BANNED-TERM" in result.warns


@pytest.mark.parametrize(
    ("name", "press_yaml", "returncode"),
    [
        ("partial override", "- id: em-dash\n  max: 8\n", 0),
        (
            "new ban missing its suggestion",
            "- id: synergy\n  terms: [synergy]\n  max: 0\n",
            1,
        ),
        ("unknown key", "- id: em-dash\n  maximum: 8\n", 1),
        (
            "negative max",
            "- id: synergy\n  terms: [synergy]\n  max: -1\n  suggestion: s\n",
            1,
        ),
        ("duplicate id", "- id: em-dash\n  max: 8\n- id: em-dash\n  max: 9\n", 1),
    ],
)
def test_validate_config_judges_a_banned_terms_override(
    vc_rc: Callable[[str], int],
    banned_repo: Callable[..., str],
    name: str,
    press_yaml: str,
    returncode: int,
) -> None:
    assert vc_rc(banned_repo(press_yaml)) == returncode, name


def test_clean_article_carries_no_placeholder_warn(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(article(), "semiconductors")
    assert "W-PLACEHOLDER" not in result.codes


def test_lifted_skeleton_placeholder_warns_and_never_blocks(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        mut(
            HEADING,
            f"{HEADING}<p>OPENING PARAGRAPH WITH A CONCRETE, CITED ANCHOR CLAIM.</p>",
        ),
        "semiconductors",
    )
    assert "W-PLACEHOLDER" in result.warns
    assert not result.blocks


@pytest.mark.parametrize(
    ("name", "paragraph"),
    [
        ("a long caps run, off-skeleton", "REPLACE THIS ENTIRE SENTENCE TONIGHT."),
        ("a lone skeleton placeholder word", "TITLE goes here."),
    ],
)
def test_caps_runs_are_read_as_leftovers(
    run_local: Callable[..., Findings], name: str, paragraph: str
) -> None:
    result = run_local(mut(HEADING, f"{HEADING}<p>{paragraph}</p>"), "semiconductors")
    assert "W-PLACEHOLDER" in result.warns, name


def test_acronym_runs_shorter_than_the_generic_bar_stay_clean(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        mut(HEADING, f"{HEADING}<p>Pricing spans HBM DRAM NAND lines.</p>"),
        "semiconductors",
    )
    assert "W-PLACEHOLDER" not in result.codes
