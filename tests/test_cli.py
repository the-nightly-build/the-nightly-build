"""The public command is a thin, checkout-owned facade over existing tools.

These tests keep the facade honest: every advertised command must resolve
inside the trusted checkout instead of relying on a global installation. The
root-launcher check also catches environment or packaging drift that unit tests
of the dispatcher alone would miss.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

from nb import cli
from press import REPO


def test_help_describes_every_public_command() -> None:
    help_text = cli.help_text()

    for name, command in cli.COMMANDS.items():
        assert name in help_text
        assert command.description in help_text
        assert command.audience in help_text


def test_dispatch_uses_the_current_python_for_python_tools() -> None:
    invocation = cli.command_arguments("check", ["--help"], root=REPO)

    assert invocation[0] == sys.executable
    assert pathlib.Path(invocation[1]) == REPO / "engine" / "check.py"
    assert invocation[2:] == ["--help"]


def test_dispatch_executes_shell_tools_directly() -> None:
    invocation = cli.command_arguments("sync", ["--help"], root=REPO)

    assert invocation == [str(REPO / "scripts" / "sync.sh"), "--help"]


def test_root_launcher_exposes_the_command_surface() -> None:
    result = subprocess.run(
        [str(REPO / "nb"), "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Commands:" in result.stdout
    assert "check" in result.stdout
    assert "history" in result.stdout
