"""The catalog: what the builder tells every other reader of the site."""

import pathlib
from collections.abc import Callable

import build_site
import pytest
from pages import Site, build_press
from press import make_full_library


def series_of(site: Site, sid: str) -> dict:
    return next(s for s in site.catalog["series"] if s["id"] == sid)


def test_catalog_titles_the_site(full_site: Site) -> None:
    assert full_site.catalog["site_title"] == "The Nightly Build"


def test_collection_series_counts_published_against_a_total(full_site: Site) -> None:
    semis = series_of(full_site, "semiconductors")

    assert semis["count"] == 1
    assert semis["total"] == 5


def test_rolling_series_counts_published_with_no_total(full_site: Site) -> None:
    briefs = series_of(full_site, "ai-briefs")

    assert briefs["count"] == 2
    assert briefs["total"] is None


def test_articles_carry_path_position_and_reading_time(full_site: Site) -> None:
    assert all(
        "path" in e and "position" in e and "reading_minutes" in e
        for e in full_site.catalog["articles"]
    )


def test_articles_are_newest_first(full_site: Site) -> None:
    assert full_site.catalog["articles"][0]["date"] == "2026-07-06"


def test_builds_are_grouped_by_nb_meta_date(full_site: Site) -> None:
    assert full_site.catalog["builds"] == {
        "2026-07-06": ["ai-briefs/2026-07-06", "semiconductors/micron"],
        "2026-07-05": ["ai-briefs/2026-07-05"],
    }


def test_tags_index_lists_the_tagged_article(full_site: Site) -> None:
    assert full_site.catalog["tags"].get("equity") == ["semiconductors/micron"]


def test_catalog_speaks_protocol_1_3(full_site: Site) -> None:
    catalog = full_site.catalog

    assert catalog["protocol"] == "1.3"
    assert catalog["footer"] is None
    assert catalog["upstream"] == build_site.UPSTREAM_REPOSITORY
    assert catalog["directory_url"] == build_site.DIRECTORY_URL


def test_a_press_is_listed_by_default(full_site: Site) -> None:
    assert full_site.catalog.get("directory", {}).get("publish") is True


@pytest.mark.parametrize(
    ("explicit", "base_url", "expected"),
    [
        (None, "https://alice.github.io/my-press", "alice/my-press"),
        ("Alice/My-Press", "https://x.github.io/y", "Alice/My-Press"),
        (None, "", None),
    ],
    ids=["derived from a Pages URL", "explicit wins", "underivable"],
)
def test_self_repository_derivation(
    explicit: str | None, base_url: str, expected: str | None
) -> None:
    assert build_site.derive_self_repository(explicit, base_url) == expected


def test_a_custom_footer_flows_to_the_catalog(net_site: Site) -> None:
    assert net_site.catalog["footer"] == "Read it with your coffee."


def test_the_repository_is_derived_at_build_time(net_site: Site) -> None:
    assert net_site.catalog["repository"] == "alice/my-press"


def test_the_directory_block_is_publish_and_description_only(net_site: Site) -> None:
    assert net_site.catalog.get("directory") == {
        "publish": True,
        "description": "Books, law, and the quiet parts of the news.",
    }


def test_opting_out_emits_only_publish_false(
    clone_testrepo: Callable[..., str],
) -> None:
    repo = clone_testrepo("press", "templates", "engine")
    pathlib.Path(repo, "press", "site.yaml").write_text(
        "directory:\n  publish: false\n"
    )

    site = build_press(repo, make_full_library(), base_url="https://x.github.io/y")

    assert site.catalog.get("directory") == {"publish": False}
