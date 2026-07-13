# examples/: a complete, working paper

A full paper configuration, kept as living documentation. The engine never
reads this folder. Copy pieces into your `press/` and edit:

```sh
cp -r examples/series/kernels press/series/my-course
```

- `the-divide/`: an open section on a custom template (the package at
  `templates/divide/`). The template enforces exactly two sides and the
  section runs `strict: true`, so the per-side citation checks become hard
  BLOCKs. Build a template when the proof should guarantee structure.
- `the-brief/`: a rolling nightly brief on the `brief` template, slugged by
  date.
- `docket/`: an open section tracking AI legal cases, carried by the
  `rs-docket` furniture.
- `positions/`: an open section rotating a fixed watchlist, one company per
  night, business first.
- `kernels/`: a sequence course in the lesson genre, with `rs-code` listings
  and the `hardware`/`benchmarks` tags.
- `inference-stack/`: a collection of appraisals with per-item tags, live
  `consult` sources, and `required_docs` shown as a commented option.

Together they exercise all four modes, both shipped templates plus a custom
one, three furniture components, the source policy, `cadence` scheduling,
word-band and source-floor calibration, tag fragments, and a voice file. How
templates, themes, and furniture fit together is
[docs/customization.md](../docs/customization.md). The shipped palette in
`themes/newsroom.css` is kept unchanged on purpose.

The upstream repo is engine-only and runs no site of its own. The maintainer
dogfoods by forking this repo like any other user.
