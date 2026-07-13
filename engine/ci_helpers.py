#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Answer press-configuration questions for the CI workflows.

check.yml needs facts that live in series.yaml but should not be parsed in
shell, currently just whether the validated series has autopublish
enabled. Keeping this outside check.py keeps the proof free of workflow
concerns and keeps the YAML parsing in one reviewed file instead of inline
python inside workflow definitions.
"""

import argparse
import re
import subprocess

import yaml

PR_PATH_RE = re.compile(r"^library/([a-z0-9-]{1,32})/[a-z0-9-]{1,64}\.html$")


def autopublish(repo, diff_base):
    out = (
        subprocess.run(
            ["git", "diff", "--name-status", "--no-renames", f"{diff_base}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        .stdout.strip()
        .splitlines()
    )
    if len(out) != 1:
        print("false")
        return
    status, _, path = out[0].partition("\t")
    if status != "A":
        print("false")
        return
    m = PR_PATH_RE.match(path)
    if not m:
        print("false")
        return
    try:
        with open(f"{repo}/press/series/{m.group(1)}/series.yaml") as fh:
            cfg = yaml.safe_load(fh)
        # Only a real boolean True auto-merges: a string like 'false' is
        # truthy, so anything but True stays a human-reviewed PR.
        print("true" if cfg.get("autopublish") is True else "false")
    except (OSError, yaml.YAMLError, AttributeError):
        print("false")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["autopublish"])
    p.add_argument("--repo", default="_main")
    p.add_argument("--diff-base", required=True)
    a = p.parse_args()
    autopublish(a.repo, a.diff_base)
