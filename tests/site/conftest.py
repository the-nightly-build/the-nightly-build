"""The sites the builder suite reads.

One full build serves most of the suite: a collection article and two nights of
briefs, built on the fixture's night. Tests that need a different press (the
directory opt-in, a sequence, a preview) build their own.
"""

import pathlib
from collections.abc import Callable

import pytest
from pages import Site, build_press
from press import make_full_library

DIRECTORY_SITE_YAML = """\
title: "Alice's Nightly Build"
footer: "Read it with your coffee."
directory:
  publish: true
  description: "Books, law, and the quiet parts of the news."
"""

PAGES_URL = "https://alice.github.io/my-press"


@pytest.fixture(scope="session")
def full_site(testrepo: str) -> Site:
    """The fixture press, fully published."""
    return build_press(testrepo, make_full_library())


@pytest.fixture
def net_site(clone_testrepo: Callable[..., str]) -> Site:
    """A press that opts into the directory, built with a Pages URL."""
    repo = clone_testrepo("press", "templates", "engine")
    pathlib.Path(repo, "press", "site.yaml").write_text(DIRECTORY_SITE_YAML)
    return build_press(repo, make_full_library(), base_url=PAGES_URL)
