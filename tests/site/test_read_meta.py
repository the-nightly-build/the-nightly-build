"""The builder reads the same nb-meta block the proof does, and no other.

Only an ``application/json`` script with the exact ``nb-meta`` identifier is
article metadata. An earlier untyped decoy must remain ordinary page content,
or the builder and publication proof would disagree about article identity.
"""

import pathlib

import build_site

DECOY = (
    "<!DOCTYPE html><html><head>"
    '<script id="nb-meta">{"series":"EVIL","slug":"evil"}</script>'
    '<script type="application/json" id="nb-meta">'
    '{"series":"semiconductors","slug":"micron","date":"2026-07-06"}'
    "</script></head><body></body></html>"
)


# The proof only recognizes <script type="application/json" id="nb-meta">, so
# an untyped decoy placed first — invisible to check.py — must never override
# the typed block the builder reads.
def test_read_meta_ignores_an_untyped_decoy(tmp_path: pathlib.Path) -> None:
    page = tmp_path / "decoy.html"
    page.write_text(DECOY)

    meta = build_site.read_meta(str(page))

    assert meta is not None
    assert meta["series"] == "semiconductors"
