"""Exercise recurring workflow synchronization against local Git remotes.

The fake GitHub CLI preserves the command boundary while making protected
auto-merge deterministic: its merge command advances the bare library ref as
GitHub would after validation. Separate origin and upstream remotes make any
accidental upstream access, premature library write, or unsafe branch rewrite
observable without network access.
"""

import os
import pathlib
import shutil
import subprocess
from dataclasses import dataclass
from typing import Literal

from press import REPO

SYNC_BRANCH = "nb/sync-library-workflows"
WORKFLOWS = (
    ".github/workflows/check.yml",
    ".github/workflows/publish.yml",
)


def git(cwd: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def configure_author(repo: pathlib.Path) -> None:
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test Press")


@dataclass(frozen=True)
class SyncRepo:
    checkout: pathlib.Path
    origin: pathlib.Path
    upstream: pathlib.Path
    gh_log: pathlib.Path
    fake_bin: pathlib.Path

    def run(
        self,
        *args: str,
        check_failure: bool = False,
        gh_mode: Literal[
            "available", "unauthenticated", "repo-unavailable", "protection-unavailable"
        ] = "available",
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "FAKE_GH_LOG": str(self.gh_log),
                "FAKE_GH_MODE": gh_mode,
                "FAKE_ORIGIN": str(self.origin),
                "NB_SYNC_MAX_POLLS": "2",
                "NB_SYNC_POLL_SECONDS": "0",
                "PATH": f"{self.fake_bin}{os.pathsep}{env['PATH']}",
            }
        )
        if check_failure:
            env["FAKE_CHECK_FAILURE"] = "1"
        return subprocess.run(
            [str(self.checkout / "scripts" / "sync.sh"), *args],
            cwd=self.checkout,
            env=env,
            capture_output=True,
            text=True,
        )

    def remote_ref(self, ref: str) -> str:
        return subprocess.run(
            ["git", f"--git-dir={self.origin}", "rev-parse", ref],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def remote_blob(self, ref: str, path: str) -> str:
        return subprocess.run(
            ["git", f"--git-dir={self.origin}", "show", f"{ref}:{path}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def update_remote_ref(self, ref: str, target: str) -> None:
        subprocess.run(
            ["git", f"--git-dir={self.origin}", "update-ref", ref, target],
            check=True,
        )


def write_fake_gh(fake_bin: pathlib.Path) -> None:
    fake_bin.mkdir()
    script = fake_bin / "gh"
    script.write_text(
        """#!/usr/bin/env sh
set -eu
printf '%s\\n' "$*" >> "$FAKE_GH_LOG"
case "${FAKE_GH_MODE:-available}:$1:$2" in
  unauthenticated:auth:status) exit 1 ;;
  repo-unavailable:repo:view) exit 1 ;;
  protection-unavailable:api:*) exit 1 ;;
esac
case "$1:$2" in
  auth:status) exit 0 ;;
  repo:view) printf '%s\\n' 'example/nightly-build' ;;
  api:*) printf '%s\\n' 'validate' ;;
  pr:list) exit 0 ;;
  pr:create) printf '%s\\n' 'https://github.com/example/nightly-build/pull/42' ;;
  pr:edit) exit 0 ;;
  pr:merge)
    [ "${FAKE_CHECK_FAILURE:-}" = 1 ] && exit 0
    sync=$(git --git-dir="$FAKE_ORIGIN" rev-parse refs/heads/nb/sync-library-workflows)
    git --git-dir="$FAKE_ORIGIN" update-ref refs/heads/library "$sync"
    ;;
  pr:view) printf '%s\\n' 'MERGED' ;;
  pr:checks)
    [ "${FAKE_CHECK_FAILURE:-}" = 1 ] && printf '%s\n' 'validate: https://example.test/check'
    ;;
  *) printf 'unexpected fake gh invocation: %s\\n' "$*" >&2; exit 2 ;;
esac
"""
    )
    script.chmod(0o755)


def make_sync_repo(
    tmp_path: pathlib.Path, *, drift: Literal["none", "both", "check"]
) -> SyncRepo:
    source = tmp_path / "source"
    origin = tmp_path / "origin.git"
    upstream = tmp_path / "upstream.git"
    maintainer = tmp_path / "maintainer"
    upstream_work = tmp_path / "upstream-work"
    checkout = tmp_path / "checkout"
    source.mkdir()
    (source / "scripts").mkdir()
    (source / ".github" / "workflows").mkdir(parents=True)
    shutil.copy2(REPO / "scripts" / "sync.sh", source / "scripts" / "sync.sh")
    shutil.copytree(REPO / "engine", source / "engine")
    for path in WORKFLOWS:
        target = source / path
        target.write_text((REPO / path).read_text())
    (source / "shared.txt").write_text("base\n")
    git(source, "init", "-q", "-b", "main")
    configure_author(source)
    git(source, "add", "-A")
    git(source, "commit", "-qm", "base engine")
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(source), str(origin)], check=True
    )
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(source), str(upstream)], check=True
    )

    subprocess.run(["git", "clone", "-q", str(origin), str(maintainer)], check=True)
    configure_author(maintainer)
    (maintainer / "shared.txt").write_text("fork\n")
    git(maintainer, "add", "shared.txt")
    git(maintainer, "commit", "-qm", "fork change")
    git(maintainer, "push", "-q", "origin", "main")

    subprocess.run(
        ["git", "clone", "-q", str(upstream), str(upstream_work)], check=True
    )
    configure_author(upstream_work)
    (upstream_work / "shared.txt").write_text("upstream\n")
    git(upstream_work, "add", "shared.txt")
    git(upstream_work, "commit", "-qm", "upstream change")
    git(upstream_work, "push", "-q", "origin", "main")

    git(maintainer, "checkout", "-q", "--orphan", "library")
    for entry in maintainer.iterdir():
        if entry.name != ".git":
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
    (maintainer / ".github" / "workflows").mkdir(parents=True)
    (maintainer / "library").mkdir()
    (maintainer / "library" / ".gitkeep").write_text("")
    for path in WORKFLOWS:
        stale = drift == "both" or (
            drift == "check" and path == ".github/workflows/check.yml"
        )
        content = "name: stale\n" if stale else (REPO / path).read_text()
        (maintainer / path).write_text(content)
    git(maintainer, "add", "-A")
    git(maintainer, "commit", "-qm", "library")
    git(maintainer, "push", "-q", "origin", "library")

    subprocess.run(["git", "clone", "-q", str(origin), str(checkout)], check=True)
    configure_author(checkout)
    git(checkout, "remote", "add", "upstream", str(upstream))
    fake_bin = tmp_path / "bin"
    gh_log = tmp_path / "gh.log"
    gh_log.write_text("")
    write_fake_gh(fake_bin)
    return SyncRepo(checkout, origin, upstream, gh_log, fake_bin)


