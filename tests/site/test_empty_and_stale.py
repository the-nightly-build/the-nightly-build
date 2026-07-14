"""Two builds that must not fall over: an empty press, and a night with a gap."""

import datetime as dt
import tempfile

from pages import Site, build_press


def empty_site(testrepo: str) -> Site:
    return build_press(testrepo, tempfile.mkdtemp())


def test_a_fresh_fork_says_the_presses_are_ready(testrepo: str) -> None:
    assert "The presses are ready" in empty_site(testrepo).index


def test_an_empty_build_still_renders_a_sections_page(testrepo: str) -> None:
    assert 'class="nb-series' in empty_site(testrepo).read("series", "index.html")


def test_a_gap_shows_the_builds_true_date(testrepo: str, full_site: Site) -> None:
    later = dt.datetime(2026, 7, 10, 9, 0, tzinfo=dt.timezone.utc)

    site = build_press(testrepo, full_site.library, now=later)

    assert "Monday, July 6, 2026" in site.index
