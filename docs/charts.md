# Charts

An article's chart is a PNG the writer renders at production time from a
committed plotly script. The script is the chart's provenance: it carries the
data (inline literals, or a sibling `.csv`/`.json` it reads) and publishes
with the article, so a reader can always see the numbers behind the pixels.

Install the repository-managed chart toolchain once:

```sh
./scripts/install-charts.sh
```

Write the chart script beside the article's other assets, at
`library/<series>/<slug>/chart-N.py`. It must build a plotly figure and bind
it to a module-level `fig`:

```python
import plotly.graph_objects as go

years = ["2020", "2021", "2022", "2023", "2024", "2025"]
training = [4, 9, 21, 48, 87, 121]
inference = [2, 4, 9, 26, 64, 118]

fig = go.Figure()
fig.add_trace(go.Scatter(name="Training", x=years, y=training))
fig.add_trace(go.Scatter(name="Inference", x=years, y=inference))
fig.update_layout(yaxis_title="US$ billions")
```

Render it:

```sh
uv run --group charts engine/render_chart.py library/<series>/<slug>/chart-1.py
```

The tool registers the paper's `nb` plotly template as the default before the
script runs, so a bare figure comes out already wearing the house style:
fixed light chart paper (a PNG cannot follow the reader's theme, so it
behaves like a photograph on the figure card), series colors from the press
theme's `--chart-1..6` tokens in order, and a line-dash and marker cycle so
series never differ by color alone. The full plotly API is available when a
chart needs more than the default look; keep axes labeled, note a non-linear
scale, and keep decoration out of the drawing.

The output lands beside the script as `chart-N.png`, sized inside the
proof's figure limits (2400px maximum edge, 2 MiB). Inspect the PNG and the
rendered article before opening the PR; the editor compares the script's
data against the research log and reads the image like any other figure.
