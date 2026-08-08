"""One command gives an article team exact, current authoring context.

The fixtures exercise both shipped and press-shadowed templates, verbatim
editorial layers, ordered tag fragments, runtime assets, and safe refusal.
Together they document the complete deterministic side of article setup.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from nb.artifacts import validate_artifacts
from nb.start_article import StartArticleError, initialize


def test_configured_item_starts_from_exact_template_and_direction(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    series = repo / "press/series/semiconductors/series.yaml"
    series.write_text(series.read_text() + "\nbands:\n  words: [1200, 2400]\n")
    workspace = tmp_path / "article"

    article = initialize(
        repo=repo,
        workspace=workspace,
        series_id="semiconductors",
        slug="micron",
        template_id="article",
    )

    assert (
        article.read_bytes() == (repo / "templates/article/skeleton.html").read_bytes()
    )
    contract = yaml.safe_load(
        (workspace / ".nb-context/template-contract.yaml").read_text()
    )
    assert contract["template"] == "article"
    assert contract["bands"]["words"] == [1200, 2400]
    direction = (
        workspace / "agent-artifacts/semiconductors/micron/editorial-direction.md"
    ).read_text()
    ordered = [
        direction.index("## 1. House editorial standard"),
        direction.index("## 2. Slop standard"),
        direction.index("## 3. Headline standard"),
        direction.index("Template identity"),
        direction.index("Series direction"),
        direction.index("Tag: equity"),
        direction.index("Selected item"),
    ]
    assert ordered == sorted(ordered)
    assert "Deep dives on the semiconductor supply chain." in direction
    assert "Frame companies for a public-market reader." in direction
    assert "prompt: Emphasize the HBM supply-agreement structure" in direction
    assert (workspace / ".nb-context/furniture/engine.md").read_bytes() == (
        repo / "templates/FURNITURE.md"
    ).read_bytes()
    assert not (workspace / ".nb-context/furniture/press.md").exists()
    assert yaml.safe_load(
        (workspace / ".nb-context/runtime-assets.yaml").read_text()
    ) == {"assets": {}}


def test_press_template_and_authoring_extensions_resolve_without_parsing(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    custom = repo / "press/templates/article"
    custom.mkdir(parents=True)
    (custom / "manifest.yaml").write_text(
        "about: custom\nclass: longread\nbands:\n  words: [1000, 2000]\n"
        "sections: [orientation, sources]\ncite_rule: per-section\n"
    )
    (custom / "skeleton.html").write_text("<html>PRESS SKELETON</html>\n")
    (custom / "identity.md").write_text("# Press identity\n\nUse this shape.\n")
    (custom / "furniture.md").write_text("# Template tool\n\nExact markup.\n")
    (custom / "furniture.css").write_text(".template-tool { color: red; }\n")
    shared = repo / "press/furniture"
    shared.mkdir()
    (shared / "catalog.md").write_text("# Shared tool\n\nShared exact markup.\n")
    (shared / "styles.css").write_text(".shared-tool { color: blue; }\n")
    (repo / "press/site.yaml").write_text(
        "title: Test\ntheme: engine/assets/themes/newspaper.css\n"
        "assets:\n  scripts:\n    - url: https://example.org/tool.js\n"
        "      integrity: sha384-example\n"
    )
    workspace = tmp_path / "article"

    article = initialize(
        repo=repo,
        workspace=workspace,
        series_id="semiconductors",
        slug="micron",
        template_id="article",
    )

    assert article.read_text() == "<html>PRESS SKELETON</html>\n"
    assert (
        (workspace / ".nb-context/furniture/press.md")
        .read_text()
        .startswith("# Shared tool")
    )
    assert (
        (workspace / ".nb-context/furniture/template.md")
        .read_text()
        .startswith("# Template tool")
    )
    assert not tuple((workspace / ".nb-context").rglob("*.css"))
    direction = (
        workspace / "agent-artifacts/semiconductors/micron/editorial-direction.md"
    ).read_text()
    assert "# Press identity" in direction
    assets = yaml.safe_load((workspace / ".nb-context/runtime-assets.yaml").read_text())
    assert assets["assets"]["scripts"][0]["url"] == "https://example.org/tool.js"


def test_open_article_keeps_requested_tag_order(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    series = repo / "press/series/wildcard"
    series.mkdir()
    (series / "series.yaml").write_text(
        "name: Wildcard\nmode: open\ntemplate: article\nprompt: prompt.md\n"
        "tags:\n  first: ../_tags/first.md\n  second: ../_tags/second.md\n"
    )
    (series / "prompt.md").write_text("Choose a new subject.\n")
    tags = repo / "press/series/_tags"
    (tags / "first.md").write_text("First direction.\n")
    (tags / "second.md").write_text("Second direction.\n")

    initialize(
        repo=repo,
        workspace=tmp_path / "article",
        series_id="wildcard",
        slug="new-subject",
        template_id="article",
        tags=("second", "first"),
    )

    direction = (
        tmp_path / "article/agent-artifacts/wildcard/new-subject/editorial-direction.md"
    ).read_text()
    assert direction.index("Tag: second") < direction.index("Tag: first")
    assert "Selected item" not in direction


def test_manual_open_article_requires_a_configured_commission(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    series = repo / "press/series/wildcard"
    series.mkdir()
    (series / "series.yaml").write_text(
        "name: Wildcard\nmode: open\ncadence: manual\ntemplate: article\n"
        "prompt: prompt.md\n"
    )
    (series / "prompt.md").write_text("Choose a new subject.\n")

    with pytest.raises(StartArticleError, match="has no item 'birds'"):
        initialize(
            repo=repo,
            workspace=tmp_path / "article",
            series_id="wildcard",
            slug="birds",
            template_id="article",
        )


def test_manual_open_article_accepts_a_configured_commission(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    series = repo / "press/series/wildcard"
    series.mkdir()
    (series / "series.yaml").write_text(
        "name: Wildcard\nmode: open\ncadence: manual\ntemplate: article\n"
        "prompt: prompt.md\nitems:\n  - slug: birds\n    prompt: Cover birds.\n"
    )
    (series / "prompt.md").write_text("Choose a new subject.\n")

    article = initialize(
        repo=repo,
        workspace=tmp_path / "article",
        series_id="wildcard",
        slug="birds",
        template_id="article",
    )

    assert article.exists()
    assert (
        "Cover birds."
        in (
            tmp_path / "article/agent-artifacts/wildcard/birds/editorial-direction.md"
        ).read_text()
    )


def test_invalid_request_leaves_no_partial_article(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    workspace = tmp_path / "article"

    with pytest.raises(StartArticleError, match="no configured prompt fragment"):
        initialize(
            repo=repo,
            workspace=workspace,
            series_id="ai-briefs",
            slug="2026-07-29",
            template_id="brief",
            tags=("unknown",),
        )

    assert not workspace.exists()


def test_invalid_runtime_context_leaves_no_partial_article(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    (repo / "press/site.yaml").write_text("[invalid]\n")
    workspace = tmp_path / "article"

    with pytest.raises(StartArticleError, match="press/site.yaml must be a mapping"):
        initialize(
            repo=repo,
            workspace=workspace,
            series_id="semiconductors",
            slug="micron",
            template_id="article",
        )

    assert not workspace.exists()


def test_existing_workspace_is_never_overwritten(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    workspace = tmp_path / "article"
    workspace.mkdir()
    marker = workspace / "keep.txt"
    marker.write_text("mine\n")

    with pytest.raises(StartArticleError, match="workspace is not empty"):
        initialize(
            repo=repo,
            workspace=workspace,
            series_id="semiconductors",
            slug="micron",
            template_id="article",
        )

    assert marker.read_text() == "mine\n"


def pin_voice_guide(repo: pathlib.Path, series_id: str, guide: str) -> pathlib.Path:
    series = repo / "press/series" / series_id / "series.yaml"
    series.write_text(series.read_text() + "\nvoice_guide: voice-guide.md\n")
    path = series.parent / "voice-guide.md"
    path.write_text(guide)
    return path


def test_pinned_voice_guide_stands_in_for_the_coach(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    guide = "# Voice guide\n\nWrite plainly.\n"
    pin_voice_guide(repo, "semiconductors", guide)
    workspace = tmp_path / "article"

    initialize(
        repo=repo,
        workspace=workspace,
        series_id="semiconductors",
        slug="micron",
        template_id="article",
    )

    invocation = workspace / "agent-artifacts/semiconductors/micron/writing-coach/01"
    assert (invocation / "voice-guide.md").read_text() == guide
    brief = (invocation / "brief.md").read_text()
    assert "press/series/semiconductors/voice-guide.md" in brief
    assert "no writing coach was invoked" in brief

    errors = validate_artifacts(workspace, series="semiconductors", slug="micron")
    assert not [error for error in errors if "writing-coach" in error]


def test_a_series_without_a_pinned_guide_still_expects_the_coach(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    workspace = tmp_path / "article"

    initialize(
        repo=repo,
        workspace=workspace,
        series_id="semiconductors",
        slug="micron",
        template_id="article",
    )

    artifacts = workspace / "agent-artifacts/semiconductors/micron"
    assert (artifacts / "editorial-direction.md").is_file()
    assert not (artifacts / "writing-coach").exists()


def test_a_missing_pinned_guide_leaves_no_partial_article(
    clone_testrepo,
    tmp_path: pathlib.Path,
) -> None:
    repo = pathlib.Path(clone_testrepo("press", "templates", "spec"))
    series = repo / "press/series/semiconductors/series.yaml"
    series.write_text(series.read_text() + "\nvoice_guide: voice-guide.md\n")
    workspace = tmp_path / "article"

    with pytest.raises(StartArticleError, match="missing pinned voice guide"):
        initialize(
            repo=repo,
            workspace=workspace,
            series_id="semiconductors",
            slug="micron",
            template_id="article",
        )

    assert not workspace.exists()
