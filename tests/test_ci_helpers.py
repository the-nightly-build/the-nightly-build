"""The facts the workflow reads: whether to auto-merge, and what the PR published.

The trigger tests are the fork-token guarantee. The editor auto-merges article
PRs, so the only thing stopping a stranger from force-publishing to a fork is
GitHub's rule that a pull_request run from a fork gets a read-only token. That
holds only while check.yml uses `pull_request`; `pull_request_target` would hand
fork PRs a writable token and break it.
"""

import pathlib
import subprocess
import sys
from collections.abc import Callable

import pytest
import yaml

from press import REPO


@pytest.mark.parametrize(
    ("series_yaml", "expected"),
    [
        pytest.param("autopublish: true\n", "true", id="true-enables-auto-merge"),
        pytest.param("autopublish: false\n", "false", id="false-disables-it"),
        pytest.param("mode: rolling\n", "false", id="absent-disables-it"),
        pytest.param("autopublish: 'false'\n", "false", id="string-false"),
        pytest.param("autopublish: 'true'\n", "false", id="string-true"),
        pytest.param("autopublish: 1\n", "false", id="int-one"),
    ],
)
def test_only_a_real_boolean_true_auto_merges(
    *, ci_helper: Callable[[str, str], str], series_yaml: str, expected: str
) -> None:
    assert ci_helper("autopublish", series_yaml) == expected


def test_article_path_prints_the_prs_one_added_article(
    ci_helper: Callable[[str, str], str],
) -> None:
    assert ci_helper("article-path", "autopublish: true\n") == "library/foo/story.html"


def revision_ci_helper(tmp_path: pathlib.Path, command: str) -> str:
    repo = tmp_path / "revision-ci"
    series = repo / "press" / "series" / "foo"
    article_path = repo / "library" / "foo" / "story.html"
    series.mkdir(parents=True)
    article_path.parent.mkdir(parents=True)
    (series / "series.yaml").write_text("autopublish: true\n")
    article_path.write_text("<html>published</html>\n")
    subprocess.run(["git", "init", "-q", "-b", "library"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "published"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "-qb", "revision"], cwd=repo, check=True)
    article_path.write_text("<html>revised</html>\n")
    revisions = repo / "agent-artifacts" / "foo" / "story" / "revisions"
    revisions.mkdir(parents=True)
    (revisions / "01.md").write_text("# Revision\n\nCorrect the article.\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "revision"], cwd=repo, check=True)
    return subprocess.run(
        [
            sys.executable,
            str(REPO / "engine" / "ci_helpers.py"),
            command,
            "--repo",
            str(repo),
            "--diff-base",
            "library",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_article_path_includes_a_revised_article(tmp_path: pathlib.Path) -> None:
    assert revision_ci_helper(tmp_path, "article-path") == "library/foo/story.html"


def test_revisions_never_autopublish(tmp_path: pathlib.Path) -> None:
    assert revision_ci_helper(tmp_path, "autopublish") == "false"


def run_sync_helper(
    tmp_path: pathlib.Path,
    *,
    extra_file: bool = False,
    only_check: bool = False,
) -> str:
    canonical = tmp_path / "canonical"
    checkout = tmp_path / "checkout"
    canonical.mkdir()
    checkout.mkdir()
    workflows = {
        ".github/workflows/check.yml": "name: check\n",
        ".github/workflows/publish.yml": "name: publish\n",
    }
    for path, content in workflows.items():
        target = canonical / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    subprocess.run(["git", "init", "-q", "-b", "library"], cwd=checkout, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=checkout, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=checkout, check=True)
    (checkout / ".gitkeep").write_text("")
    subprocess.run(["git", "add", "-A"], cwd=checkout, check=True)
    subprocess.run(["git", "commit", "-qm", "library"], cwd=checkout, check=True)
    subprocess.run(["git", "checkout", "-qb", "sync"], cwd=checkout, check=True)
    proposed = {".github/workflows/check.yml": workflows[".github/workflows/check.yml"]}
    if not only_check:
        proposed = workflows
    for path, content in proposed.items():
        target = checkout / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    if extra_file:
        (checkout / "unexpected.txt").write_text("extra\n")
    subprocess.run(["git", "add", "-A"], cwd=checkout, check=True)
    subprocess.run(["git", "commit", "-qm", "sync"], cwd=checkout, check=True)

    return subprocess.run(
        [
            sys.executable,
            str(REPO / "engine" / "ci_helpers.py"),
            "sync",
            "--repo",
            str(canonical),
            "--diff-base",
            "library",
        ],
        cwd=checkout,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_sync_requires_both_exact_workflow_blobs(tmp_path: pathlib.Path) -> None:
    assert run_sync_helper(tmp_path) == "true"


def test_sync_rejects_other_files(tmp_path: pathlib.Path) -> None:
    assert run_sync_helper(tmp_path, extra_file=True) == "false"


def test_sync_accepts_one_stale_canonical_workflow(tmp_path: pathlib.Path) -> None:
    assert run_sync_helper(tmp_path, only_check=True) == "true"


def check_yml_triggers() -> set[str]:
    workflow = yaml.safe_load(
        (REPO / ".github" / "workflows" / "check.yml").read_text()
    )
    # PyYAML parses the bare key `on` as the boolean True (YAML 1.1); accept either.
    triggers = workflow.get("on", workflow.get(True)) or {}
    return set(triggers) if isinstance(triggers, dict) else {triggers}


def test_check_yml_triggers_on_pull_request() -> None:
    assert "pull_request" in check_yml_triggers()


def test_check_yml_never_uses_pull_request_target() -> None:
    assert "pull_request_target" not in check_yml_triggers()


def test_check_yml_routes_exact_syncs_to_the_protected_merge_job() -> None:
    workflow = yaml.safe_load(
        (REPO / ".github" / "workflows" / "check.yml").read_text()
    )
    validate = workflow["jobs"]["validate"]
    automerge = workflow["jobs"]["automerge"]

    assert "sync" in validate["outputs"]
    assert "needs.validate.outputs.sync == 'true'" in automerge["if"]


def test_canonical_workflows_use_the_checkout_owned_command() -> None:
    for name in ("check.yml", "publish.yml"):
        workflow = (REPO / ".github" / "workflows" / name).read_text()
        assert "_main/nb" in workflow
        assert "_main/engine/" not in workflow
        assert "pip install" not in workflow
        assert "uv pip" not in workflow
