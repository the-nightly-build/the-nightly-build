# examples/ — a complete, working press

A full press configuration, kept as living documentation: six series — one per
shipped template plus an **open desk** (`wildcard/`, where the agent
picks each night's topic and form within a beat) — the whole source policy
(`required_docs`, `consult`, `sources_exclusive`), rhythm controls
(`cadence`, `paused`, `selection`), a voice file, and commented-out advanced
options in every series.yaml.

The engine never reads this folder. To use any of it, copy files into your
`press/` and edit:

```
cp -r examples/series/ai-history press/series/my-history
```

The upstream repo is engine-only — it runs no press of its own. The
maintainer dogfoods by forking this repo like any other user.
