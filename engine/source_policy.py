# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Print the resolved source obligations for a commissioned series.

The orchestrator uses this before commissioning so each relevant brief receives
the real source floor, including a template default intentionally absent from
series.yaml.
It writes JSON only, which makes the result safe to copy into a commission card
without asking an agent to recreate source-policy logic from configuration prose.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import NoReturn

from nb.config import load_registry, load_series, template_choices
from nb.source_policy import resolve


def _die(message: str) -> NoReturn:
    sys.stderr.write(f"{message}\n")
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--series", required=True)
    args = parser.parse_args()
    series, path = load_series(args.repo, args.series)
    if not isinstance(series, dict):
        _die(f"configured series not found: {path}")
    series_map = {str(key): value for key, value in series.items()}
    registry = load_registry(args.repo)
    template_ids = template_choices(series_map)
    if not template_ids:
        _die(f"series has no template choices: {path}")
    unknown = [template_id for template_id in template_ids if not isinstance(registry.get(template_id), dict)]
    if unknown:
        _die(f"unknown template(s): {', '.join(unknown)}")
    policies = {
        template_id: resolve(series_map, {str(k): v for k, v in template.items()})
        for template_id in template_ids
        if isinstance(template := registry.get(template_id), dict)
    }
    shared = {
        key: series_map[key] for key in ("sources_by_kind", "per_item_sources") if series_map.get(key) is not None
    }
    sys.stdout.write(f"{json.dumps({'templates': policies, 'series': shared}, sort_keys=True)}\n")


if __name__ == "__main__":
    main()
