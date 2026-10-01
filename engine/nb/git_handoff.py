"""Describe Git operations a connected runtime must finish before continuing."""

from __future__ import annotations

import json
import pathlib

HANDOFF_EXIT = 3


class GitHandoffError(RuntimeError):
    def __init__(self, *, repo: pathlib.Path, arguments: tuple[str, ...], reason: str):
        super().__init__(reason)
        self.repo = repo
        self.arguments = arguments

    def emit(self) -> int:
        print("NB_GIT_REQUIRED")
        print(f"reason={self}")
        print(f"checkout={self.repo}")
        print("argv=" + json.dumps(["git", "-C", str(self.repo), *self.arguments]))
        print(
            "Use the runtime's connected Git/GitHub tools to resolve Git access "
            "and refresh local refs, or restore CLI Git access. Then rerun the "
            "interrupted nb command. After a failed push, rerun preparation; "
            "temporary worktrees may already have been removed."
        )
        return HANDOFF_EXIT
