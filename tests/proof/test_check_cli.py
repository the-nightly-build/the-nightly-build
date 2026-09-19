"""nb check in local mode reads the library checkout the engine keeps.

The writer's proof needs the published state to catch a slug that is already
published. The checkout under .nb-work/library is the one nb duty, nb history,
and nb prepare-pr keep, so local mode reads it when no --library is given. An
article workspace's own library/ folder holds the draft and must never stand in
for it: the draft would read as already published.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
from collections.abc import Callable

import check
from press import TODAY, article


def _draft() -> pathlib.Path:
    path = pathlib.Path(tempfile.mkdtemp(), "library", "semiconductors", "micron.html")
    path.parent.mkdir(parents=True)
    path.write_text(article())
    return path


def _run(repo: str, draft: pathlib.Path, capsys) -> dict:
    check.main(
        [
            str(draft),
            "--series",
            "semiconductors",
            "--repo",
            repo,
            "--no-check-links",
            "--json",
            "--today",
            TODAY,
        ]
    )
    return json.loads(capsys.readouterr().out)


def test_local_mode_reads_the_managed_library_when_no_library_is_given(
    clone_testrepo: Callable[..., str], capsys
) -> None:
    repo = clone_testrepo("press", "templates", "spec", "engine")
    published = pathlib.Path(repo, ".nb-work", "library", "semiconductors")
    published.mkdir(parents=True)
    (published / "micron.html").write_text("")

    report = _run(repo, _draft(), capsys)

    assert any(
        f["code"] == "B-MODE" and "already published" in f["message"]
        for f in report["findings"]
    )


def test_local_mode_without_a_managed_library_cannot_know_what_is_published(
    clone_testrepo: Callable[..., str], capsys
) -> None:
    repo = clone_testrepo("press", "templates", "spec", "engine")

    report = _run(repo, _draft(), capsys)

    assert not any(f["code"] == "B-MODE" for f in report["findings"])
