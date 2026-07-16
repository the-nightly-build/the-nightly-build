"""Rubrics: pinned criteria enforced, row integrity, and the citation warn.

The rubric contract is attribute-driven (data-nb-criterion + data-score), so
these tests run it on a synthetic press template rather than a shipped one —
proving the rules are registry- and series-driven, never hardcoded to a
template name. Integrity failures (a dropped pinned criterion, a meter text
that disagrees with its attribute, a bad score) block regardless of strict;
the uncited-row finding is a warn that strict escalates, like any
calibration-tier finding.
"""

import pathlib
from collections.abc import Callable

import pytest

from findings import Findings
from press import LOREM

SOURCES = "".join(
    f'<li id="s{i}"><a data-nb-source href="https://example.org/u{i}">x</a></li>'
    for i in range(1, 6)
)

ROWS = """
<div class="nb-rubric-row" data-nb-criterion="speed" data-score="5">
  <span class="nb-rubric-name">Speed</span>
  <span class="nb-rubric-score">5/5</span>
  <p class="nb-rubric-note">Fast.<sup class="nb-cite"><a href="#s1">1</a></sup></p>
</div>
<div class="nb-rubric-row" data-nb-criterion="evidence" data-score="3">
  <span class="nb-rubric-name">Evidence</span>
  <span class="nb-rubric-score">3/5</span>
  <p class="nb-rubric-note">Mixed.<sup class="nb-cite"><a href="#s2">2</a></sup></p>
</div>
<div class="nb-rubric-row" data-nb-criterion="battery-life" data-score="1">
  <span class="nb-rubric-name">Battery life</span>
  <span class="nb-rubric-score">1/5</span>
  <p class="nb-rubric-note">Short.<sup class="nb-cite"><a href="#s3">3</a></sup></p>
</div>
"""


def review(rows: str = ROWS) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Some Tool</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "bench", "slug": "some-tool",
  "template": "scored", "title": "Some Tool", "mode": "collection",
  "order": null, "date": "2026-07-06", "tags": [], "sources": 5,
  "words": 460, "reading_minutes": 2, "dek": "Reviewed.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body>
<section data-nb-section="rubric">{rows}<p>{LOREM * 7}
<sup class="nb-cite"><a href="#s1">1</a></sup></p></section>
<section data-nb-section="sources"><ol>{SOURCES}</ol></section>
</body></html>"""


SCORED_MANIFEST = (
    "class: shortread\nwords: [200, 3000]\n"
    "sections: [rubric, sources]\ncite_rule: per-section\nmodes: [collection]\n"
)

SCORED_SKELETON = """<!DOCTYPE html><html><body>
<section data-nb-section="rubric">
<div class="nb-rubric-row" data-nb-criterion="CRITERION-SLUG" data-score="0">
<span class="nb-rubric-score">0/5</span></div>
</section>
<section data-nb-section="sources"></section>
</body></html>"""

BENCH_SERIES = """name: The Bench
mode: collection
template: scored
autopublish: true
strict: false
rubric:
  - id: speed
    name: Speed
  - id: evidence
    name: Evidence
    note: Independent tests, never the vendor's demo.
items:
  - {slug: some-tool, title: Some Tool}
