"""Source counts reach the reader through source_label, or not at all."""

import pathlib

from pages import build_press
from press import article, write_article


def test_a_non_int_sources_value_never_reaches_the_reader_raw(
    testrepo: str, tmp_path: pathlib.Path
) -> None:
    library = str(tmp_path / "library-root")
    write_article(
        library,
        "semiconductors",
        slug="micron",
        html=article().replace('"sources": 8,', '"sources": "<b>x</b>",'),
    )

    site = build_press(testrepo, library)

    assert "<b>x</b>" not in site.index
