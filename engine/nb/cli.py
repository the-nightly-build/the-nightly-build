"""One public command surface for the Nightly Build.

The command intentionally delegates to the repository's existing executable
modules. It centralizes discovery and dependency setup without creating a
second implementation of proof, rendering, scheduling, or configuration.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from dataclasses import dataclass

__all__ = (
    "COMMANDS",
    "Command",
    "checkout_root",
    "command_arguments",
    "executable",
    "help_text",
    "main",
    "parser",
)


@dataclass(frozen=True)
class Command:
    path: str
    description: str
    audience: str


COMMANDS = {
    "setup": Command(
        "scripts/setup.sh", "Set up a press and its publishing boundary", "human"
    ),
    "sync": Command(
        "scripts/sync.sh", "Synchronize protected publishing workflows", "orchestrator"
    ),
    "duty": Command(
        "engine/duty.py", "Resolve articles due for a UTC date", "orchestrator"
    ),
    "validate": Command(
        "engine/validate_config.py", "Validate press configuration", "human"
    ),
    "source-policy": Command(
        "engine/source_policy.py",
        "Resolve an article's source obligations",
        "orchestrator",
    ),
    "production-policy": Command(
        "engine/production_policy.py",
        "Resolve role model and effort guidance",
        "orchestrator",
    ),
    "check": Command(
        "engine/check.py", "Check an article or Article PR", "writer, editor, CI"
    ),
    "preview": Command(
        "engine/build_site.py",
        "Build a site with draft articles",
        "writer, editor, human",
    ),
    "build": Command("engine/build_site.py", "Build the published static site", "CI"),
    "asset": Command(
        "engine/capture_asset.py", "Capture a bounded source asset", "writer"
    ),
    "chart": Command(
        "engine/render_chart.py", "Render a chart with the press theme", "writer"
    ),
    "render-check": Command(
        "engine/render_check.py", "Probe a rendered article in Chrome", "CI"
    ),
    "ci": Command("engine/ci_helpers.py", "Resolve deterministic workflow facts", "CI"),
    "history": Command(
        "engine/nb/history.py",
        "Search bounded records of published coverage",
        "orchestrator, researcher, writer, editor",
    ),
    "start-article": Command(
        "engine/nb/start_article.py",
        "Initialize one exact article workspace",
        "orchestrator",
    ),
    "prepare-pr": Command(
        "engine/nb/prepare_pr.py",
        "Prepare and open one exact Article PR",
        "orchestrator",
    ),
}


def checkout_root() -> pathlib.Path:
    configured = os.environ.get("NB_ROOT")
    return (
        pathlib.Path(configured).resolve()
        if configured
        else pathlib.Path(__file__).resolve().parents[2]
    )


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog="nb",
        description="The Nightly Build command line",
        add_help=False,
    )
    command.add_argument("-h", "--help", action="store_true")
    command.add_argument("command", nargs="?")
    command.add_argument("arguments", nargs=argparse.REMAINDER)
    return command


def help_text() -> str:
    width = max(len(name) for name in COMMANDS)
    lines = [
        "The Nightly Build command line",
        "",
        "Usage: nb <command> [arguments]",
        "",
        "Commands:",
    ]
    for name, command in COMMANDS.items():
        lines.append(f"  {name:<{width}}  {command.description} [{command.audience}]")
    lines.extend(("", "Run nb <command> --help for command-specific options."))
    return "\n".join(lines)


def executable(command: Command, *, root: pathlib.Path | None = None) -> pathlib.Path:
    target = (root or checkout_root()) / command.path
    if not target.is_file():
        raise SystemExit(f"nb installation is incomplete: missing {target}")
    return target


def command_arguments(
    name: str, arguments: list[str], *, root: pathlib.Path | None = None
) -> list[str]:
    command = COMMANDS[name]
    target = executable(command, root=root)
    if target.suffix == ".sh":
        return [str(target), *arguments]
    return [sys.executable, str(target), *arguments]


def main(arguments: list[str] | None = None) -> None:
    parsed = parser().parse_args(arguments)
    if parsed.help or parsed.command is None:
        print(help_text())
        return
    if parsed.command not in COMMANDS:
        raise SystemExit(f"unknown command: {parsed.command}\n\n{help_text()}")

    invocation = command_arguments(parsed.command, parsed.arguments)
    os.execv(invocation[0], invocation)


if __name__ == "__main__":
    main()
