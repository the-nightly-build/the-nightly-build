"""Keep the orchestrator's source policy identical to the proof's policy.

The regression here is the hidden longread default. A series without an explicit
minimum must still commission research for eight sources rather than discovering
the requirement only when proof runs, and declared kind composition must survive.
"""

from nb.config import apply_template_bands
from nb.source_policy import minimum, resolve


def test_template_default_is_visible_to_the_orchestrator() -> None:
    assert resolve({}, {"class": "longread"}) == {"min_sources": 8}
    assert minimum({}, {"class": "longread"}) == 8


def test_explicit_zero_disables_the_source_default() -> None:
    assert minimum({"min_sources": 0}, {"class": "longread"}) == 0


def test_series_bands_replace_defaults_field_by_field() -> None:
    effective = apply_template_bands(
        {"bands": {"words": [800, 2000], "flex_sections": [1, 3]}},
        series={"bands": {"words": [100, 5000]}},
    )

    assert effective["bands"] == {
        "words": [100, 5000],
        "flex_sections": [1, 3],
    }


def test_series_policy_overrides_the_default_and_keeps_composition() -> None:
    assert resolve(
        {"min_sources": 4, "sources_by_kind": {"primary": 1, "secondary": 2}},
        {"class": "longread"},
    ) == {
        "min_sources": 4,
        "sources_by_kind": {"primary": 1, "secondary": 2},
    }
