# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Answer PR-shape questions for the CI workflows.

check.yml needs to know whether a PR adds a new article and which single
article a PR adds or revises. Keeping this outside check.py keeps the proof
free of workflow concerns and the path grammar in one reviewed module.
"""

import argparse
import shutil
import subprocess
import sys

from nb import meta as nb_meta
from nb.workflow_sync import classify_workflow_sync

__all__ = ("changed_files",)


def changed_files(diff_base: str) -> list[tuple[str, str]]:
    git = shutil.which("git")
    if git is None:
        message = "git executable not found"
        raise FileNotFoundError(message)
    out = (
        subprocess.run(
            [git, "diff", "--name-status", "--no-renames", f"{diff_base}...HEAD"],
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


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["new-article", "article-path", "sync"])
    p.add_argument("--repo", default="_main")
    p.add_argument("--diff-base", required=True)
    a = p.parse_args()
    if a.cmd == "new-article":
        flag = "true" if nb_meta.article_bundle_path(changed_files(a.diff_base)) is not None else "false"
        sys.stdout.write(f"{flag}\n")
    elif a.cmd == "article-path":
        changes = changed_files(a.diff_base)
        path = nb_meta.article_bundle_path(changes) or nb_meta.revision_bundle_path(changes)
        sys.stdout.write(f"{path or ''}\n")
    else:
        sync = classify_workflow_sync(
            ".",
            a.repo,
            head="HEAD",
            changes=changed_files(a.diff_base),
        )
        sys.stdout.write(f"{'true' if sync.valid else 'false'}\n")
