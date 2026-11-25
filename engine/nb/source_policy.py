"""Resolve the source obligations that a commission must make explicit.

The proof has always applied template-class defaults, but an agent reading only
series.yaml cannot see them. The orchestrator's command uses this deliberately
small copy of that stable policy to make the requirement visible before research.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ("DEFAULT_MIN_SOURCES", "minimum", "resolve")

DEFAULT_MIN_SOURCES = {"longread": 8, "shortread": 5}


def minimum(series: Mapping[str, object], template: Mapping[str, object]) -> int:
    configured = series.get("min_sources")
    if isinstance(configured, int) and not isinstance(configured, bool) and configured >= 0:
        return configured
    template_class = template.get("class", "longread")
    return DEFAULT_MIN_SOURCES.get(template_class, 5) if isinstance(template_class, str) else 5


def resolve(series: Mapping[str, object], template: Mapping[str, object]) -> dict[str, object]:
    floor = minimum(series, template)
    policy: dict[str, object] = {"min_sources": floor}
    for key in ("sources_by_kind", "per_item_sources"):
        value = series.get(key)
        if value:
            policy[key] = value
    return policy
