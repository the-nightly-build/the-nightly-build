"""Series modes the builder renders: a numbered sequence, and an open series."""

import pathlib
from collections.abc import Callable

import pytest
from pages import Site, build_press
from press import article, write_article

WILDCARD_YAML = """\
name: Wildcard
mode: open
templates: [article, brief]
cadence: weekdays
autopublish: true
strict: false
items:
  - {slug: commissioned-piece, title: On Commission}
"""


@pytest.fixture
def sequence_site(clone_testrepo: Callable[..., str], tmp_path: pathlib.Path) -> Site:
    repo = clone_testrepo("press", "templates", "engine")
    series_yaml = pathlib.Path(repo, "press", "series", "semiconductors", "series.yaml")
    series_yaml.write_text(
        series_yaml.read_text().replace("mode: collection", "mode: sequence")
    )
    library = str(tmp_path / "library-root")
    write_article(
        library,
        "semiconductors",
        slug="micron",
        html=article().replace(
            '"mode": "collection", "order": null', '"mode": "sequence", "order": 1'
        ),
    )
    return build_press(repo, library)


@pytest.fixture
def open_site(clone_testrepo: Callable[..., str], tmp_path: pathlib.Path) -> Site:
    repo = clone_testrepo("press", "templates", "engine")
    wildcard = pathlib.Path(repo, "press", "series", "wildcard")
    wildcard.mkdir()
    (wildcard / "series.yaml").write_text(WILDCARD_YAML)
    library = str(tmp_path / "library-root")
    write_article(
        library,
        "wildcard",
        slug="the-cuda-moat",
        html=article()
        .replace(
            '"series": "semiconductors", "slug": "micron",',
            '"series": "wildcard", "slug": "the-cuda-moat",',
        )
        .replace('"mode": "collection"', '"mode": "open"'),
    )
    return build_press(repo, library)


def test_a_sequence_page_numbers_published_items_in_config_order(
    sequence_site: Site,
) -> None:
    page = sequence_site.read("series", "semiconductors", "index.html")

    assert ">01<" in page
    assert ">05<" not in page


def test_a_sequence_page_renders_no_placeholder_for_unpublished_items(
    sequence_site: Site,
) -> None:
    page = sequence_site.read("series", "semiconductors", "index.html")

    assert "nb-seq-unpub" not in page
    assert "continue here" not in page
    assert "nb-progress-wide" not in page


def test_a_sequence_shows_a_published_count_not_progress(sequence_site: Site) -> None:
    page = sequence_site.read("series", "index.html")

    assert "1 published" in page
    assert "1 of 5" not in page


def test_an_open_series_carries_its_choice_list_and_cadence(open_site: Site) -> None:
    wildcard = next(s for s in open_site.catalog["series"] if s["id"] == "wildcard")

    assert wildcard["mode"] == "open"
    assert wildcard["templates"] == ["article", "brief"]
    assert wildcard["cadence"] == "weekdays"
    assert wildcard["total"] is None


def test_an_open_series_page_reads_reverse_chron_by_month(open_site: Site) -> None:
    page = open_site.read("series", "wildcard", "index.html")

    assert "July 2026" in page
    assert "the-cuda-moat" in page


def test_an_open_series_renders_no_placeholder_for_a_pending_commission(
    open_site: Site,
) -> None:
    page = open_site.read("series", "wildcard", "index.html")

    assert "On Commission" not in page
    assert "commissioned" not in page


def test_an_open_series_page_shows_the_template_choice_list(open_site: Site) -> None:
    assert "article, brief" in open_site.read("series", "wildcard", "index.html")
