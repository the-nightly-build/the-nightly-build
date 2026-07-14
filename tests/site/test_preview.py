"""The press check: a draft previewed against the published library."""

import pathlib
import re

import pytest
from pages import Site, build_press, undress
from press import article, write_article

DRAFT = (
    article()
    .replace('"slug": "micron"', '"slug": "tsmc"')
    .replace(
        "Micron Technology: The Scarcest Commodity in AI",
        "TSMC: The Foundry at the Center of the World",
    )
)


@pytest.fixture
def preview_site(testrepo: str, full_site: Site, tmp_path: pathlib.Path) -> Site:
    draft_root = str(tmp_path / "draft")
    write_article(draft_root, "semiconductors", slug="tsmc", html=DRAFT)
    return build_press(testrepo, full_site.library, preview_root=draft_root)


def test_a_preview_renders_identically_to_production(preview_site: Site) -> None:
    assert "Press check" not in preview_site.index


def test_a_preview_merges_the_draft_with_the_published_library(
    preview_site: Site,
) -> None:
    assert "TSMC: The Foundry" in preview_site.index
    assert "Micron Technology" in preview_site.index


def test_the_draft_is_flagged_in_the_catalog(preview_site: Site) -> None:
    articles = preview_site.catalog["articles"]

    assert any(e.get("draft") for e in articles if e["slug"] == "tsmc")
    assert not any(e.get("draft") for e in articles if e["slug"] == "micron")


def test_the_draft_file_is_copied_modulo_stamp_and_chrome(preview_site: Site) -> None:
    copied = preview_site.read("library", "semiconductors", "tsmc.html")

    assert re.sub(r"\?v=[0-9a-f]+", "", undress(copied)) == DRAFT


def test_the_published_article_file_is_untouched(preview_site: Site) -> None:
    published = preview_site.read("library", "semiconductors", "micron.html")

    assert "Press check" not in published