def test_default_sync_is_idempotent_and_never_fetches_upstream(
    tmp_path: pathlib.Path,
) -> None:
    repo = make_sync_repo(tmp_path, drift="none")

    first = repo.run()
    second = repo.run()

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert "pr create" not in repo.gh_log.read_text()


def test_current_workflows_do_not_require_gh(tmp_path: pathlib.Path) -> None:
    repo = make_sync_repo(tmp_path, drift="none")

    result = repo.run(gh_mode="unauthenticated")

    assert result.returncode == 0, result.stderr
    assert repo.gh_log.read_text() == ""


def test_drift_opens_a_protected_pr_and_verifies_library(
    tmp_path: pathlib.Path,
) -> None:
    repo = make_sync_repo(tmp_path, drift="both")

    result = repo.run()

    assert result.returncode == 0, result.stderr
    for path in WORKFLOWS:
        assert repo.remote_blob("main", path) == repo.remote_blob("library", path)
    calls = repo.gh_log.read_text()
    assert "pr create" in calls
    assert "pr merge 42" in calls
    assert "--auto --squash" in calls


def test_one_stale_workflow_self_heals(tmp_path: pathlib.Path) -> None:
    repo = make_sync_repo(tmp_path, drift="check")

    result = repo.run()

    assert result.returncode == 0, result.stderr
    for path in WORKFLOWS:
        assert repo.remote_blob("main", path) == repo.remote_blob("library", path)


