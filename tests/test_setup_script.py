"""Exercise first-time setup against a local Git remote.

Each run of scripts/setup.sh starts from a fresh fork. With the fake GitHub
CLI, setup must scaffold the press, create and seed the library branch, and
make the fork settings itself, never touching the Pages environment. Without a
signed-in CLI it must still do the git side and print the settings only an
admin can make.
"""

import json
import os
import pathlib
import shutil
import subprocess
from dataclasses import dataclass

from press import REPO
from test_sync_script import WORKFLOWS, configure_author, git, write_fake_gh


@dataclass(frozen=True)
class SetupRepo:
    checkout: pathlib.Path
    origin: pathlib.Path
    gh_log: pathlib.Path
    fake_bin: pathlib.Path

    def run(self, *, gh_mode: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "FAKE_GH_LOG": str(self.gh_log),
                "FAKE_GH_MODE": gh_mode,
                "FAKE_ORIGIN": str(self.origin),
                "PATH": f"{self.fake_bin}{os.pathsep}{env['PATH']}",
                "UV_PROJECT_ENVIRONMENT": str(REPO / ".venv"),
            }
        )
        return subprocess.run(
            [str(self.checkout / "scripts" / "setup.sh")],
            cwd=self.checkout,
            env=env,
            capture_output=True,
            text=True,
        )

    def main_files(self) -> set[str]:
        listing = subprocess.run(
            ["git", f"--git-dir={self.origin}", "ls-tree", "-r", "--name-only", "main"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return set(listing.split())

    def library_files(self) -> set[str]:
        listing = subprocess.run(
            [
                "git",
                f"--git-dir={self.origin}",
                "ls-tree",
                "-r",
                "--name-only",
                "library",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return set(listing.split())


def make_setup_repo(tmp_path: pathlib.Path) -> SetupRepo:
    source = tmp_path / "source"
    origin = tmp_path / "origin.git"
    checkout = tmp_path / "checkout"
    (source / "scripts").mkdir(parents=True)
    (source / ".github" / "workflows").mkdir(parents=True)
    for name in ("nb", "pyproject.toml", "uv.lock"):
        shutil.copy2(REPO / name, source / name)
    for name in ("setup.sh", "sync.sh"):
        shutil.copy2(REPO / "scripts" / name, source / "scripts" / name)
    for name in ("engine", "templates", "spec"):
        shutil.copytree(REPO / name, source / name)
    for path in WORKFLOWS:
        (source / path).write_text((REPO / path).read_text())
    git(source, "init", "-q", "-b", "main")
    configure_author(source)
    git(source, "add", "-A")
    git(source, "commit", "-qm", "engine")
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(source), str(origin)], check=True
    )
    subprocess.run(["git", "clone", "-q", str(origin), str(checkout)], check=True)
    configure_author(checkout)
    fake_bin = tmp_path / "bin"
    gh_log = tmp_path / "gh.log"
    gh_log.write_text("")
    write_fake_gh(fake_bin)
    return SetupRepo(checkout, origin, gh_log, fake_bin)


def test_setup_without_gh_seeds_library_and_prints_the_clicks(
    tmp_path: pathlib.Path,
) -> None:
    repo = make_setup_repo(tmp_path)

    result = repo.run(gh_mode="unauthenticated")

    assert result.returncode == 0, result.stderr + result.stdout
    assert {"library/.gitkeep", *WORKFLOWS} <= repo.library_files()
    assert "Still to do" in result.stdout
    assert "The presses are ready" not in result.stdout
    assert "press/series/dispatches/series.yaml" in repo.main_files()
    assert "settings/pages" in result.stdout
    assert "/actions" in result.stdout
    assert "settings/branches" in result.stdout
    assert "auto-merge" not in result.stdout
    assert "api" not in repo.gh_log.read_text()


def test_setup_scaffolds_the_default_paper(tmp_path: pathlib.Path) -> None:
    repo = make_setup_repo(tmp_path)

    result = repo.run(gh_mode="available")

    assert result.returncode == 0, result.stderr + result.stdout
    series = repo.checkout / "press" / "series"
    assert "cadence: manual" in (series / "dispatches" / "series.yaml").read_text()
    news_brief = (series / "news-brief" / "series.yaml").read_text()
    assert "mode: rolling" in news_brief and "cadence: daily" in news_brief
    feature = (series / "feature" / "series.yaml").read_text()
    assert "templates: [article, paper]" in feature and "cadence: daily" in feature
    for name in ("dispatches", "news-brief", "feature"):
        assert (series / name / "prompt.md").read_text().strip()
        assert f"press/series/{name}/prompt.md" in repo.main_files()
    assert (
        "Ask your agent" not in (repo.checkout / "press" / "editorial.md").read_text()
    )
    assert "Ask for an article" in result.stdout
    assert "pushed to main" in result.stdout


def test_scaffolded_paper_has_daily_work_and_dispatches_never_does(
    tmp_path: pathlib.Path,
) -> None:
    repo = make_setup_repo(tmp_path)
    result = repo.run(gh_mode="available")
    assert result.returncode == 0, result.stderr + result.stdout

    duty = subprocess.run(
        [str(repo.checkout / "nb"), "duty", "--repo", str(repo.checkout)],
        capture_output=True,
        text=True,
        env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(REPO / ".venv")},
    )

    assert duty.returncode == 0, duty.stderr + duty.stdout
    report = json.loads(duty.stdout)
    assert {entry["series"] for entry in report["due"]} == {"news-brief", "feature"}
    assert {entry["series"] for entry in report["idle"]} == {"dispatches"}


def test_setup_hands_off_a_refused_scaffold_push(tmp_path: pathlib.Path) -> None:
    # origin's main moves on before setup pushes, so the push is not a fast-forward
    repo = make_setup_repo(tmp_path)
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(repo.origin), str(other)], check=True)
    configure_author(other)
    (other / "note.txt").write_text("someone else pushed first\n")
    git(other, "add", "note.txt")
    git(other, "commit", "-qm", "unrelated change on main")
    git(other, "push", "-q", "origin", "main")

    result = repo.run(gh_mode="available")

    assert result.returncode == 3, result.stderr + result.stdout
    assert "press/series/dispatches/series.yaml" not in repo.main_files()
    assert "NB_GIT_REQUIRED" in result.stderr
    assert "argument=push" in result.stderr
    assert "argument=main" in result.stderr


