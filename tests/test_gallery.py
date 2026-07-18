"""The furniture gallery stays in lockstep with the catalogs.

The gallery (scripts/gallery/build.py) renders every catalog piece from a
hand-written sample fragment, and a piece without a sample silently vanishes
from the review page — the exact failure the gallery exists to prevent. These
tests hold the two surfaces together: every ``##`` entry in every discovered
catalog must have a sample and must appear on the built page, and the build
must refuse to produce a page when a sample is missing.
"""

import pathlib

import pytest
from gallery.build import SAMPLES, build, discover_pieces

REPO = pathlib.Path(__file__).resolve().parents[1]


def test_every_engine_piece_has_a_sample() -> None:
    pieces = discover_pieces(REPO)

    assert pieces, "no catalog pieces discovered"
    missing = [
        p.slug
        for p in pieces
        if p.engine_owned and not (SAMPLES / f"{p.slug}.html").is_file()
    ]
    assert not missing


def test_the_built_page_shows_every_piece(tmp_path: pathlib.Path) -> None:
    out = build(REPO, tmp_path / "gallery" / "index.html")
    page = out.read_text(encoding="utf-8")

    for piece in discover_pieces(REPO):
        assert f'id="{piece.slug}"' in page
        assert piece.name in page


def test_the_build_fails_loudly_on_a_missing_sample(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    (repo / "templates").mkdir(parents=True)
    (repo / "templates" / "FURNITURE.md").write_text(
        "# Furniture\n\n## Imaginary piece\n\nA piece with no sample.\n"
    )

    with pytest.raises(SystemExit, match="imaginary-piece"):
        build(repo, tmp_path / "out" / "index.html")


def test_press_furniture_without_a_sample_renders_a_placeholder(
    tmp_path: pathlib.Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / "templates").mkdir(parents=True)
    (repo / "templates" / "FURNITURE.md").write_text("# Furniture\n")
    press = repo / "press" / "furniture"
    press.mkdir(parents=True)
    (press / "catalog.md").write_text(
        "# Mine\n\n## House special\n\nA press-only piece.\n"
    )

    page = build(repo, tmp_path / "out" / "index.html").read_text(encoding="utf-8")

    assert "House special" in page
    assert "no gallery sample yet" in page