"""


@pytest.fixture
def rubric_repo(clone_testrepo: Callable[..., str]) -> str:
    repo = clone_testrepo("press", "templates", "engine")
    template = pathlib.Path(repo) / "press" / "templates" / "scored"
    template.mkdir(parents=True)
    (template / "manifest.yaml").write_text(SCORED_MANIFEST)
    (template / "skeleton.html").write_text(SCORED_SKELETON)
    series = pathlib.Path(repo) / "press" / "series" / "bench"
    series.mkdir()
    (series / "series.yaml").write_text(BENCH_SERIES)
    return repo


def test_pinned_criteria_plus_an_extension_row_pass(
    run_local: Callable[..., Findings], rubric_repo: str
) -> None:
    result = run_local(review(), "bench", slug="some-tool", repo=rubric_repo)
    assert not result.blocks
    assert "W-RUBRIC" not in result.codes


def test_a_dropped_pinned_criterion_blocks(
    run_local: Callable[..., Findings], rubric_repo: str
) -> None:
    rows = ROWS.replace('data-nb-criterion="evidence"', 'data-nb-criterion="extras"')
    result = run_local(review(rows), "bench", slug="some-tool", repo=rubric_repo)
    assert "B-RUBRIC" in result.blocks


def test_zero_rows_under_a_pinning_series_blocks(
    run_local: Callable[..., Findings], rubric_repo: str
) -> None:
    result = run_local(review(rows=""), "bench", slug="some-tool", repo=rubric_repo)
    assert "B-RUBRIC" in result.blocks


def test_a_duplicate_criterion_blocks(
    run_local: Callable[..., Findings], rubric_repo: str
) -> None:
    rows = ROWS.replace('data-nb-criterion="battery-life"', 'data-nb-criterion="speed"')
    result = run_local(review(rows), "bench", slug="some-tool", repo=rubric_repo)
    assert "B-RUBRIC" in result.blocks


@pytest.mark.parametrize("bad_score", ["6", "-1", "mixed", None])
def test_a_score_outside_the_scale_blocks(
    run_local: Callable[..., Findings], rubric_repo: str, *, bad_score: str | None
) -> None:
    if bad_score is None:
        rows = ROWS.replace(' data-score="5"', "", 1)
    else:
        rows = ROWS.replace('data-score="5"', f'data-score="{bad_score}"', 1)
    result = run_local(review(rows), "bench", slug="some-tool", repo=rubric_repo)
    assert "B-RUBRIC" in result.blocks


def test_rendered_score_text_must_match_the_attribute(
    run_local: Callable[..., Findings], rubric_repo: str
) -> None:
    rows = ROWS.replace(
        '<span class="nb-rubric-score">5/5</span>',
        '<span class="nb-rubric-score">4/5</span>',
    )
    result = run_local(review(rows), "bench", slug="some-tool", repo=rubric_repo)
    assert "B-RUBRIC" in result.blocks


def test_a_malformed_criterion_slug_blocks(
    run_local: Callable[..., Findings], rubric_repo: str
) -> None:
    rows = ROWS.replace(
        'data-nb-criterion="battery-life"', 'data-nb-criterion="Battery Life!"'
    )
    result = run_local(review(rows), "bench", slug="some-tool", repo=rubric_repo)
    assert "B-RUBRIC" in result.blocks


def test_an_uncited_row_warns_and_strict_escalates(
    run_local: Callable[..., Findings], rubric_repo: str
) -> None:
    rows = ROWS.replace(
        'Short.<sup class="nb-cite"><a href="#s3">3</a></sup>', "Short."
    )
    result = run_local(review(rows), "bench", slug="some-tool", repo=rubric_repo)
    assert "W-RUBRIC" in result.codes
    assert "W-RUBRIC" not in result.blocks

    series_yaml = pathlib.Path(rubric_repo, "press", "series", "bench", "series.yaml")
    series_yaml.write_text(
        series_yaml.read_text().replace("strict: false", "strict: true")
    )
    strict_result = run_local(review(rows), "bench", slug="some-tool", repo=rubric_repo)
    assert "W-RUBRIC" in strict_result.blocks


def test_rows_in_a_series_without_a_rubric_are_still_integrity_checked(
    run_local: Callable[..., Findings], rubric_repo: str
) -> None:
    series_yaml = pathlib.Path(rubric_repo, "press", "series", "bench", "series.yaml")
    series_yaml.write_text(
        "name: The Bench\nmode: collection\ntemplate: scored\n"
        "items:\n  - {slug: some-tool, title: Some Tool}\n"
    )
    rows = ROWS.replace('data-score="5"', 'data-score="9"', 1)
    result = run_local(review(rows), "bench", slug="some-tool", repo=rubric_repo)
    assert "B-RUBRIC" in result.blocks


def test_validate_config_accepts_a_pinning_series(
    vc_rc: Callable[[str], int], rubric_repo: str
) -> None:
    assert vc_rc(rubric_repo) == 0


def test_validate_config_rejects_a_malformed_rubric(
    vc_rc: Callable[[str], int], rubric_repo: str
) -> None:
    series_yaml = pathlib.Path(rubric_repo, "press", "series", "bench", "series.yaml")
    series_yaml.write_text(
        series_yaml.read_text().replace(
            "  - id: speed\n    name: Speed\n", "  - id: speed\n"
        )
    )
    assert vc_rc(rubric_repo) == 1


def test_validate_config_rejects_a_rowless_skeleton_under_a_pinning_series(
    vc_rc: Callable[[str], int], rubric_repo: str
) -> None:
    skeleton = pathlib.Path(
        rubric_repo, "press", "templates", "scored", "skeleton.html"
    )
    skeleton.write_text(
        "<!DOCTYPE html><html><body>"
        '<section data-nb-section="rubric"></section>'
        '<section data-nb-section="sources"></section>'
        "</body></html>"
    )
    assert vc_rc(rubric_repo) == 1