def test_setup_with_gh_makes_the_settings_and_skips_the_environment(
    tmp_path: pathlib.Path,
) -> None:
    repo = make_setup_repo(tmp_path)

    result = repo.run(gh_mode="available")

    assert result.returncode == 0, result.stderr + result.stdout
    assert {"library/.gitkeep", *WORKFLOWS} <= repo.library_files()
    assert "The presses are ready" in result.stdout
    assert "Still to do" not in result.stdout
    calls = repo.gh_log.read_text()
    assert "repos/example/nightly-build/pages" in calls
    assert "actions/permissions" in calls
    assert "branches/library/protection" in calls
    assert "allow_auto_merge" in calls
    assert "environments/github-pages" not in calls


def test_setup_is_idempotent_over_a_healthy_fork(tmp_path: pathlib.Path) -> None:
    repo = make_setup_repo(tmp_path)
    first = repo.run(gh_mode="available")
    assert first.returncode == 0, first.stderr + first.stdout

    second = repo.run(gh_mode="available")

    assert second.returncode == 0, second.stderr + second.stdout
    assert "library branch already exists" in second.stdout


def test_setup_failed_branch_query_never_creates_library(tmp_path) -> None:
    from press import refuse_git_remote

    repo = make_setup_repo(tmp_path)
    refuse_git_remote(repo.fake_bin, operation="ls-remote")

    result = repo.run(gh_mode="available")

    assert result.returncode == 3, result.stderr
    assert "NB_GIT_REQUIRED" in result.stderr
    assert "creating orphan library branch" not in result.stdout
    assert (
        subprocess.run(
            [
                "git",
                f"--git-dir={repo.origin}",
                "show-ref",
                "--verify",
                "refs/heads/library",
            ],
            capture_output=True,
        ).returncode
        != 0
    )
