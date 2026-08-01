"""The front page: the latest build and its surrounding chrome.

The suite covers article ordering, navigation destinations, source metadata,
appearance controls, external-link safety, and repository discovery. Labels
remain free to evolve without becoming test contracts.
"""

import build_site
from pages import Site


def menu_eco(page: str) -> str:
    _before, marker, after = page.partition('<div class="nb-menu-eco">')
    assert marker
    return after.partition("</div>")[0]


def test_the_newsstand_leads_with_the_nights_date(full_site: Site) -> None:
    assert "Monday, July 6, 2026" in full_site.index


def test_the_newsstand_totals_the_nights_reading(full_site: Site) -> None:
    assert "min read</span>" in full_site.index
    assert "nb-articleline" in full_site.index


def test_the_lead_cell_is_the_longest_read(full_site: Site) -> None:
    assert 'nb-lead-cell" href="library/semiconductors/micron.html"' in full_site.index


def test_the_newsstand_carries_the_appearance_toggle(full_site: Site) -> None:
    assert 'class="nb-appearance"' in full_site.index


def test_stories_carry_section_kickers(full_site: Site) -> None:
    assert 'class="nb-kicker"' in full_site.index


def test_cells_show_each_articles_source_count(full_site: Site) -> None:
    assert ">8 sources</span>" in full_site.index
    assert ">5 sources</span>" in full_site.index


def test_the_newsstand_links_the_previous_night(full_site: Site) -> None:
    assert 'href="builds/2026-07-05/"' in full_site.index


def test_the_menu_marks_the_root_as_current(full_site: Site) -> None:
    assert '<a href="" aria-current="page">' in full_site.index


def test_the_default_imprint_credits_the_canonical_repo(full_site: Site) -> None:
    imprint = (
        f'class="nb-imprint" href="https://github.com/{build_site.UPSTREAM_REPOSITORY}"'
    )

    assert imprint in full_site.index


def test_the_menu_links_to_the_canonical_repo(full_site: Site) -> None:
    assert (
        f'href="https://github.com/{build_site.UPSTREAM_REPOSITORY}" target="_blank" '
        'rel="noopener noreferrer">' in menu_eco(full_site.index)
    )


def test_the_hamburger_links_the_directory(full_site: Site) -> None:
    assert (
        f'href="{build_site.DIRECTORY_URL}" target="_blank" '
        'rel="noopener noreferrer">' in menu_eco(full_site.index)
    )


def test_the_menu_omits_a_press_link_when_the_repository_is_unknown(
    full_site: Site,
) -> None:
    assert menu_eco(full_site.index).count("<a ") == 2


def test_a_custom_footer_renders_as_an_unlinked_imprint(net_site: Site) -> None:
    assert '<span class="nb-imprint">Read it with your coffee.</span>' in net_site.index


def test_the_star_link_targets_this_press_when_the_repository_is_known(
    net_site: Site,
) -> None:
    eco = menu_eco(net_site.index)

    assert (
        'href="https://github.com/alice/my-press" target="_blank" '
        'rel="noopener noreferrer">' in eco
    )
    assert eco.count("<a ") == 3
