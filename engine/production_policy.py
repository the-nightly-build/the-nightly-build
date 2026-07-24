#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Print the resolved model and effort guidance for an article's roles.

The correspondent runs this command before launching production. Its JSON
output is safe to copy into ``task.md`` without reconstructing configuration
precedence in a model prompt.
"""

import argparse
import json
import os

from nb.config import load_series, load_yaml
from nb.production_policy import ProductionPolicy, StagePolicy, resolve


def _stage_policy(value: dict) -> StagePolicy:
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


def _production_policy(value: dict | None) -> ProductionPolicy | None:
    if not isinstance(value, dict):
        return None
    policy: ProductionPolicy = {}
    profile = value.get("profile")
    required = value.get("required")
    stages = value.get("stages")
    if isinstance(profile, str):
        policy["profile"] = profile
    if isinstance(required, bool):
        policy["required"] = required
    if isinstance(stages, dict):
        policy["stages"] = {
            stage: _stage_policy(stage_policy)
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
        raise SystemExit(f"configured series not found: {series_path}")

    press_path = os.path.join(args.repo, "press", "production.yaml")
    press = load_yaml(press_path) if os.path.isfile(press_path) else None
    result = resolve(
        _production_policy(press),
        _production_policy(series.get("production")),
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
