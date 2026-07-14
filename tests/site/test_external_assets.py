"""Third-party assets a press declares: pinned, hashed, or refused."""

import pathlib
from collections.abc import Callable

import build_site
import validate_config
from pages import Site, build_press
from press import make_full_library

DECLARED = 'src="https://cdn.example/hi.js"'


def test_an_asset_without_integrity_is_rejected() -> None:
    errors: list[str] = []

    validate_config.check_site_assets(
        {"scripts": [{"url": "https://cdn.example/x.js"}]}, errors=errors
    )

    assert any("integrity" in e for e in errors)


def test_a_non_https_asset_url_is_rejected() -> None:
    errors: list[str] = []

    validate_config.check_site_assets(
        {"scripts": [{"url": "http://cdn.example/x.js", "integrity": "sha384-AAA"}]},
        errors=errors,
    )

    assert any("https" in e for e in errors)


def test_pinned_and_hashed_assets_validate() -> None:
    errors: list[str] = []

    validate_config.check_site_assets(
        {
            "scripts": [
                {
                    "url": "https://cdn.example/x.js",
                    "integrity": "sha384-A",
                    "defer": True,
                }
            ],
            "styles": [{"url": "https://cdn.example/x.css", "integrity": "sha512-B"}],
        },
        errors=errors,
    )

    assert errors == []


def test_a_rendered_asset_carries_integrity_and_crossorigin() -> None:
    html = build_site.render_assets_html(
        {"scripts": [{"url": "https://cdn.example/x.js", "integrity": "sha384-A"}]}
    )

    assert 'integrity="sha384-A"' in html
    assert 'crossorigin="anonymous"' in html


def test_no_declared_assets_renders_nothing() -> None:
    assert build_site.render_assets_html(None) == ""


def test_a_declared_asset_is_injected_into_chrome_pages_and_articles(
    clone_testrepo: Callable[..., str],
) -> None:
    repo = clone_testrepo("press", "templates", "engine")
    site_yaml = pathlib.Path(repo, "press", "site.yaml")
    site_yaml.write_text(
        site_yaml.read_text()
        + "assets:\n  scripts:\n    - url: https://cdn.example/hi.js\n"
        + "      integrity: sha384-TESTHASH\n"
    )

    site: Site = build_press(repo, make_full_library())

    assert DECLARED in site.index
    assert DECLARED in site.read("library", "semiconductors", "micron.html")
