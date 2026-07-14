"""The Atom feeds: what a reader's feed reader gets, and how it tells papers apart."""

import xml.etree.ElementTree as ET

import build_site
from pages import Site, build_press
from press import NOW, make_full_library

NS = "{http://www.w3.org/2005/Atom}"


def entries(xml_text: str) -> list[ET.Element]:
    return ET.fromstring(xml_text).findall(f"{NS}entry")


def find_text(elem: ET.Element, path: str) -> str:
    node = elem.find(path)
    assert node is not None, f"missing element: {path}"
    return node.text or ""


def test_the_global_feed_carries_every_article(full_site: Site) -> None:
    assert len(entries(full_site.read("feed.xml"))) == 3


def test_the_newest_entries_carry_full_script_free_content(full_site: Site) -> None:
    content = find_text(entries(full_site.read("feed.xml"))[0], f"{NS}content")

    assert "Micron" in content
    assert "<script" not in content


def test_a_series_feed_is_scoped_to_its_series(full_site: Site) -> None:
    assert len(entries(full_site.read("series", "ai-briefs", "feed.xml"))) == 2


def test_two_papers_on_one_host_get_distinct_feed_ids() -> None:
    feed_a = build_site.atom_feed(
        "https://alice.github.io/paper-a", "feed.xml", title="A", eds=[], generated=NOW
    )
    feed_b = build_site.atom_feed(
        "https://alice.github.io/paper-b", "feed.xml", title="B", eds=[], generated=NOW
    )

    id_a = find_text(ET.fromstring(feed_a), f"{NS}id")
    id_b = find_text(ET.fromstring(feed_b), f"{NS}id")

    assert id_a != id_b
    assert id_a.startswith("tag:alice.github.io,")


def test_a_feed_carries_an_author_name_from_the_site_title() -> None:
    feed = build_site.atom_feed(
        "https://alice.github.io/paper-a", "feed.xml", title="A", eds=[], generated=NOW
    )

    assert find_text(ET.fromstring(feed), f"{NS}author/{NS}name") == "A"


def test_the_same_slug_on_two_papers_gets_distinct_entry_ids(testrepo: str) -> None:
    a = build_press(testrepo, make_full_library(), base_url="https://a.example")
    b = build_press(testrepo, make_full_library(), base_url="https://b.example")

    id_a = find_text(ET.fromstring(a.read("feed.xml")), f"{NS}entry/{NS}id")
    id_b = find_text(ET.fromstring(b.read("feed.xml")), f"{NS}entry/{NS}id")

    assert id_a != id_b
    assert "a.example" in id_a
    assert "b.example" in id_b
