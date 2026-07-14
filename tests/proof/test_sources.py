"""Sources: their form, the citations that reach them, and the mix they make.

A source list is the load-bearing part of an article, so the proof asks three
questions of it. Is each entry a link the reader can follow (B-SOURCES-FORM,
B-CITES-RESOLVE)? Does the series allow the source at all (B-SOURCES-EXCLUSIVE)?
And is the composition the one the series asked for (B-SOURCE-KIND)? The kind
findings BLOCK regardless of `strict`, because sourcing is not calibration —
every assertion here says so.
"""

import pathlib
from collections.abc import Callable

import check
import pytest
from findings import Findings
from press import TODAY, article, mut

ARXIV = "https://arxiv.org/abs/2601.00001"
CONFORMING_ITEM = [(ARXIV, "primary"), ("https://reuters.com/a", "secondary")]

ALL_PRIMARY = article().replace(
    "<a data-nb-source", '<a data-nb-source data-nb-kind="primary"'
)
MIXED = ALL_PRIMARY.replace(
    'data-nb-kind="primary" href="https://example.org/src7"',
    'data-nb-kind="secondary" href="https://example.org/src7"',
).replace(
    'data-nb-kind="primary" href="https://example.org/src8"',
    'data-nb-kind="secondary" href="https://example.org/src8"',
)
# A floor met by an entry no line cites is not met: the mix is what the article
# rests on, not what its list advertises.
LISTED_NOT_CITED = MIXED.replace(
    "</ol>",
    '<li id="s9"><a data-nb-source data-nb-kind="secondary" '
    'href="https://apnews.com/x">src</a></li></ol>',
    1,
)
PER_ITEM_PATCH = "per_item_sources:\n  primary: [1, 1]\n  secondary: [1, 2]\n"
BY_KIND_PATCH = "sources_by_kind:\n  primary: [4, null]\n  secondary: [2, null]\n"


# --------------------------------------------------------------------------- #
# B-SOURCES-FORM / B-CITES-RESOLVE
# --------------------------------------------------------------------------- #


def test_an_article_with_no_sources_at_all_blocks(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        article().replace("data-nb-source", "data-nb-src"), "semiconductors"
    )

    assert "B-SOURCES-FORM" in result.blocks


@pytest.mark.parametrize(
    ("name", "old", "new"),
    [
        (
            "http rather than https",
            'href="https://example.org/src4"',
            'href="http://example.org/src4"',
        ),
        (
            "a local file on a source that was never declared required",
            'href="https://example.org/src4"',
            'href="sources/local.txt"',
        ),
        (
            "an off-origin path, even on a required source",
            'href="https://example.org/src1"',
            'href="//evil.example/x.txt"',
        ),
    ],
)
def test_a_source_link_that_is_not_absolute_https_blocks(
    run_local: Callable[..., Findings], name: str, old: str, new: str
) -> None:
    result = run_local(mut(old, new), "semiconductors")

    assert "B-SOURCES-FORM" in result.blocks


def test_a_required_source_may_cite_a_repo_relative_local_file(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        mut('href="https://example.org/src1"', 'href="sources/mu-10k-2025.txt"'),
        "semiconductors",
    )

    assert "B-SOURCES-FORM" not in result.codes
    assert not result.blocks


@pytest.mark.parametrize(
    ("name", "new"),
    [
        ("a source number that does not exist", '<a href="#s99">99</a>'),
        ("an id that is not a source", '<a href="#nb-meta">5</a>'),
    ],
)
def test_a_citation_that_does_not_reach_a_source_blocks(
    run_local: Callable[..., Findings], name: str, new: str
) -> None:
    result = run_local(mut('<a href="#s5">5</a>', new), "semiconductors")

    assert "B-CITES-RESOLVE" in result.blocks


# --------------------------------------------------------------------------- #
# sources_exclusive
# --------------------------------------------------------------------------- #


def series_yaml(repo: str, series: str = "semiconductors") -> pathlib.Path:
    return pathlib.Path(repo) / "press" / "series" / series / "series.yaml"


