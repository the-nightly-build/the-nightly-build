"""Exercise production-record generation without a GitHub PR.

The record is a local preflight input and must preserve each gitignored role
artifact exactly, including when GitHub's body limit moves it to a comment.
These tests use tiny independent files so a failure shows whether serialization,
fence nesting, or the overflow boundary lost an artifact rather than a PR API.
"""

import pathlib

import build_record


def artifacts(tmp_path: pathlib.Path) -> pathlib.Path:
    work = tmp_path / ".nb-work" / "series" / "slug"
    work.mkdir(parents=True)
    (work / "task.md").write_text("# Task\n\nDo the work.\n")
    (work / "requested-changes.md").write_text("# Editorial read\n\nAccepted.\n")
    (work / "voice.md").write_text(
        "# Voice\n\nSource: https://example.org/one\n"
        "Source: https://example.org/two\nSource: https://example.org/three\n"
    )
    (work / "research.md").write_text(
        "# Research\n\nEvidence.\n\n## Discarded\n\n- https://example.org — context only\n"
    )
    return work


def article(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "library" / "series" / "slug.html"
    path.parent.mkdir(parents=True)
    path.write_text(
        '<script type="application/json" id="nb-meta">'
        '{"series":"series","slug":"slug","mode":"open","template":"article",'
        '"date":"2026-07-15","title":"A title","order":null}</script>'
    )
    return path


def test_build_embeds_every_artifact_verbatim(tmp_path: pathlib.Path) -> None:
    body, comment = build_record.build(article(tmp_path), artifacts(tmp_path))

    assert comment is None
    assert "## Task" in body
    assert "Do the work." in body
    assert "## Process" in body
    assert "## Voice brief" in body
    assert "## Research" in body
    assert "## Also consulted" in body
    assert "- https://example.org — context only" in body
    assert body.count("````text") == 4


def test_build_moves_oversized_record_to_marked_comment(tmp_path: pathlib.Path) -> None:
    work = artifacts(tmp_path)
    (work / "research.md").write_text("# Research\n\n" + "x" * 200)

    body, comment = build_record.build(article(tmp_path), work, limit=100)

    assert "nb-record-sha256:" in body
    assert "full production record exceeds" in body
    assert comment is not None
    assert comment.startswith("<!-- nb-production-record ")
    assert "x" * 200 in comment
