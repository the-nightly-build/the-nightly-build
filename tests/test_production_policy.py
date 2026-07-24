"""Production guidance stays portable while resolving deterministically.

The resolver is the single source of truth for profile, press, and series
precedence, so a correspondent never has to reproduce configuration logic in a
prompt. These tests also protect the deliberate boundary between portable
semantic tiers and exact provider model overrides.
"""

import json
import pathlib
import subprocess
import sys
from collections.abc import Callable

import pytest

from nb.production_policy import STAGES, ProductionPolicy, resolve
from press import REPO


def test_missing_configuration_uses_the_cost_aware_default() -> None:
    policy = resolve()

    assert policy["profile"] == "balanced"
    assert policy["stages"] == {
        "writing-coach": {
            "model": "capable",
            "effort": "medium",
            "required": False,
        },
        "researcher": {
            "model": "efficient",
            "effort": "medium",
            "required": False,
        },
        "writer": {"model": "capable", "effort": "high", "required": False},
        "editor": {"model": "capable", "effort": "high", "required": False},
        "publisher": {
            "model": "efficient",
            "effort": "low",
            "required": False,
        },
    }


def test_inherit_is_an_explicit_profile() -> None:
    policy = resolve({"profile": "inherit"})

    assert policy["stages"] == {
        stage: {"model": "inherit", "effort": "inherit", "required": False}
        for stage in STAGES
    }


@pytest.mark.parametrize(
    ("profile", "writer", "publisher"),
    [
        pytest.param(
            "economy",
            {"model": "capable", "effort": "medium", "required": False},
            {"model": "efficient", "effort": "low", "required": False},
            id="economy",
        ),
        pytest.param(
            "balanced",
            {"model": "capable", "effort": "high", "required": False},
            {"model": "efficient", "effort": "low", "required": False},
            id="balanced",
        ),
        pytest.param(
            "quality",
            {"model": "premium", "effort": "high", "required": False},
            {"model": "efficient", "effort": "low", "required": False},
            id="quality",
        ),
    ],
)
def test_profiles_resolve_complete_role_guidance(
    profile: str,
    *,
    writer: dict[str, str | bool],
    publisher: dict[str, str | bool],
) -> None:
    policy = resolve({"profile": profile})

    assert policy["stages"]["writer"] == writer
    assert policy["stages"]["publisher"] == publisher


def test_series_overrides_press_fields_without_erasing_other_defaults() -> None:
    press: ProductionPolicy = {
        "profile": "balanced",
        "required": True,
        "stages": {
            "writer": {"model": "provider/exact-writer"},
            "editor": {"required": False},
        },
    }
    series: ProductionPolicy = {
        "profile": "economy",
        "required": False,
        "stages": {
            "writer": {"effort": "xhigh", "required": True},
        },
    }

    policy = resolve(press, series)

    assert policy["profile"] == "economy"
    assert policy["stages"]["writer"] == {
        "model": "provider/exact-writer",
        "effort": "xhigh",
        "required": True,
    }
    assert policy["stages"]["editor"]["required"] is False
    assert policy["stages"]["researcher"] == {
        "model": "efficient",
        "effort": "low",
        "required": False,
    }


def test_cli_reads_press_and_series_policy(
    clone_testrepo: Callable[..., str],
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "engine", "templates"))
    (repo / "press" / "production.yaml").write_text(
        "profile: balanced\nstages:\n  writer:\n    model: provider/writer\n"
    )
    series = repo / "press" / "series" / "semiconductors" / "series.yaml"
    series.write_text(
        series.read_text()
        + "\nproduction:\n  stages:\n    writer:\n      effort: max\n"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "engine" / "production_policy.py"),
            "--repo",
            str(repo),
            "--series",
            "semiconductors",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    policy = json.loads(result.stdout)

    assert policy["profile"] == "balanced"
    assert policy["stages"]["writer"] == {
        "model": "provider/writer",
        "effort": "max",
        "required": False,
    }
