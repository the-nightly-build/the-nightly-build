"""The front page: tonight's build, and the chrome around it."""

import build_site
from pages import Site


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


def test_a_real_build_carries_no_press_check_banner(full_site: Site) -> None:
    assert "Press check" not in full_site.index


def test_the_menu_says_today(full_site: Site) -> None:
    assert ">Today</a>" in full_site.index


def test_the_default_imprint_credits_the_canonical_repo(full_site: Site) -> None:
    imprint = (
        f'class="nb-imprint" href="https://github.com/{build_site.UPSTREAM_REPOSITORY}"'
    )

    assert imprint in full_site.index
    assert ">GitHub</a>" not in full_site.index


def test_the_footer_recruits_to_the_canonical_repo(full_site: Site) -> None:
    assert (
        f'href="https://github.com/{build_site.UPSTREAM_REPOSITORY}" target="_blank" '
        'rel="noopener noreferrer">Start your own' in full_site.index
    )


def test_the_hamburger_links_the_directory(full_site: Site) -> None:
    assert (
        f'href="{build_site.DIRECTORY_URL}" target="_blank" '
        'rel="noopener noreferrer">The whole newspaper' in full_site.index
    )


def test_the_star_link_is_omitted_when_the_repository_is_unknown(
    full_site: Site,
) -> None:
    assert "Star on GitHub" not in full_site.index


def test_a_custom_footer_renders_as_an_unlinked_imprint(net_site: Site) -> None:
    assert '<span class="nb-imprint">Read it with your coffee.</span>' in net_site.index


def test_the_star_link_targets_this_press_when_the_repository_is_known(
    net_site: Site,
) -> None:
    assert (
        'href="https://github.com/alice/my-press" target="_blank" '
        'rel="noopener noreferrer">Star on GitHub' in net_site.index
    )
