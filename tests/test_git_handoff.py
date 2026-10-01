"""Git-dependent commands report connector work without claiming success."""

import os
import shutil
import subprocess
import sys

import pytest

from press import REPO, make_press


@pytest.mark.parametrize("command", ["duty.py", "nb/history.py"])
def test_managed_library_read_without_git_emits_handoff(tmp_path, command) -> None:
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    repo = make_press()
    args = ["--repo", repo] if command == "duty.py" else []
    result = subprocess.run(
        [sys.executable, str(REPO / "engine" / command), *args],
        env={
            **os.environ,
            "NB_ROOT": repo,
            "PATH": str(empty_bin),
            "PYTHONPATH": str(REPO / "engine"),
            "NB_LIBRARY": "",
        },
        capture_output=True,
        text=True,
    )

    assert result.returncode == 3
    assert "NB_GIT_REQUIRED" in result.stdout
    assert '"fetch", "-q", "origin", "library"' in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("command", ["setup", "sync"])
def test_shell_command_without_git_emits_handoff(tmp_path, command) -> None:
    minimal_bin = tmp_path / "bin"
    minimal_bin.mkdir()
    for name in ("dirname", "cat"):
        executable = shutil.which(name)
        assert executable is not None
        (minimal_bin / name).symlink_to(executable)
    result = subprocess.run(
        ["/bin/sh", str(REPO / "scripts" / f"{command}.sh")],
        env={**os.environ, "PATH": str(minimal_bin)},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 3
    assert "NB_GIT_REQUIRED" in result.stderr
    assert "reason=git is not installed" in result.stderr
