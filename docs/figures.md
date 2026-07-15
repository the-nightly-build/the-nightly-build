# Source figures

An article may carry an exact figure from a cited primary or public document.
It is an article bundle: the HTML remains `library/<series>/<slug>.html`; each
figure is a PNG, JPEG, or WebP directly under `library/<series>/<slug>/`.
Nothing in an article may load an image from the web.

Install the repository-managed capture toolchain once:

```sh
./scripts/install-figure-capture.sh
```

Use the least invasive capture method that preserves the exact visual:

```sh
# A source supplies the image itself.
uv run --group figure-capture engine/capture_figure.py image SOURCE-IMAGE-URL \
  library/SERIES/SLUG/figure-1.webp

# A source supplies only a PDF. Coordinates are points from its top-left page origin.
uv run --group figure-capture engine/capture_figure.py pdf PAPER.pdf \
  library/SERIES/SLUG/figure-1.png --page 4 --clip X,Y,WIDTH,HEIGHT

# A source page renders a canvas or has no exportable figure.
uv run --group figure-capture engine/capture_figure.py web SOURCE-PAGE-URL \
  library/SERIES/SLUG/figure-1.png --selector 'CSS-SELECTOR'
```

The helper normalizes outputs to a 2400-pixel maximum edge. Research logs name
the source figure, its page or web location, its argumentative use, and the
parts that must remain; they do not prescribe crop coordinates. The writer
makes the first crop, then inspects the local asset and rendered article. The
editor compares both with the source and can request a recrop that names what
must remain and what must leave. The proof rejects
oversized, missing, externally hosted, or uncited figures. It does not decide
whether a visual is publishable: use only an exact primary-source figure and
state what it shows in useful alternative text and a caption that cites the
document.
