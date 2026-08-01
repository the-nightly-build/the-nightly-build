"""The furniture gallery stays in lockstep with the catalogs.

The gallery (scripts/gallery/build.py) renders every catalog piece from a
hand-written sample fragment. Engine samples ship with the engine; press samples
live beside their owning catalog and may fall back to a path-specific
placeholder. These tests hold those ownership boundaries together.
"""

import pathlib
import re

import pytest
from gallery.build import build, discover_pieces

REPO = pathlib.Path(__file__).resolve().parents[1]


def test_every_engine_piece_has_a_sample() -> None:
    pieces = discover_pieces(REPO)

    assert pieces, "no catalog pieces discovered"
    missing = [p.slug for p in pieces if p.engine_owned and not p.sample_path.is_file()]
    assert not missing


def test_table_sample_exercises_long_labels_and_prose_cells() -> None:
    sample = (REPO / "scripts/gallery/samples/table.html").read_text(encoding="utf-8")
    labels = re.findall(r'<span class="nb-table-token">([^<]+)</span>', sample)
    prose_cells = re.findall(r'<td class="txt">\s*(.*?)\s*</td>', sample, flags=re.S)

    assert labels
    assert prose_cells
    assert max(map(len, labels)) >= 12
    assert any(len(" ".join(cell.split())) >= 80 for cell in prose_cells)


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
    assert "press/furniture/samples/house-special.html" in page


def test_shared_press_furniture_uses_its_own_sample(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    (repo / "templates").mkdir(parents=True)
    (repo / "templates" / "FURNITURE.md").write_text("# Furniture\n")
    furniture = repo / "press" / "furniture"
    (furniture / "samples").mkdir(parents=True)
    (furniture / "catalog.md").write_text(
        "# Mine\n\n## House special\n\nA press-only piece.\n"
    )
    (furniture / "samples" / "house-special.html").write_text(
        '<div class="house-sample">local shared sample</div>\n'
    )

    page = build(repo, tmp_path / "out" / "index.html").read_text(encoding="utf-8")

    assert "local shared sample" in page
    assert "no gallery sample yet" not in page


def test_press_template_uses_its_own_sample_directory(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    (repo / "templates").mkdir(parents=True)
    (repo / "templates" / "FURNITURE.md").write_text("# Furniture\n")
    template = repo / "press" / "templates" / "feature"
    (template / "samples").mkdir(parents=True)
    (template / "furniture.md").write_text(
        "# Feature furniture\n\n## Story rail\n\nA template-only piece.\n"
    )
    (template / "samples" / "story-rail.html").write_text(
        '<div class="story-sample">local template sample</div>\n'
    )

    page = build(repo, tmp_path / "out" / "index.html").read_text(encoding="utf-8")

    assert "local template sample" in page
    piece = next(p for p in discover_pieces(repo) if p.name == "Story rail")
    assert piece.sample_path == template / "samples" / "story-rail.html"


def test_engine_template_samples_remain_in_the_engine_gallery_directory() -> None:
    piece = next(
        p for p in discover_pieces(REPO) if p.engine_owned and p.scope != "engine base"
    )

    assert piece.sample_path.parent == REPO / "scripts" / "gallery" / "samples"
