"""The facts the workflow reads: whether a PR is new, and what it publishes.

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

import yaml

from press import REPO, git


def test_new_articles_are_always_classified_for_auto_merge(
    ci_helper: Callable[[str, str], str],
) -> None:
    assert ci_helper("new-article", "mode: rolling\n") == "true"


def test_article_path_prints_the_prs_one_added_article(
    ci_helper: Callable[[str, str], str],
) -> None:
    assert ci_helper("article-path", "mode: rolling\n") == "library/foo/story.html"


def revision_ci_helper(tmp_path: pathlib.Path, command: str) -> str:
    repo = tmp_path / "revision-ci"
    series = repo / "press" / "series" / "foo"
    article_path = repo / "library" / "foo" / "story.html"
    series.mkdir(parents=True)
    article_path.parent.mkdir(parents=True)
    (series / "series.yaml").write_text("mode: rolling\n")
    article_path.write_text("<html>published</html>\n")
    git("init", "-q", "-b", "library", cwd=str(repo))
    git("config", "user.email", "t@t", cwd=str(repo))
    git("config", "user.name", "t", cwd=str(repo))
    git("add", "-A", cwd=str(repo))
    git("commit", "-qm", "published", cwd=str(repo))
    git("checkout", "-qb", "revision", cwd=str(repo))
    article_path.write_text("<html>revised</html>\n")
    revisions = repo / "agent-artifacts" / "foo" / "story" / "revisions"
    revisions.mkdir(parents=True)
    (revisions / "01.md").write_text("# Revision\n\nCorrect the article.\n")
    git("add", "-A", cwd=str(repo))
    git("commit", "-qm", "revision", cwd=str(repo))
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


def test_revisions_are_not_classified_as_new_articles(tmp_path: pathlib.Path) -> None:
    assert revision_ci_helper(tmp_path, "new-article") == "false"


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

    git("init", "-q", "-b", "library", cwd=str(checkout))
    git("config", "user.email", "t@t", cwd=str(checkout))
    git("config", "user.name", "t", cwd=str(checkout))
    (checkout / ".gitkeep").write_text("")
    git("add", "-A", cwd=str(checkout))
    git("commit", "-qm", "library", cwd=str(checkout))
    git("checkout", "-qb", "sync", cwd=str(checkout))
    proposed = {".github/workflows/check.yml": workflows[".github/workflows/check.yml"]}
    if not only_check:
        proposed = workflows
    for path, content in proposed.items():
        target = checkout / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    if extra_file:
        (checkout / "unexpected.txt").write_text("extra\n")
    git("add", "-A", cwd=str(checkout))
    git("commit", "-qm", "sync", cwd=str(checkout))

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
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "check.yml").read_text())
    # PyYAML parses the bare key `on` as the boolean True (YAML 1.1); accept either.
    triggers = workflow.get("on", workflow.get(True)) or {}
    return set(triggers) if isinstance(triggers, dict) else {triggers}


def test_check_yml_triggers_on_pull_request() -> None:
    assert "pull_request" in check_yml_triggers()


def test_check_yml_never_uses_pull_request_target() -> None:
    assert "pull_request_target" not in check_yml_triggers()


def test_check_yml_routes_exact_syncs_to_the_protected_merge_job() -> None:
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "check.yml").read_text())
    validate = workflow["jobs"]["validate"]
    automerge = workflow["jobs"]["automerge"]

    assert "sync" in validate["outputs"]
    assert "needs.validate.outputs.sync == 'true'" in automerge["if"]


def test_check_yml_automerges_every_valid_new_article() -> None:
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "check.yml").read_text())
    validate = workflow["jobs"]["validate"]
    automerge = workflow["jobs"]["automerge"]

    assert "new_article" in validate["outputs"]
    assert "needs.validate.outputs.new_article == 'true'" in automerge["if"]


def test_canonical_workflows_use_the_checkout_owned_command() -> None:
    for name in ("check.yml", "publish.yml"):
        workflow = (REPO / ".github" / "workflows" / name).read_text()
        assert "_main/nb" in workflow
        assert "_main/engine/" not in workflow
        assert "pip install" not in workflow
        assert "uv pip" not in workflow
