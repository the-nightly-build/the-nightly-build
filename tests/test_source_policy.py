"""Keep the desk's visible source policy identical to the proof's policy.

The regression here is the hidden longread default. A series without an explicit
minimum must still commission research for eight sources rather than discovering
the requirement only when proof runs, and declared kind composition must survive.
"""

from nb.source_policy import minimum, resolve


def test_template_default_is_visible_to_the_desk() -> None:
    assert resolve({}, {"class": "longread"}) == {"min_sources": 8}
    assert minimum({}, {"class": "longread"}) == 8


def test_series_policy_overrides_the_default_and_keeps_composition() -> None:
    assert resolve(
        {"min_sources": 4, "sources_by_kind": {"primary": 1, "secondary": 2}},
        {"class": "longread"},
    ) == {
        "min_sources": 4,
        "sources_by_kind": {"primary": 1, "secondary": 2},
    }
