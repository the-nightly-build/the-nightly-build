"""A dateless article must not win the newsstand or blank it."""

import pathlib

import build_site
import pytest
from pages import Site, build_press
from press import article, write_article

UNDATED = (
    article()
    .replace('"slug": "micron"', '"slug": "tsmc"')
    .replace('"date": "2026-07-06", ', "")
    .replace("Micron Technology: The Scarcest Commodity in AI", "TSMC (undated draft)")
)


@pytest.fixture
def dateless_site(testrepo: str, tmp_path: pathlib.Path) -> Site:
    library = str(tmp_path / "library-root")
    write_article(library, "semiconductors", slug="micron", html=article())
    write_article(library, "semiconductors", slug="tsmc", html=UNDATED)
    return build_press(testrepo, library)


def test_the_newsstand_still_leads_with_the_dated_article(dateless_site: Site) -> None:
    assert "Micron Technology" in dateless_site.index
    assert "No articles this night" not in dateless_site.index


def test_a_real_date_wins_latest_over_the_dateless_bucket(dateless_site: Site) -> None:
    nights = sorted(dateless_site.catalog["builds"], key=build_site.date_sort_key)

    assert nights[-1] == "2026-07-06"


def test_the_dateless_article_still_gets_its_own_build_page(
    dateless_site: Site,
) -> None:
    assert "TSMC (undated draft)" in dateless_site.read(
        "builds", "unknown", "index.html"
    )
