"""Hostile series, slugs and tags: escaped in the markup, refused on the filesystem.

series and slug flow raw from library directory and file names, so a quote or an
ampersand must not break an href attribute or an Atom <id>, and a tag must never
escape --out.
"""

import pathlib
import xml.etree.ElementTree as ET

import build_site
import pytest
from pages import build_press
from press import NOW, article, write_article

NS = "{http://www.w3.org/2005/Atom}"

HOSTILE_ED = {
    "series": 'a"&b',
    "slug": 'c"&d',
    "reading_minutes": 3,
    "meta": {"title": "T", "dek": "d", "sources": 2},
}


@pytest.mark.parametrize("lead", [False, True], ids=["story item", "lead cell"])
def test_a_hostile_href_is_escaped(lead: bool) -> None:
    html = build_site.story_item(HOSTILE_ED, {}, lead=lead)

    assert 'library/a"&b/c"&d' not in html
    assert "a&quot;&amp;b/c&quot;&amp;d" in html


def test_a_hostile_atom_entry_id_stays_well_formed(tmp_path: pathlib.Path) -> None:
    page = tmp_path / "x.html"
    page.write_text("<html><body><p>hi</p></body></html>")
    ed = {
        "series": 'a"&b',
        "slug": 'c"&d',
        "file": str(page),
        "reading_minutes": 3,
        "meta": {"title": "T", "dek": "d", "date": "2026-07-06"},
    }

    feed = build_site.atom_feed("", "feed.xml", title="T", eds=[ed], generated=NOW)
    entry_id = ET.fromstring(feed).find(f"{NS}entry/{NS}id")

    assert entry_id is not None
    assert entry_id.text == 'urn:nightly-build:library/a"&b/c"&d'


@pytest.mark.parametrize(
    ("tag", "safe"),
    [
        ("../../escape", False),
        ("/etc/passwd", False),
        ("a\\b", False),
        ("equity", True),
        ("markets/equity", True),
    ],
)
def test_is_safe_tag(tag: str, safe: bool) -> None:
    assert build_site.is_safe_tag(tag) == safe


def test_a_traversal_tag_is_dropped_and_writes_nothing_outside_out(
    testrepo: str, tmp_path: pathlib.Path
) -> None:
    library = str(tmp_path / "library-root")
    write_article(
        library,
        "semiconductors",
        slug="micron",
        html=article().replace('"tags": ["equity"]', '"tags": ["../../pwned"]'),
    )
    out = tmp_path / "site"

    catalog = build_site.build(testrepo, library, out=str(out), now=NOW)

    assert "../../pwned" not in catalog["tags"]
    assert not (out.parent / "pwned").exists()


def test_a_nested_tag_page_links_its_assets_at_its_true_depth(
    testrepo: str, tmp_path: pathlib.Path
) -> None:
    library = str(tmp_path / "library-root")
    write_article(
        library,
        "semiconductors",
        slug="micron",
        html=article().replace('"tags": ["equity"]', '"tags": ["markets/equity"]'),
    )

    site = build_press(testrepo, library)
    page = site.read("tags", "markets", "equity", "index.html")

    assert "../../../assets/nb.css" in page
