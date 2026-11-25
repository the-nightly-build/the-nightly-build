# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Print the resolved model and effort guidance for an article's roles.

The orchestrator runs this command before launching production. Its JSON
output is safe to resolve into each exact role brief without reconstructing
configuration precedence in a model prompt.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import TYPE_CHECKING, NoReturn

from nb.config import load_series, load_yaml
from nb.production_policy import ProductionPolicy, StagePolicy, resolve

if TYPE_CHECKING:
    from collections.abc import Mapping


def _die(message: str) -> NoReturn:
    sys.stderr.write(f"{message}\n")
    raise SystemExit(1)


def _stage_policy(value: Mapping[str, object]) -> StagePolicy:
    policy: StagePolicy = {}
    model = value.get("model")
    effort = value.get("effort")
    required = value.get("required")
    if isinstance(model, str):
        policy["model"] = model
    if isinstance(effort, str):
        policy["effort"] = effort
    if isinstance(required, bool):
        policy["required"] = required
    return policy


def _production_policy(value: object) -> ProductionPolicy | None:
    if not isinstance(value, dict):
        return None
    raw = {str(key): item for key, item in value.items()}
    policy: ProductionPolicy = {}
    profile = raw.get("profile")
    required = raw.get("required")
    stages = raw.get("stages")
    if isinstance(profile, str):
        policy["profile"] = profile
    if isinstance(required, bool):
        policy["required"] = required
    if isinstance(stages, dict):
        policy["stages"] = {
            stage: _stage_policy({str(k): v for k, v in stage_policy.items()})
            for stage, stage_policy in stages.items()
            if isinstance(stage, str) and isinstance(stage_policy, dict)
        }
    return policy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--series", required=True)
    args = parser.parse_args()

    series, series_path = load_series(args.repo, args.series)
    if not isinstance(series, dict):
        _die(f"configured series not found: {series_path}")

    press_path = pathlib.Path(args.repo) / "press" / "production.yaml"
    press = load_yaml(press_path) if press_path.is_file() else None
    result = resolve(
        _production_policy(press),
        _production_policy(series.get("production")),
    )
    sys.stdout.write(f"{json.dumps(result, sort_keys=True)}\n")


if __name__ == "__main__":
    main()
