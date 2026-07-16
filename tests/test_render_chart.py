"""The chart tool: palette resolution, the nb template, and a real render.

render_chart.py is the writer's only sanctioned way to draw a chart, so what
it guarantees is worth pinning: the palette comes from the press theme's
--chart-1..6 tokens with a built-in fallback for themes that predate them,
the registered template carries the fixed chart paper and the dash/marker
cycle that keeps series apart without color, and a rendered PNG lands inside
the proof's figure limits. The end-to-end render needs kaleido's Chrome, so
it skips — never fails — on machines and CI runners that lack it.
"""

import pathlib

import pytest

from nb.proof.structure import MAX_FIGURE_EDGE, image_dimensions

render_chart = pytest.importorskip(
    "render_chart", reason="the optional charts group is not installed"
)

REPO = pathlib.Path(__file__).resolve().parents[1]


def test_theme_palette_reads_chart_tokens(tmp_path: pathlib.Path) -> None:
    theme = tmp_path / "engine" / "assets" / "themes" / "newspaper.css"
    theme.parent.mkdir(parents=True)
    theme.write_text(
        ":root { --chart-1: #111111; --chart-2: #222222; }\n"
        "@media (prefers-color-scheme: dark) { :root { --chart-1: #999999; } }\n"
    )

    assert render_chart.theme_palette(str(tmp_path)) == ["#111111", "#222222"]


def test_theme_palette_falls_back_without_tokens(tmp_path: pathlib.Path) -> None:
    theme = tmp_path / "engine" / "assets" / "themes" / "newspaper.css"
    theme.parent.mkdir(parents=True)
    theme.write_text(":root { --accent: #8a5c08; }\n")

    assert render_chart.theme_palette(str(tmp_path)) == render_chart.FALLBACK_PALETTE


def test_nb_template_carries_palette_and_secondary_encoding() -> None:
    palette = ["#111111", "#222222", "#333333"]
    template = render_chart.nb_template(palette)

    assert list(template.layout.colorway) == palette
    assert template.layout.paper_bgcolor == "#ffffff"
    dashes = {trace.line.dash for trace in template.data.scatter}
    symbols = {trace.marker.symbol for trace in template.data.scatter}
    assert len(dashes) > 1
    assert len(symbols) > 1


def test_render_produces_a_proof_sized_png(tmp_path: pathlib.Path) -> None:
    kaleido = pytest.importorskip("kaleido")
    script = tmp_path / "chart-1.py"
    script.write_text(
        "import plotly.graph_objects as go\n"
        'fig = go.Figure(go.Scatter(name="Series", x=[1, 2, 3], y=[2, 1, 3]))\n'
    )

    try:
        out = render_chart.render(script, out=tmp_path / "chart-1.png", repo=str(REPO))
    except (kaleido.errors.ChromeNotFoundError, RuntimeError) as error:
        pytest.skip(f"kaleido cannot render here: {error}")

    dimensions = image_dimensions(str(out))
    assert dimensions is not None
    assert max(dimensions) == MAX_FIGURE_EDGE
