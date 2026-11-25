"""Describe Git operations a connected runtime must finish before continuing."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib

HANDOFF_EXIT = 3


class GitHandoffError(RuntimeError):
    def __init__(self, *, repo: pathlib.Path, arguments: tuple[str, ...], reason: str) -> None:
        super().__init__(reason)
        self.repo = repo
        self.arguments = arguments

    def emit(self) -> int:
        argv = json.dumps(["git", "-C", str(self.repo), *self.arguments])
        lines = (
            "NB_GIT_REQUIRED",
            f"reason={self}",
            f"checkout={self.repo}",
            f"argv={argv}",
            (
                "Use the runtime's connected Git/GitHub tools to resolve Git access "
                "and refresh local refs, or restore CLI Git access. Then rerun the "
                "interrupted nb command. After a failed push, rerun preparation; "
                "temporary worktrees may already have been removed."
            ),
        )
        sys.stdout.write("\n".join(lines) + "\n")
        return HANDOFF_EXIT
