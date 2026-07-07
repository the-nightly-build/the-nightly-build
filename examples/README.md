# examples/: a complete, working press

A full press configuration, kept as living documentation. Six desks show the
whole surface, including the parts a paper builds for itself: a custom template
and custom furniture. It keeps the shipped palette on purpose, so it is a
starting point, not a look to undo.

- `the-divide/` is an **open desk** on a **custom template** (`divide`, defined
  in `templates/registry.yaml` and `templates/divide.html`). It argues one
  contested question from every side. The template enforces at least two sides,
  each its own section, and the desk runs `strict: true` so the per-side
  citation checks become hard BLOCKs. This is the reason to build a template:
  structure the proof guarantees rather than the prose promises.
- `the-brief/` is a **rolling** nightly brief on the `brief` template, slugged
  by date.
- `docket/` is an **open desk** (article) tracking AI legal cases, carried by a
  **custom furniture** piece, the case docket (`rs-docket`).
- `positions/` is an **open desk** (article) that rotates a fixed watchlist of
  companies, one per night, business first.
- `kernels/` is a **sequence** course (article, lesson genre) using **custom
  furniture** for real code (`rs-code`) and the `hardware`/`benchmarks` tags.
- `inference-stack/` is a **collection** of appraisals (article) with per-item
  tags, `consult` sources, and a commented `required_docs` example.

Between them they exercise all four modes, both shipped templates plus a custom
one, three custom furniture components (`rs-code` with CSS-only syntax
highlighting, `rs-docket`, `rs-side`), the source policy (`consult` live,
`required_docs` and `sources_exclusive` shown as documented options), rhythm
controls (`cadence`, `paused`, `selection`), word-band and source-floor
calibration, tag fragments, a voice file, and commented advanced options in
every `series.yaml`.

Custom furniture has to live in a press theme file, because that is the only
CSS the engine publishes for a press. `themes/newsroom.css` keeps the shipped
palette unchanged and adds the components below the tokens, on the press's own
`rs-` prefix (the `nb-` prefix is the engine's); each desk's `prompt.md` shows
the markup. See [docs/customization.md](../docs/customization.md) for how
templates, themes, and furniture fit together.

The engine never reads this folder. To use any of it, copy files into your
`press/` and edit:

```sh
cp -r examples/series/kernels press/series/my-course
```

The upstream repo is engine-only; it runs no press of its own. The maintainer
dogfoods by forking this repo like any other user.
