"""Recognize the one non-article change allowed to reach ``library``.

A workflow sync is a content-addressed exception, not a title, label, or PR
author. It is valid only when the PR changes one or both publishing workflows,
changes nothing else, and copies their exact blobs from the fork's ``main``.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

__all__ = ("WorkflowSync", "classify_workflow_sync")

SYNC_PATHS = frozenset(
    {
        ".github/workflows/check.yml",
        ".github/workflows/publish.yml",
    }
)


@dataclass(frozen=True)
class WorkflowSync:
    attempted: bool
    valid: bool
    reason: str | None = None


def _git_executable() -> str:
    git = shutil.which("git")
    if git is None:
        msg = "git executable not found on PATH"
        raise FileNotFoundError(msg)
    return git


def classify_workflow_sync(
    repo: str | Path,
    main: str | Path,
    *,
    head: str,
    changes: list[tuple[str, str]],
) -> WorkflowSync:
    changed_paths = {path for _status, path in changes}
    attempted = bool(changed_paths & SYNC_PATHS)
    if not attempted:
        return WorkflowSync(attempted=False, valid=False)

    if not changed_paths <= SYNC_PATHS or len(changes) != len(changed_paths):
        return WorkflowSync(
            attempted=True,
            valid=False,
            reason="a workflow sync may change only the publishing workflows",
        )

    invalid_statuses = [status for status, _path in changes if status not in {"A", "M"}]
    if invalid_statuses:
        return WorkflowSync(
            attempted=True,
            valid=False,
            reason="a workflow sync may only add or update the publishing workflows",
        )

    git = _git_executable()
    for path in sorted(changed_paths):
        canonical_path = Path(main, path)
        try:
            canonical = canonical_path.read_bytes()
            proposed = subprocess.run(
                [git, "-C", str(repo), "show", f"{head}:{path}"],
                capture_output=True,
                check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError):
            return WorkflowSync(
                attempted=True,
                valid=False,
                reason=f"cannot compare {path} with the fork's main branch",
            )
        if proposed != canonical:
            return WorkflowSync(
                attempted=True,
                valid=False,
                reason=f"{path} does not exactly match the fork's main branch",
            )

    return WorkflowSync(attempted=True, valid=True)
