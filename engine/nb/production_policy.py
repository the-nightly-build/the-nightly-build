"""Resolve harness-agnostic model and effort guidance for article roles.

Production policy is advice for the runtime, not a provider configuration file.
This module turns semantic presets plus press and series overrides into the
complete role-by-role directives copied into each article commission.
"""

from typing import TypedDict

STAGES = (
    "writing-coach",
    "researcher",
    "writer",
    "editor",
    "publisher",
)
PROFILES = ("inherit", "economy", "balanced", "quality")
MODEL_TIERS = ("inherit", "efficient", "capable", "premium")


class StagePolicy(TypedDict, total=False):
    model: str
    effort: str
    required: bool


class ProductionPolicy(TypedDict, total=False):
    profile: str
    required: bool
    stages: dict[str, StagePolicy]


class ResolvedStagePolicy(TypedDict):
    model: str
    effort: str
    required: bool


class ResolvedProductionPolicy(TypedDict):
    profile: str
    stages: dict[str, ResolvedStagePolicy]


_PROFILE_PRESETS: dict[str, dict[str, tuple[str, str]]] = {
    "inherit": {stage: ("inherit", "inherit") for stage in STAGES},
    "economy": {
        "writing-coach": ("efficient", "medium"),
        "researcher": ("efficient", "low"),
        "writer": ("capable", "medium"),
        "editor": ("capable", "medium"),
        "publisher": ("efficient", "low"),
    },
    "balanced": {
        "writing-coach": ("capable", "medium"),
        "researcher": ("efficient", "medium"),
        "writer": ("capable", "high"),
        "editor": ("capable", "high"),
        "publisher": ("efficient", "low"),
    },
    "quality": {
        "writing-coach": ("premium", "high"),
        "researcher": ("capable", "high"),
        "writer": ("premium", "high"),
        "editor": ("premium", "high"),
        "publisher": ("efficient", "low"),
    },
}


def _profile_name(
    press: ProductionPolicy | None, series: ProductionPolicy | None
) -> str:
    for policy in (series, press):
        if policy is None:
            continue
        profile = policy.get("profile")
        if profile in PROFILES:
            return profile
    return "balanced"


def _apply_stage_fields(
    resolved: dict[str, ResolvedStagePolicy], policy: ProductionPolicy | None
) -> None:
    if policy is None:
        return
    stages = policy.get("stages", {})
    for stage in STAGES:
        override = stages.get(stage)
        if override is None:
            continue
        model = override.get("model")
        effort = override.get("effort")
        if isinstance(model, str) and model.strip():
            resolved[stage]["model"] = model.strip()
        if isinstance(effort, str) and effort.strip():
            resolved[stage]["effort"] = effort.strip()


def _apply_required(
    resolved: dict[str, ResolvedStagePolicy], policy: ProductionPolicy | None
) -> None:
    if policy is None:
        return
    required = policy.get("required")
    if isinstance(required, bool):
        for stage in STAGES:
            resolved[stage]["required"] = required
    stages = policy.get("stages", {})
    for stage in STAGES:
        override = stages.get(stage)
        if override is not None and isinstance(override.get("required"), bool):
            resolved[stage]["required"] = override["required"]


def resolve(
    press: ProductionPolicy | None = None,
    series: ProductionPolicy | None = None,
) -> ResolvedProductionPolicy:
    profile = _profile_name(press, series)
    stages: dict[str, ResolvedStagePolicy] = {
        stage: {
            "model": _PROFILE_PRESETS[profile][stage][0],
            "effort": _PROFILE_PRESETS[profile][stage][1],
            "required": False,
        }
        for stage in STAGES
    }
    _apply_stage_fields(stages, press)
    _apply_stage_fields(stages, series)
    _apply_required(stages, press)
    _apply_required(stages, series)
    return {"profile": profile, "stages": stages}


__all__ = (
    "MODEL_TIERS",
    "PROFILES",
    "STAGES",
    "ProductionPolicy",
    "ResolvedProductionPolicy",
    "ResolvedStagePolicy",
    "StagePolicy",
    "resolve",
)
