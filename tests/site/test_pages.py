"""The pages around the front page: builds, sections, series, tags, search."""

import json

from pages import Site


def test_a_build_page_links_the_previous_night(full_site: Site) -> None:
    page = full_site.read("builds", "2026-07-06", "index.html")

    assert "← Sunday, July 5, 2026" in page


def test_an_older_night_links_forward_to_the_newsstand(full_site: Site) -> None:
    page = full_site.read("builds", "2026-07-05", "index.html")

    assert 'href="../../">Monday, July 6, 2026 →' in page


def test_the_build_archive_groups_by_month(full_site: Site) -> None:
    assert "July 2026" in full_site.read("builds", "index.html")


def test_the_sections_page_lists_the_series(full_site: Site) -> None:
    page = full_site.read("series", "index.html")

    assert 'class="nb-series' in page
    assert "Semiconductors" in page


def test_the_sections_page_counts_published_not_progress(full_site: Site) -> None:
    page = full_site.read("series", "index.html")

    assert "1 published" in page
    assert "1 of 5" not in page
    assert "of None" not in page


def test_a_collection_page_shows_the_published_card(full_site: Site) -> None:
    page = full_site.read("series", "semiconductors", "index.html")

    assert "Micron Technology" in page


def test_a_collection_page_renders_no_placeholder_for_unpublished_items(
    full_site: Site,
) -> None:
    page = full_site.read("series", "semiconductors", "index.html")

    assert page.count("coming") == 0
    assert "commissioned" not in page


def test_a_rolling_page_groups_by_month_reverse_chron(full_site: Site) -> None:
    page = full_site.read("series", "ai-briefs", "index.html")

    assert "July 2026" in page
    assert page.find("2026-07-06") < page.rfind("2026-07-05")


def test_a_tag_page_lists_the_tagged_article(full_site: Site) -> None:
    assert "Micron Technology" in full_site.read("tags", "equity", "index.html")


def test_the_search_index_carries_clean_prose(full_site: Site) -> None:
    first = json.loads(full_site.read("search-index.json"))[0]

    assert "<" not in first["text"]
    assert not first["text"].startswith("class=")
