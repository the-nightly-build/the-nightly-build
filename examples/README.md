# examples/: a complete, working paper

A full paper configuration, kept as living documentation. The engine never reads
this folder. Copy pieces into your `press/` and edit:

```sh
cp -r examples/series/kernels press/series/my-course
```

`production.yaml` makes the balanced cost profile visible. Presses that omit it
receive the same cost-aware default. Set `profile: inherit` to keep the harness
model for every role.

- `the-divide/`: an open section on the shipped `unbiased` template, run with
  `strict: true` so the per-side citation checks become hard BLOCKs.
- `the-brief/`: a rolling nightly brief on the `brief` template, slugged by
  date.
- `docket/`: an open section tracking AI legal cases, carried by the `rs-docket`
  furniture.
- `positions/`: an open section rotating a fixed watchlist, one company per
  night, business first.
- `kernels/`: a sequence course on the `article` template, with `nb-code`
  listings and the `hardware`/`benchmarks` tags.
- `inference-stack/`: a collection of appraisals with per-item tags, live
  `consult` sources, and `required_docs` shown as a commented option.

Together they exercise all four modes, three shipped templates (`article`,
`brief`, and `unbiased`), multiple furniture components, the source policy,
`cadence` scheduling, word-band and source-floor calibration, tag fragments, and
a voice file. The [furniture guide](../docs/guides/customize/furniture.md)
explains how templates, themes, and furniture fit together. The shipped palette
in `themes/newsroom.css` is kept unchanged on purpose.

The upstream repo is engine-only and runs no site of its own. The maintainer
dogfoods by forking this repo like any other user.