@pytest.fixture
def exclusive_repo(clone_testrepo: Callable[..., str]) -> str:
    """A press whose semiconductors series may cite only sec.gov and example.org."""
    tmp = clone_testrepo("press", "templates")
    y = series_yaml(tmp)
    y.write_text(
        y.read_text().replace(
            "consult:\n  - https://www.sec.gov/",
            "sources_exclusive: true\nconsult:\n  - https://www.sec.gov/\n"
            "  - https://example.org/",
        )
    )
    return tmp


def test_exclusive_all_sources_in_the_declared_set(
    run_local: Callable[..., Findings], exclusive_repo: str
) -> None:
    result = run_local(article(), "semiconductors", repo=exclusive_repo)

    assert "B-SOURCES-EXCLUSIVE" not in result.codes
    assert not result.blocks


def test_exclusive_an_outside_source_blocks(
    run_local: Callable[..., Findings], exclusive_repo: str
) -> None:
    result = run_local(
        mut('href="https://example.org/src4"', 'href="https://other.example/x"'),
        "semiconductors",
        repo=exclusive_repo,
    )

    assert "B-SOURCES-EXCLUSIVE" in result.blocks


def test_exclusive_declared_required_doc_entries_are_exempt(
    run_local: Callable[..., Findings], exclusive_repo: str
) -> None:
    y = series_yaml(exclusive_repo)
    y.write_text(
        y.read_text()
        .replace("  - https://example.org/\n", "")
        .replace(
            'prompt: "Emphasize the HBM supply-agreement structure and the memory-cycle debate."',
            "required_docs:\n      - id: mu-10k-2025\n        path: sources/mu-10k-2025.txt",
        )
    )

    result = run_local(article(), "semiconductors", repo=exclusive_repo)

    # 8 sources: s1 exempt (declared doc), s2 exempt (sec.gov consult) — the
    # remaining 6 example.org sources violate. 6 blocks proves both exemptions.
    assert "B-SOURCES-EXCLUSIVE" in result.blocks
    assert "W-REQ-DOC" not in result.codes
    assert len(result.blocks) == 6


# --------------------------------------------------------------------------- #
# source kinds (B-SOURCE-KIND: composition, not count)
# --------------------------------------------------------------------------- #
# min_sources counts and cannot see composition: a brief whose every item came
# off one arXiv listing clears any floor. A series declares the mix it wants
# instead. Whether a declared kind is honest is the editor's read, not a count.


def kinded_brief(items: list[list[tuple[str, str]]]) -> str:
    """A brief whose items cite the (href, kind) sources named, in first-cite order."""
    numbered: dict[str, tuple[int, str]] = {}
    for item in items:
        for href, kind in item:
            numbered.setdefault(href, (len(numbered) + 1, kind))
    body = "".join(
        f'<div data-nb-item><span class="tag">topic{i}</span>'
        f"<h4>Development number {i} happened today"
        + "".join(
            f'<sup class="nb-cite"><a href="#s{numbered[href][0]}">'
            f"{numbered[href][0]}</a></sup>"
            for href, _ in item
        )
        + "</h4><p>What happened, and the immediate context around it.</p></div>"
        for i, item in enumerate(items, 1)
    )
    src = "".join(
        f'<li id="s{n}"><a data-nb-source data-nb-kind="{kind}" href="{href}">src</a></li>'
        for href, (n, kind) in sorted(numbered.items(), key=lambda kv: kv[1][0])
    )
    meta = f"""{{
  "protocol": "1.0", "series": "ai-briefs", "slug": "{TODAY}",
  "template": "brief", "title": "Daily brief for {TODAY}",
  "mode": "rolling", "order": null, "date": "{TODAY}", "tags": [],
  "sources": {len(numbered)}, "words": 300, "reading_minutes": 5,
  "dek": "Five items, each cited to the document that owns it.",
  "harness": "test-fixture", "model": "claude-fable-5"
}}"""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Brief {TODAY}</title>
<script type="application/json" id="nb-meta">
{meta}
</script>
</head><body class="nb-article">
<section data-nb-section="items">{body}</section>
<section data-nb-section="sources"><h2>Sources</h2><ol>{src}</ol></section>
</body></html>"""


def brief_with(first_item: list[tuple[str, str]]) -> str:
    """The conforming brief, with its first item's sources swapped out."""
    return kinded_brief(
        [
            first_item,
            [
                ("https://www.sec.gov/filings/x", "primary"),
                ("https://ft.com/b", "secondary"),
            ],
            [
                ("https://curia.europa.eu/r", "primary"),
                ("https://apnews.com/c", "secondary"),
            ],
            [
                ("https://www.federalregister.gov/d", "primary"),
                ("https://wsj.com/e", "secondary"),
            ],
        ]
    )


