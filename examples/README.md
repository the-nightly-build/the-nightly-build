# examples/: a complete, working paper

A full paper configuration, kept as living documentation. Six sections show the
whole surface, including the parts a paper builds for itself: a custom template
and custom furniture. It keeps the shipped palette on purpose: a starting
point, not a look to undo.

- `the-divide/` is an **open section** on a **custom template** (`divide`, the
  package at `examples/templates/divide/`: manifest, skeleton, brief, and its
  own `rs-side` furniture). It
  argues one contested question from both sides. The template enforces exactly two
  sides, each its own section, and the section runs `strict: true` so the per-side
  citation checks become hard BLOCKs. This is the reason to build a template:
  structure the proof guarantees, not the prose promises.
- `the-brief/` is a **rolling** nightly brief on the `brief` template, slugged
  by date.
- `docket/` is an **open section** (article) tracking AI legal cases, carried by a
  **custom furniture** piece, the case docket (`rs-docket`).
- `positions/` is an **open section** (article) that rotates a fixed watchlist of
  companies, one per night, business first.
- `kernels/` is a **sequence** course (article, lesson genre) using **custom
  furniture** for real code (`rs-code`) and the `hardware`/`benchmarks` tags.
- `inference-stack/` is a **collection** of appraisals (article) with per-item
  tags, `consult` sources, and a commented `required_docs` example.

Between them they exercise all four modes, both shipped templates plus a custom
one, three custom furniture components (`rs-code` with Prism-based syntax
highlighting, `rs-docket`, `rs-side`), the source policy (`consult` live,
`required_docs` and `sources_exclusive` shown as documented options), `cadence`
scheduling, word-band and source-floor calibration, tag fragments, and a voice
file.

Custom furniture lives in one of two scopes, all on the paper's own `rs-` prefix
(the `nb-` prefix is the engine's). Pieces shared across sections live
in `furniture/` (`catalog.md` + `styles.css`): `rs-code` and `rs-docket`.
A piece only one template renders lives in that template's folder:
`rs-side` in `templates/divide/`. `themes/newsroom.css` is only the palette,
unchanged from the shipped default. The engine concatenates it with every
furniture file into the published `assets/theme.css`. Each section's `prompt.md`
shows the markup. See [docs/customization.md](../docs/customization.md) for how
templates, themes, and furniture fit together.

The engine never reads this folder. To use any of it, copy files into your
`press/` and edit:

```sh
cp -r examples/series/kernels press/series/my-course
```

The upstream repo is engine-only and runs no site of its own. The maintainer
dogfoods by forking this repo like any other user.
