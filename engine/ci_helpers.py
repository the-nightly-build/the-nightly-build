#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Answer PR-shape and press-configuration questions for the CI workflows.

check.yml needs facts that should not be derived in shell: whether the
validated series has autopublish enabled, and which single article the PR
adds or revises (the render probe's target). Keeping this outside check.py
keeps the proof free of workflow concerns and keeps the parsing in one
reviewed file instead of inline logic inside workflow definitions.
"""

import argparse
import subprocess

import yaml

from nb import meta as nb_meta
from nb.workflow_sync import classify_workflow_sync

__all__ = ("autopublish", "changed_files")


def changed_files(diff_base: str) -> list[tuple[str, str]]:
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
    changes: list[tuple[str, str]] = []
    for line in out:
        status, _, path = line.partition("\t")
        if path:
            changes.append((status, path))
    return changes


def autopublish(repo: str, diff_base: str) -> None:
    path = nb_meta.article_bundle_path(changed_files(diff_base))
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
    p.add_argument("cmd", choices=["autopublish", "article-path", "sync"])
    p.add_argument("--repo", default="_main")
    p.add_argument("--diff-base", required=True)
    a = p.parse_args()
    if a.cmd == "autopublish":
        autopublish(a.repo, a.diff_base)
    elif a.cmd == "article-path":
        changes = changed_files(a.diff_base)
        path = nb_meta.article_bundle_path(changes) or nb_meta.revision_bundle_path(
            changes
        )
        print(path or "")
    else:
        sync = classify_workflow_sync(
            ".",
            a.repo,
            head="HEAD",
            changes=changed_files(a.diff_base),
        )
        print("true" if sync.valid else "false")