@pytest.fixture
def per_item_briefs(patched_repo: Callable[..., str]) -> str:
    """The brief series, asking every item for one primary and up to two reads."""
    return patched_repo(PER_ITEM_PATCH, series="ai-briefs")


@pytest.fixture
def by_kind_semis(patched_repo: Callable[..., str]) -> str:
    """The article series, asking the piece as a whole for a mix."""
    return patched_repo(BY_KIND_PATCH)


def test_a_brief_pairing_every_primary_with_an_independent_read_passes(
    run_local: Callable[..., Findings], per_item_briefs: str
) -> None:
    result = run_local(
        brief_with(CONFORMING_ITEM), "ai-briefs", slug=TODAY, repo=per_item_briefs
    )

    assert not result.blocks


def test_an_item_with_no_primary_blocks(
    run_local: Callable[..., Findings], per_item_briefs: str
) -> None:
    result = run_local(
        brief_with(
            [("https://reuters.com/a", "secondary"), ("https://ft.com/z", "secondary")]
        ),
        "ai-briefs",
        slug=TODAY,
        repo=per_item_briefs,
    )

    assert "B-SOURCE-KIND" in result.blocks


def test_an_item_over_the_secondary_ceiling_blocks(
    run_local: Callable[..., Findings], per_item_briefs: str
) -> None:
    result = run_local(
        brief_with(
            [
                *CONFORMING_ITEM,
                ("https://theverge.com/a", "secondary"),
                ("https://wired.com/a", "secondary"),
            ]
        ),
        "ai-briefs",
        slug=TODAY,
        repo=per_item_briefs,
    )

    assert "B-SOURCE-KIND" in result.blocks


def test_an_item_citing_its_one_primary_twice_still_cites_one_primary(
    run_local: Callable[..., Findings], per_item_briefs: str
) -> None:
    result = run_local(
        brief_with([(ARXIV, "primary"), (ARXIV, "primary"), *CONFORMING_ITEM[1:]]),
        "ai-briefs",
        slug=TODAY,
        repo=per_item_briefs,
    )

    assert not result.blocks


def test_a_kind_the_protocol_does_not_define_blocks_with_no_composition_declared(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        brief_with(CONFORMING_ITEM).replace(
            'data-nb-kind="secondary"', 'data-nb-kind="tertiary"', 1
        ),
        "ai-briefs",
        slug=TODAY,
    )

    assert "B-SOURCE-KIND" in result.blocks


def test_a_source_that_declares_no_kind_blocks_where_the_series_constrains_the_mix(
    run_local: Callable[..., Findings], per_item_briefs: str
) -> None:
    result = run_local(
        brief_with(CONFORMING_ITEM).replace(' data-nb-kind="primary"', "", 1),
        "ai-briefs",
        slug=TODAY,
        repo=per_item_briefs,
    )

    assert "B-SOURCE-KIND" in result.blocks


def test_by_kind_an_article_sourced_only_to_the_documents_it_reports_on_blocks(
    run_local: Callable[..., Findings], by_kind_semis: str
) -> None:
    result = run_local(ALL_PRIMARY, "semiconductors", repo=by_kind_semis)

    assert "B-SOURCE-KIND" in result.blocks


