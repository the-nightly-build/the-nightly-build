"""Exercise deterministic Article PR preparation against a real Git remote.

The fixtures create a protected-branch-shaped bare repository and invoke the
real command boundary. Assertions cover both direct GitHub CLI delivery and
the harness-agnostic connector handoff, including the exact committed bundle.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

import pytest

from press import article, git, make_press, refuse_git_remote, write_agent_artifacts


def make_library(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    seed = tmp_path / "seed"
    origin = tmp_path / "origin.git"
    checkout = tmp_path / "library-checkout"
    seed.mkdir()
    git("init", "-q", "-b", "library", cwd=str(seed))
    git("config", "user.name", "Test Press", cwd=str(seed))
    git("config", "user.email", "test@example.com", cwd=str(seed))
    (seed / "library").mkdir()
    (seed / "library" / ".gitkeep").write_text("")
    git("add", "-A", cwd=str(seed))
    git("commit", "-qm", "library", cwd=str(seed))
    subprocess.run(["git", "clone", "-q", "--bare", str(seed), str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(checkout)], check=True)
    return checkout, origin


def make_workspace(tmp_path: pathlib.Path) -> pathlib.Path:
    workspace = tmp_path / "workspace"
    article_path = workspace / "library" / "semiconductors" / "micron.html"
    article_path.parent.mkdir(parents=True)
    article_path.write_text(article())
    write_agent_artifacts(str(workspace), "semiconductors", slug="micron")
    context = workspace / ".nb-context"
    context.mkdir()
    (context / "private.md").write_text("temporary authoring context\n")
    return article_path


def publish_article(library: pathlib.Path) -> None:
    git("config", "user.name", "Test Press", cwd=str(library))
    git("config", "user.email", "test@example.com", cwd=str(library))
    target = library / "library" / "semiconductors" / "micron.html"
    target.parent.mkdir(parents=True)
    target.write_text(article())
    write_agent_artifacts(str(library), "semiconductors", slug="micron")
    git("add", "library", "agent-artifacts", cwd=str(library))
    git("commit", "-qm", "publish micron", cwd=str(library))
    git("push", "-q", "origin", "library", cwd=str(library))


def run_prepare(
    article_path: pathlib.Path,
    *,
    library: pathlib.Path | None,
    main_root: pathlib.Path,
    path: str,
    gh_log: pathlib.Path | None = None,
    extra: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "NB_ROOT": str(main_root),
            "PATH": path,
            "PYTHONPATH": str(pathlib.Path(__file__).parents[1] / "engine"),
        }
    )
    if gh_log is not None:
        environment["FAKE_GH_LOG"] = str(gh_log)
    command = [
        sys.executable,
        str(pathlib.Path(__file__).parents[1] / "engine" / "nb" / "prepare_pr.py"),
        str(article_path),
        *(("--library", str(library)) if library is not None else ()),
        "--no-check-links",
        "--today",
        "2026-07-06",
        *extra,
    ]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=environment,
    )


def write_fake_gh(fake_bin: pathlib.Path) -> None:
    fake_bin.mkdir()
    script = fake_bin / "gh"
    script.write_text(
        """#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "$FAKE_GH_LOG"
case "$1:$2" in
  auth:status) exit 0 ;;
  repo:view) printf '%s\\n' 'example/nightly-build' ;;
  pr:list) exit 0 ;;
  pr:create) printf '%s\\n' 'https://github.com/example/nightly-build/pull/42' ;;
  *) printf 'unexpected gh call: %s\\n' "$*" >&2; exit 2 ;;
