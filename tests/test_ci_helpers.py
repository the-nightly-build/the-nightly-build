"""The facts the workflow reads: whether to auto-merge, and what the PR published.

The trigger tests are the fork-token guarantee. The editor auto-merges article
PRs, so the only thing stopping a stranger from force-publishing to a fork is
GitHub's rule that a pull_request run from a fork gets a read-only token. That
holds only while check.yml uses `pull_request`; `pull_request_target` would hand
fork PRs a writable token and break it.
"""

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
    ci_helper: Callable[[str, str], str], series_yaml: str, expected: str
) -> None:
    assert ci_helper("autopublish", series_yaml) == expected


def test_article_path_prints_the_prs_one_added_article(
    ci_helper: Callable[[str, str], str],
) -> None:
    assert ci_helper("article-path", "autopublish: true\n") == "library/foo/story.html"


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