def test_by_kind_a_conforming_mix_passes_and_a_null_ceiling_means_no_ceiling(
    run_local: Callable[..., Findings], by_kind_semis: str
) -> None:
    result = run_local(MIXED, "semiconductors", repo=by_kind_semis)

    assert not result.blocks


def test_by_kind_a_ceiling_is_enforced_too(
    run_local: Callable[..., Findings], patched_repo: Callable[..., str]
) -> None:
    result = run_local(
        MIXED,
        "semiconductors",
        repo=patched_repo("sources_by_kind:\n  secondary: [0, 1]\n"),
    )

    assert "B-SOURCE-KIND" in result.blocks


def test_by_kind_a_source_with_no_kind_escapes_the_mix_so_it_blocks(
    run_local: Callable[..., Findings], by_kind_semis: str
) -> None:
    result = run_local(
        MIXED.replace(
            'data-nb-kind="primary" href="https://example.org/src4"',
            'href="https://example.org/src4"',
        ),
        "semiconductors",
        repo=by_kind_semis,
    )

    assert "B-SOURCE-KIND" in result.blocks


def test_a_series_that_constrains_nothing_says_nothing_about_an_unkinded_source(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(article(), "semiconductors")

    assert "B-SOURCE-KIND" not in result.codes
    assert not result.blocks


def test_by_kind_counts_the_sources_the_article_cites_not_the_ones_it_lists(
    run_local: Callable[..., Findings], patched_repo: Callable[..., str]
) -> None:
    result = run_local(
        LISTED_NOT_CITED,
        "semiconductors",
        repo=patched_repo("sources_by_kind:\n  secondary: [3, null]\n"),
    )

    assert "B-SOURCE-KIND" in result.blocks


def test_a_band_the_config_botched_is_a_finding_not_a_traceback(
    run_local: Callable[..., Findings], patched_repo: Callable[..., str]
) -> None:
    result = run_local(
        MIXED, "semiconductors", repo=patched_repo("sources_by_kind:\n  primary: 4\n")
    )

    assert "B-SERIES" in result.blocks


# --------------------------------------------------------------------------- #
# the compositions a series may declare at all
# --------------------------------------------------------------------------- #


def open_briefs_repo(
    clone_testrepo: Callable[..., str], templates: list[str], patch: str = ""
) -> str:
    """The rolling brief series reopened as an open section with a template choice."""
    tmp = clone_testrepo("press", "templates", "engine")
    y = pathlib.Path(tmp) / "press" / "series" / "ai-briefs" / "series.yaml"
    y.write_text(
        f"name: AI & Semiconductors\nmode: open\ntemplates: [{', '.join(templates)}]\n"
        f"prompt: prompt.md\nautopublish: true\nstrict: false\nmin_sources: 5\n{patch}"
    )
    return tmp


def unkinded_template_repo(patched_repo: Callable[..., str]) -> str:
    """A series constraining the mix, on a template whose sources carry no kind."""
    tmp = patched_repo("sources_by_kind:\n  primary: [4, null]\n")
    skel = pathlib.Path(tmp) / "templates" / "article" / "skeleton.html"
    skel.write_text(skel.read_text().replace(' data-nb-kind="primary"', ""))
    return tmp


def test_per_item_sources_validates_on_a_per_item_template(
    vc_rc: Callable[[str], int], per_item_briefs: str
) -> None:
    assert vc_rc(per_item_briefs) == 0


def test_per_item_sources_on_a_per_section_template_is_a_config_error(
    vc_rc: Callable[[str], int], patched_repo: Callable[..., str]
) -> None:
    assert vc_rc(patched_repo("per_item_sources:\n  primary: [1, 1]\n")) == 1


def test_per_item_sources_validates_when_every_template_choice_cites_per_item(
    vc_rc: Callable[[str], int], clone_testrepo: Callable[..., str]
) -> None:
    assert vc_rc(open_briefs_repo(clone_testrepo, ["brief"], PER_ITEM_PATCH)) == 0


def test_per_item_sources_a_template_choice_could_dodge_is_a_config_error(
    vc_rc: Callable[[str], int], clone_testrepo: Callable[..., str]
) -> None:
    assert (
        vc_rc(open_briefs_repo(clone_testrepo, ["brief", "article"], PER_ITEM_PATCH))
        == 1
    )


def test_sources_by_kind_with_a_null_ceiling_validates(
    vc_rc: Callable[[str], int], by_kind_semis: str
) -> None:
    assert vc_rc(by_kind_semis) == 0


@pytest.mark.parametrize(
    ("name", "patch"),
    [
        ("a kind outside primary/secondary", "sources_by_kind:\n  tertiary: [1, 2]\n"),
        ("a band whose high is below its low", "sources_by_kind:\n  primary: [4, 2]\n"),
        ("a scalar where a band belongs", "sources_by_kind:\n  primary: 4\n"),
    ],
)
def test_a_composition_the_config_botched_is_rejected(
    vc_rc: Callable[[str], int],
    patched_repo: Callable[..., str],
    name: str,
    patch: str,
) -> None:
    assert vc_rc(patched_repo(patch)) == 1


def test_a_composition_on_a_template_that_omits_data_nb_kind_is_a_config_error(
    vc_rc: Callable[[str], int], patched_repo: Callable[..., str]
) -> None:
    assert vc_rc(unkinded_template_repo(patched_repo)) == 1


# --------------------------------------------------------------------------- #
# source link resolution
# --------------------------------------------------------------------------- #
# B-SOURCE-DEAD blocks only on definitive death; everything ambiguous passes,
# so a real-but-restricted source (or an offline runner) never false-blocks.


@pytest.mark.parametrize(
    ("name", "status", "error", "verdict"),
    [
        ("404", 404, None, "dead"),
        ("410", 410, None, "dead"),
        ("a domain that does not resolve", None, "dns", "dead"),
        ("200", 200, None, "ok"),
        ("a 403 bot-block", 403, None, "ok"),
        ("500", 500, None, "ok"),
        ("a timeout", None, "net", "unverified"),
    ],
)
def test_classify_link(
    name: str, status: int | None, error: str | None, verdict: str
) -> None:
    assert check.classify_link(status, error) == verdict


def test_no_links_to_probe_returns_empty() -> None:
    assert check.dead_source_links([]) == []


# The local (rehearsal) branch of main() must forward --check-links, or a dead
# citation passes the press check yet fails B-SOURCE-DEAD in CI. Every source
# points at the reserved `.invalid` TLD (RFC 6761), which never resolves — so
# the probe classifies it dead offline or online, making this deterministic
# without a real network round-trip. The assertion is purely about whether
# main() wires the flag through.
DEAD_ARTICLE = (
    article()
    .replace("https://example.org/", "https://nb-dead.invalid/")
    .replace("https://www.sec.gov/filings/mu-10k", "https://nb-dead.invalid/sec")
)


@pytest.mark.parametrize(
    ("name", "flags", "dead"),
    [
        ("local mode probes links by default", [], True),
        ("--no-check-links suppresses probing locally", ["--no-check-links"], False),
    ],
)
def test_rehearsal_honors_check_links(
    run_main_json: Callable[[list[str]], dict],
    testrepo: str,
    tmp_path: pathlib.Path,
    name: str,
    flags: list[str],
    dead: bool,
) -> None:
    art = tmp_path / "library" / "semiconductors" / "micron.html"
    art.parent.mkdir(parents=True)
    art.write_text(DEAD_ARTICLE)

    out = run_main_json(
        [
            str(art),
            "--series",
            "semiconductors",
            "--repo",
            testrepo,
            "--today",
            TODAY,
            "--json",
            *flags,
        ]
    )

    blocked = {f["code"] for f in out["findings"] if f["level"] == "BLOCK"}
    assert ("B-SOURCE-DEAD" in blocked) is dead