def test_unauthenticated_gh_prepares_an_agent_handoff(
    tmp_path: pathlib.Path,
) -> None:
    repo = make_sync_repo(tmp_path, drift="both")
    library_before = repo.remote_ref("refs/heads/library")

    result = repo.run(gh_mode="unauthenticated")

    assert result.returncode == 3
    assert repo.remote_ref("refs/heads/library") == library_before
    for path in WORKFLOWS:
        assert repo.remote_blob("main", path) == repo.remote_blob(SYNC_BRANCH, path)
    assert "NB_SYNC_PR_REQUIRED" in result.stdout
    assert "reason=gh is not authenticated" in result.stdout
    assert "base=library" in result.stdout
    assert f"head={SYNC_BRANCH}" in result.stdout
    assert "Wait for the `validate` check" in result.stdout
    assert "Rerun `scripts/sync.sh`" in result.stdout
    assert "pr create" not in repo.gh_log.read_text()

    repo.update_remote_ref("refs/heads/library", f"refs/heads/{SYNC_BRANCH}")
    verified = repo.run(gh_mode="unauthenticated")

    assert verified.returncode == 0, verified.stderr
    assert "library workflows already match origin/main" in verified.stdout
    assert repo.gh_log.read_text().count("auth status") == 1


def test_repo_discovery_failure_uses_the_agent_handoff(
    tmp_path: pathlib.Path,
) -> None:
    repo = make_sync_repo(tmp_path, drift="both")

    result = repo.run(gh_mode="repo-unavailable")

    assert result.returncode == 3
    assert "reason=gh cannot resolve the origin repository" in result.stdout
    assert "pr list" not in repo.gh_log.read_text()


def test_protection_api_failure_uses_the_agent_handoff(
    tmp_path: pathlib.Path,
) -> None:
    repo = make_sync_repo(tmp_path, drift="both")

    result = repo.run(gh_mode="protection-unavailable")

    assert result.returncode == 3
    assert "reason=gh cannot read library branch protection" in result.stdout
    assert "repository=example/nightly-build" in result.stdout
    assert "pr list" not in repo.gh_log.read_text()


def test_sync_refuses_to_overwrite_an_unrecognized_remote_branch(
    tmp_path: pathlib.Path,
) -> None:
    repo = make_sync_repo(tmp_path, drift="both")
    git(repo.checkout, "fetch", "-q", "origin", "library")
    git(repo.checkout, "checkout", "-qb", SYNC_BRANCH, "origin/library")
    for path in WORKFLOWS:
        target = repo.checkout / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((REPO / path).read_text())
    (repo.checkout / "manual.txt").write_text("keep me\n")
    git(repo.checkout, "add", "-A")
    git(repo.checkout, "commit", "-qm", "manual sync work")
    git(repo.checkout, "push", "-q", "origin", SYNC_BRANCH)
    before = repo.remote_ref(f"refs/heads/{SYNC_BRANCH}")
    git(repo.checkout, "checkout", "-q", "main")

    result = repo.run()

    assert result.returncode != 0
    assert "unrecognized edits" in result.stderr
    assert repo.remote_ref(f"refs/heads/{SYNC_BRANCH}") == before
    assert "pr create" not in repo.gh_log.read_text()


def test_upstream_conflict_stops_before_library_sync(tmp_path: pathlib.Path) -> None:
    repo = make_sync_repo(tmp_path, drift="both")
    library_before = repo.remote_ref("refs/heads/library")

    result = repo.run("--update-main-from-upstream")

    assert result.returncode != 0
    assert "shared.txt" in result.stderr
    assert repo.remote_ref("refs/heads/library") == library_before
    assert "pr create" not in repo.gh_log.read_text()


def test_failed_sync_reports_the_check_and_repair_path(tmp_path: pathlib.Path) -> None:
    repo = make_sync_repo(tmp_path, drift="both")

    result = repo.run(check_failure=True)

    assert result.returncode != 0
    assert "validate: https://example.test/check" in result.stderr
    assert "Fix the canonical engine on main" in result.stderr
    assert repo.remote_blob("library", WORKFLOWS[0]) != repo.remote_blob(
        "main", WORKFLOWS[0]
    )
