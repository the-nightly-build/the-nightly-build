#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Answer PR-shape and press-configuration questions for the CI workflows.

check.yml needs facts that should not be derived in shell: whether the
validated series has autopublish enabled, and which single article the PR
adds (the render probe's target). Keeping this outside check.py keeps the
proof free of workflow concerns and keeps the parsing in one reviewed file
instead of inline logic inside workflow definitions.
"""

import argparse
import subprocess

import nb_meta
import yaml


def added_article(diff_base):
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
        return None
    status, _, path = out[0].partition("\t")
    if status != "A" or not nb_meta.PR_PATH_RE.match(path):
        return None
    return path


def autopublish(repo, diff_base):
    path = added_article(diff_base)
    if path is None:
        print("false")
        return
    series_id = path.split("/")[1]
    try:
        with open(f"{repo}/press/series/{series_id}/series.yaml") as fh:
            cfg = yaml.safe_load(fh)
        # Only a real boolean True auto-merges: a string like 'false' is
        # truthy, so anything but True stays a human-reviewed PR.
        print("true" if cfg.get("autopublish") is True else "false")
    except (OSError, yaml.YAMLError, AttributeError):
        print("false")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["autopublish", "article-path"])
    p.add_argument("--repo", default="_main")
    p.add_argument("--diff-base", required=True)
    a = p.parse_args()
    if a.cmd == "autopublish":
        autopublish(a.repo, a.diff_base)
    else:
        print(added_article(a.diff_base) or "")
