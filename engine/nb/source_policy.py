"""Resolve the source obligations that a commission must make explicit.

The proof has always applied template-class defaults, but an agent reading only
series.yaml cannot see them. The desk's command uses this deliberately small
copy of that stable policy to make the requirement visible before research.
"""

__all__ = ("DEFAULT_MIN_SOURCES", "minimum", "resolve")

DEFAULT_MIN_SOURCES = {"longread": 8, "shortread": 5}


def minimum(series: dict, template: dict) -> int:
    return series.get("min_sources") or DEFAULT_MIN_SOURCES.get(
        template.get("class", "longread"), 5
    )


def resolve(series: dict, template: dict) -> dict[str, int | dict[str, int]]:
    floor = minimum(series, template)
    policy: dict[str, int | dict[str, int]] = {"min_sources": floor}
    for key in ("sources_by_kind", "per_item_sources"):
        if series.get(key):
            policy[key] = series[key]
    return policy
