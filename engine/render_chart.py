#!/usr/bin/env python3
"""Render an article chart: a plotly script in, a normalized PNG out.

Run through ``uv run --group charts`` after bootstrapping the optional chart
toolchain (``scripts/install-charts.sh``). The input is the chart's committed
provenance script (``library/<series>/<slug>/chart-N.py``), which must build a
plotly figure and bind it to a module-level ``fig``; this tool registers the
paper's "nb" plotly template as the default before the script runs, so a bare
figure comes out already wearing the house style. The chart is drawn on its
own fixed light chart paper — a PNG cannot follow the reader's theme, so it
behaves like a photograph — while its series colors come from the press
theme's ``--chart-1..6`` tokens (a built-in colorblind-safe set when a theme
predates them). Output is sized to the proof's figure limits; the tool knows
nothing about captions or citations, which stay the writer's job.
"""

import argparse
import pathlib
import re
import runpy

import plotly.graph_objects as go
import plotly.io as pio

from nb.proof.structure import MAX_FIGURE_BYTES, MAX_FIGURE_EDGE, image_dimensions
from nb.site.assets import css_owners
from nb.site.library import load_site_config

# The fixed chart paper: light, like a printed figure, in any reader theme.
PAPER = "#ffffff"
INK = "#1f2733"
MUTED = "#68727f"
GRID = "#e9edf2"

# Falls back when the press theme predates the --chart-1..6 tokens: the
# shipped newspaper light palette, CVD-validated in that theme's PR.
FALLBACK_PALETTE = ["#96640a", "#1c5cab", "#008a74", "#a8332e", "#6d28d9", "#2e7d4f"]

# Secondary encoding so series never differ by color alone: line dashes and
# marker symbols cycle with the colorway, slot for slot.
DASHES = ["solid", "dash", "dot", "dashdot", "longdash", "solid"]
MARKERS = ["circle", "square", "diamond", "triangle-up", "x", "cross"]

EXPORT_WIDTH = 1200
EXPORT_HEIGHT = 675
EXPORT_SCALE = 2


def theme_palette(repo: str) -> list[str]:
    owners = css_owners(repo, load_site_config(repo))
    if owners:
        base_block = re.split(
            r"@media|\[data-mode", pathlib.Path(owners[0]).read_text(encoding="utf-8")
        )[0]
        tokens = dict(re.findall(r"--chart-(\d+)\s*:\s*(#[0-9a-fA-F]{6})", base_block))
        if tokens:
            return [tokens[n] for n in sorted(tokens, key=int)]
    return FALLBACK_PALETTE


def nb_template(palette: list[str]) -> go.layout.Template:
    axis = {
        "gridcolor": GRID,
        "linecolor": GRID,
        "zerolinecolor": GRID,
        "tickcolor": MUTED,
        "tickfont": {"color": MUTED, "size": 13},
        "title": {"font": {"color": MUTED, "size": 14}},
    }
    template = go.layout.Template(
        layout={
            "paper_bgcolor": PAPER,
            "plot_bgcolor": PAPER,
            "colorway": palette,
            "font": {
                "family": "Inter, Helvetica, Arial, sans-serif",
                "color": INK,
                "size": 14,
            },
            "xaxis": axis,
            "yaxis": axis,
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "font": {"color": INK, "size": 13},
            },
            "margin": {"t": 48, "r": 24, "b": 56, "l": 64},
        }
    )
    template.data.scatter = [
        go.Scatter(
            line={"dash": dash, "width": 2.5}, marker={"symbol": symbol, "size": 7}
        )
        for dash, symbol in zip(DASHES, MARKERS, strict=True)
    ]
    return template


def render(script: pathlib.Path, *, out: pathlib.Path, repo: str) -> pathlib.Path:
    pio.templates["nb"] = nb_template(theme_palette(repo))
    pio.templates.default = "nb"

    module = runpy.run_path(str(script))
    fig = module.get("fig")
    if not isinstance(fig, go.Figure):
        raise SystemExit(f"{script} must bind a plotly Figure to a module-level `fig`")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(
        str(out), width=EXPORT_WIDTH, height=EXPORT_HEIGHT, scale=EXPORT_SCALE
    )

    size = out.stat().st_size
    if size > MAX_FIGURE_BYTES:
        raise SystemExit(
            f"{out} is {size} bytes; the proof caps figures at {MAX_FIGURE_BYTES}"
        )
    dimensions = image_dimensions(str(out))
    if dimensions is None or max(dimensions) > MAX_FIGURE_EDGE:
        raise SystemExit(
            f"{out} exceeds the proof's {MAX_FIGURE_EDGE}px edge cap: {dimensions}"
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render an article chart: a plotly script in, a normalized PNG out."
    )
    parser.add_argument(
        "script", type=pathlib.Path, help="chart-N.py binding a module-level `fig`"
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        help="output PNG (default: the script's stem + .png)",
    )
    parser.add_argument(
        "--repo", default=".", help="repo root whose theme supplies the palette"
    )
    args = parser.parse_args()

    out = args.out or args.script.with_suffix(".png")
    if out.suffix.lower() != ".png":
        parser.error("output must end in .png")
    print(render(args.script, out=out, repo=args.repo))


if __name__ == "__main__":
    main()
