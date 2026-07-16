"""The look: palette parity, contrast, and the cache stamp.

A theme defines its color tokens four times over (light, dark, and the two
manual-override blocks), and a missing token in any block silently falls back
to the light value, which readers only notice as a broken dark mode. These
tests read the shipped newspaper theme as the contract's reference: every
block must carry the full token set, and the data colors (--chart-1..6,
--ok/--warn/--bad) must hold their WCAG floors against that block's own --bg
and --panel, so a re-skin cannot ship unreadable legends or status text. The
stamp tests prove that an edit to any CSS owner — the theme or any furniture
file — changes the cache-busting stamp, because an unstamped edit never
reaches a reader who already holds the old file.
"""

import pathlib
import re
from collections.abc import Callable

import pytest

from pages import build_press
from press import REPO, make_full_library

THEME_CSS = (REPO / "engine" / "assets" / "themes" / "newspaper.css").read_text()
PALETTE_BLOCK_BODIES = [
    body
    for _, body in re.findall(
        r"(:root[^{]*|@media[^{]*\{\s*:root[^{]*)\{([^}]*)\}", THEME_CSS
    )
]
PALETTE_BLOCKS = [
    set(re.findall(r"--([a-z0-9-]+)\s*:", body)) for body in PALETTE_BLOCK_BODIES
]
NON_COLOR = {"serif", "sans", "mono", "radius"}
BASE_COLORS = PALETTE_BLOCKS[0] - NON_COLOR

CHART_TOKENS = {f"chart-{i}" for i in range(1, 7)}
STATUS_TOKENS = {"ok", "warn", "bad"}


def test_the_theme_has_four_palette_blocks() -> None:
    assert len(PALETTE_BLOCKS) == 4


@pytest.mark.parametrize("index", range(1, len(PALETTE_BLOCKS)))
def test_every_palette_block_defines_every_color_token(index: int) -> None:
    missing = BASE_COLORS - PALETTE_BLOCKS[index]

    assert not missing


def test_the_theme_defines_the_data_color_tokens() -> None:
    assert CHART_TOKENS | STATUS_TOKENS <= BASE_COLORS


def wcag_contrast(hex_a: str, hex_b: str) -> float:
    def luminance(hex_color: str) -> float:
        channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            for c in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    high, low = sorted((luminance(hex_a), luminance(hex_b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


# Chart marks must be readable on the page and the panel (WCAG 1.4.11 non-text,
# 3:1); status tokens color small text (grade verdicts, holds-up labels), so
# they carry the 4.5:1 text bar. Checked per block so no mode can regress.
@pytest.mark.parametrize("index", range(len(PALETTE_BLOCK_BODIES)))
def test_data_colors_keep_contrast_on_their_surfaces(index: int) -> None:
    hexes = dict(
        re.findall(
            r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})", PALETTE_BLOCK_BODIES[index]
        )
    )
    surfaces = [hexes["bg"], hexes["panel"]]

    for token in sorted(CHART_TOKENS):
        for surface in surfaces:
            assert wcag_contrast(hexes[token], surface) >= 3.0, (token, surface)
    for token in sorted(STATUS_TOKENS):
        for surface in surfaces:
            assert wcag_contrast(hexes[token], surface) >= 4.5, (token, surface)


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
