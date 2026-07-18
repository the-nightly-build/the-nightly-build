# Source assets

An article may carry an exact image from a cited primary or public document.
It is a source asset: a figure, photograph, document detail, or other visual
evidence that lets the reader inspect an argument the prose uses. The HTML
remains `library/<series>/<slug>.html`; each asset is a PNG, JPEG, or WebP
directly under `library/<series>/<slug>/`. Nothing in an article may load an
image from the web.

Install the repository-managed capture toolchain once:

```sh
./scripts/install-figure-capture.sh
```

Use the least invasive capture method that preserves the exact visual:

```sh
# A source supplies the image itself.
uv run --group figure-capture engine/capture_asset.py image SOURCE-IMAGE-URL \
  library/SERIES/SLUG/asset-1.webp

# A source supplies only a PDF. Coordinates are points from its top-left page origin.
uv run --group figure-capture engine/capture_asset.py pdf PAPER.pdf \
  library/SERIES/SLUG/asset-1.png --page 4 --clip X,Y,WIDTH,HEIGHT

# A source page renders a canvas or has no exportable figure.
uv run --group figure-capture engine/capture_asset.py web SOURCE-PAGE-URL \
  library/SERIES/SLUG/asset-1.png --selector 'CSS-SELECTOR'
```

The helper normalizes outputs to a 2400-pixel maximum edge. Research logs name
the source asset, its location, its argumentative use, and the evidence a crop
must retain or remove; they do not prescribe coordinates. The writer makes the
first crop, then inspects the asset and rendered article. The editor compares
both with the source and can request a recrop that names what must remain and
what must leave. Crop away surrounding page furniture and printed source
captions unless that text is itself evidence. The HTML caption is a short
factual label and source citation; interpretation belongs in the prose. The
proof rejects oversized, missing, externally hosted, or uncited assets. It does
not decide whether a visual is publishable: use only an exact primary or public
source asset and state what it shows in useful alternative text.

A source asset is always captured evidence, never something the pipeline
draws. A data visualization the article itself generates is a chart, a
different concept with its own contract: the reserved `chart-N` name, a
committed `chart-N.py`, and the data source cited in the caption. See docs/charts.md.