esac
"""
    )
    script.chmod(0o755)


def test_prepare_pr_pushes_exact_bundle_and_opens_pr(tmp_path: pathlib.Path) -> None:
    library, origin = make_library(tmp_path)
    article_path = make_workspace(tmp_path)
    main_root = pathlib.Path(make_press())
    fake_bin = tmp_path / "bin"
    log = tmp_path / "gh.log"
    log.write_text("")
    write_fake_gh(fake_bin)

    result = run_prepare(
        article_path,
        library=library,
        main_root=main_root,
        path=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        gh_log=log,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.rstrip().endswith(
        "https://github.com/example/nightly-build/pull/42"
    )
    branch = "refs/heads/nb/article/semiconductors/micron"
    changed = subprocess.run(
        [
            "git",
            f"--git-dir={origin}",
            "diff",
            "--name-only",
            "library",
            branch,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert "library/semiconductors/micron.html" in changed
    assert "agent-artifacts/semiconductors/micron/editorial-direction.md" in changed
    assert (
        "agent-artifacts/semiconductors/micron/editor/01/editorial-review.md" in changed
    )
    assert not any(path.startswith(".nb-context/") for path in changed)
    assert "pr create" in log.read_text()


def test_prepare_pr_hold_opens_a_draft(tmp_path: pathlib.Path) -> None:
    library, _origin = make_library(tmp_path)
    article_path = make_workspace(tmp_path)
    main_root = pathlib.Path(make_press())
    fake_bin = tmp_path / "bin"
    log = tmp_path / "gh.log"
    log.write_text("")
    write_fake_gh(fake_bin)

    result = run_prepare(
        article_path,
        library=library,
        main_root=main_root,
        path=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        gh_log=log,
        extra=("--hold",),
    )

    assert result.returncode == 0, result.stderr
    create = next(line for line in log.read_text().splitlines() if "pr create" in line)
    assert "--draft" in create


def test_prepare_pr_hold_handoff_names_the_draft(tmp_path: pathlib.Path) -> None:
    library, _origin = make_library(tmp_path)
    article_path = make_workspace(tmp_path)
    main_root = pathlib.Path(make_press())
    git_path = shutil.which("git")
    assert git_path is not None
    minimal_bin = tmp_path / "minimal-bin"
    minimal_bin.mkdir()
    (minimal_bin / "git").symlink_to(git_path)

    result = run_prepare(
        article_path,
        library=library,
        main_root=main_root,
        path=str(minimal_bin),
        extra=("--hold",),
    )

    assert result.returncode == 3, result.stderr
    assert "base=library\ndraft=true\n" in result.stdout


def test_prepare_pr_keeps_its_own_library_checkout(tmp_path: pathlib.Path) -> None:
    # no --library: the engine fetches origin/library under .nb-work/ itself
    _checkout, origin = make_library(tmp_path)
    article_path = make_workspace(tmp_path)
    main_root = pathlib.Path(make_press())
    git("init", "-q", "-b", "main", cwd=str(main_root))
    git("remote", "add", "origin", str(origin), cwd=str(main_root))
    fake_bin = tmp_path / "bin"
    log = tmp_path / "gh.log"
    log.write_text("")
    write_fake_gh(fake_bin)

    result = run_prepare(
        article_path,
        library=None,
        main_root=main_root,
        path=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        gh_log=log,
    )

    assert result.returncode == 0, result.stderr
    managed = main_root / ".nb-work" / "library"
    assert (managed / "library").is_dir()
    assert "pr create" in log.read_text()


def test_prepare_pr_prints_connector_handoff_without_gh(
    tmp_path: pathlib.Path,
) -> None:
    library, _origin = make_library(tmp_path)
    article_path = make_workspace(tmp_path)
    main_root = pathlib.Path(make_press())
    git_path = shutil.which("git")
    assert git_path is not None
    minimal_bin = tmp_path / "minimal-bin"
    minimal_bin.mkdir()
    (minimal_bin / "git").symlink_to(git_path)

    result = run_prepare(
        article_path,
        library=library,
        main_root=main_root,
        path=str(minimal_bin),
    )

    assert result.returncode == 3, result.stderr
    assert "NB_ARTICLE_PR_REQUIRED" in result.stdout
    assert "head=nb/article/semiconductors/micron" in result.stdout


def test_prepare_pr_safely_replaces_its_own_generated_branch(
    tmp_path: pathlib.Path,
) -> None:
    library, origin = make_library(tmp_path)
    article_path = make_workspace(tmp_path)
    main_root = pathlib.Path(make_press())
    fake_bin = tmp_path / "bin"
    log = tmp_path / "gh.log"
    log.write_text("")
    write_fake_gh(fake_bin)
    command_path = f"{fake_bin}{os.pathsep}{os.environ['PATH']}"

    first = run_prepare(
        article_path,
        library=library,
        main_root=main_root,
        path=command_path,
        gh_log=log,
    )
    branch = "refs/heads/nb/article/semiconductors/micron"
    first_commit = subprocess.run(
        ["git", f"--git-dir={origin}", "rev-parse", branch],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    article_path.write_text(article().replace("</body>", "<!-- revised --></body>"))

    second = run_prepare(
        article_path,
        library=library,
        main_root=main_root,
        path=command_path,
        gh_log=log,
    )
    second_commit = subprocess.run(
        ["git", f"--git-dir={origin}", "rev-parse", branch],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    count = subprocess.run(
        ["git", f"--git-dir={origin}", "rev-list", "--count", f"library..{branch}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert second_commit != first_commit
    assert count == "1"


def test_prepare_pr_preserves_an_unrecognized_remote_branch(
    tmp_path: pathlib.Path,
) -> None:
    library, origin = make_library(tmp_path)
    article_path = make_workspace(tmp_path)
    main_root = pathlib.Path(make_press())
    branch = "nb/article/semiconductors/micron"
    git("checkout", "-qb", branch, "origin/library", cwd=str(library))
    (library / "manual.txt").write_text("preserve this work\n")
    git("add", "manual.txt", cwd=str(library))
    git("config", "user.name", "Test Press", cwd=str(library))
    git("config", "user.email", "test@example.com", cwd=str(library))
    git("commit", "-qm", "manual branch", cwd=str(library))
    git("push", "-q", "origin", branch, cwd=str(library))
    before = subprocess.run(
        ["git", f"--git-dir={origin}", "rev-parse", f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    git("checkout", "-q", "library", cwd=str(library))

    result = run_prepare(
        article_path,
        library=library,
        main_root=main_root,
        path=os.environ["PATH"],
    )
    after = subprocess.run(
        ["git", f"--git-dir={origin}", "rev-parse", f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    assert result.returncode == 1
    assert "contains unrecognized edits" in result.stderr
    assert after == before


def test_normal_prepare_pr_rejects_an_already_published_article(
    tmp_path: pathlib.Path,
) -> None:
    library, _origin = make_library(tmp_path)
    article_path = make_workspace(tmp_path)
    publish_article(library)

    result = run_prepare(
        article_path,
        library=library,
        main_root=pathlib.Path(make_press()),
        path=os.environ["PATH"],
    )

    assert result.returncode == 1
    assert "article is already published" in result.stderr


@pytest.mark.parametrize("managed", [False, True])
def test_prepare_pr_hands_off_when_git_is_missing(tmp_path, *, managed) -> None:
    library, _origin = make_library(tmp_path)
    article_path = make_workspace(tmp_path)
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()

    result = run_prepare(
        article_path,
        library=None if managed else library,
        main_root=pathlib.Path(make_press()),
        path=str(empty_bin),
        extra=("--hold",),
    )

    assert result.returncode == 3
    assert "NB_GIT_REQUIRED" in result.stdout
    assert "NB_ARTICLE_PR_REQUIRED" not in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("operation", ["fetch", "ls-remote", "push"])
def test_prepare_pr_hands_off_failed_remote_operations(tmp_path, operation) -> None:
    library, _origin = make_library(tmp_path)
    article_path = make_workspace(tmp_path)
    fake_bin = tmp_path / "bin"
    refuse_git_remote(fake_bin, operation=operation)

    result = run_prepare(
        article_path,
        library=library,
        main_root=pathlib.Path(make_press()),
        path=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        extra=("--hold",),
    )

    assert result.returncode == 3, result.stderr
    assert "NB_GIT_REQUIRED" in result.stdout
    assert "remote access unavailable" in result.stdout
    assert f'"{operation}"' in result.stdout
    assert "NB_ARTICLE_PR_REQUIRED" not in result.stdout
