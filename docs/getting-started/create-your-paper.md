# Create your paper

A **paper** is the published site; its **press** is the configuration under
`press/` that produces it. A fresh press has three series: **Dispatches** (what
you ask for) plus **News Brief** and **Feature** (scheduled runs, defaulting to
technology).

## Personalize the default paper

Ask your AI to make the paper yours or change its coverage. It asks two
questions, one at a time: what news you want and what you want to read about.
Your answers rewrite the opening coverage paragraph of each series prompt (and
the reader sentence in `press/editorial.md` if relevant), leaving everything
else untouched. The change is validated, committed, and pushed to `main` for the
next scheduled run.

Requesting an article never triggers these questions; the article runs as-is
until you ask to customize the paper.

## Design a paper from scratch

When you want custom beats, voice, or rhythm, start a design conversation with
your assistant. It proposes directions, tests them with sample ideas and
counterexamples, and simulates a first week before asking for approval. The
press encodes at least:

- purpose and target reader
- each series's scope and explicit exclusions
- evidence standards and qualifying sources
- voice, tested against concrete examples
- cadence, length, and visual density
- runtime billing model and sustainable production budget

This produces a compact configuration tree:

```text
press/
├── site.yaml
├── editorial.md
├── production.yaml
└── series/<id>/
    ├── series.yaml
    └── prompt.md
```

See [Series reference](../reference/series.md) for the schema and
[Appearance and voice](../guides/customize/appearance-and-voice.md) for custom
themes and voice guides.

Commit and push the validated press to `main`. Both CI validation and scheduled
runs read `press/` from remote `main`, so uncommitted or unpushed changes have
no effect. Next: [Schedule publication](../guides/operate/schedule.md).
