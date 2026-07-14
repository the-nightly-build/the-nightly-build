"""The look: palette parity, and the cache stamp that carries an edit to the reader."""

import pathlib
import re
from collections.abc import Callable

import pytest
from pages import build_press
from press import REPO, make_full_library

THEME_CSS = (REPO / "engine" / "assets" / "themes" / "newspaper.css").read_text()
PALETTE_BLOCKS = [
    set(re.findall(r"--([a-z0-9-]+)\s*:", body))
    for _, body in re.findall(
        r"(:root[^{]*|@media[^{]*\{\s*:root[^{]*)\{([^}]*)\}", THEME_CSS
    )
]
NON_COLOR = {"serif", "sans", "mono", "radius"}
BASE_COLORS = PALETTE_BLOCKS[0] - NON_COLOR


def test_the_theme_has_four_palette_blocks() -> None:
    assert len(PALETTE_BLOCKS) == 4


@pytest.mark.parametrize("index", range(1, len(PALETTE_BLOCKS)))
def test_every_palette_block_defines_every_color_token(index: int) -> None:
    missing = BASE_COLORS - PALETTE_BLOCKS[index]

    assert not missing


def test_a_theme_edit_changes_the_cache_busting_stamp(
    clone_testrepo: Callable[..., str],
) -> None:
    repo = clone_testrepo("press", "templates", "engine")
    before = build_press(repo, make_full_library()).stamp

    theme = pathlib.Path(repo, "engine", "assets", "themes", "newspaper.css")
    theme.write_text(theme.read_text() + "\n:root{--nb-test-token:1}\n")

    assert build_press(repo, make_full_library()).stamp != before


# copy_assets folds every CSS owner — the theme, the shared press furniture, and
# each template's bespoke furniture.css — into the single assets/theme.css, and
# the stamp must fold in the same owners so a furniture edit reaches the reader.
def test_furniture_concatenates_into_theme_css_and_busts_the_stamp(
    clone_testrepo: Callable[..., str],
) -> None:
    repo = clone_testrepo("press", "templates", "engine")
    shared_css = pathlib.Path(repo, "press", "furniture", "styles.css")
    shared_css.parent.mkdir(parents=True)
    shared_css.write_text(".rs-shared-furniture{color:rebeccapurple}\n")
    template_css = pathlib.Path(repo, "templates", "article", "furniture.css")
    template_css.write_text(".rs-article-furniture{color:seagreen}\n")

    site = build_press(repo, make_full_library())
    theme_out = site.read("assets", "theme.css")

    assert "--bg" in theme_out
    assert ".rs-shared-furniture" in theme_out
    assert ".rs-article-furniture" in theme_out

    template_css.write_text(".rs-article-furniture{color:crimson}\n")

    assert build_press(repo, make_full_library()).stamp != site.stamp
