# Create your paper

A paper is the published result. Its press is the configuration under `press/`
that produces it.

You do not need answers prepared. Start the conversation and expect the
assistant to propose directions, test them with representative article ideas and
counterexamples, and simulate a first week before asking for approval. Every
decision the press encodes gets settled this way. At a minimum:

- what the paper is for and who reads it
- the territory each series owns, and what it refuses to cover
- what counts as evidence and which sources qualify
- how the paper should sound, tested against real examples
- the reading rhythm: how often, how long, how visual
- how the runtime is billed and how much production usage you can sustain

The output becomes a small configuration tree:

```text
press/
├── site.yaml
├── editorial.md
├── production.yaml
└── series/<id>/
    ├── series.yaml
    └── prompt.md
```

Use [Series reference](../reference/series.md) for the exact configuration
contract. Use
[appearance and voice](../guides/customize/appearance-and-voice.md) when the
editorial concept needs a distinct visual system.

Once the proposed press validates, commit it and push to `main`. The scheduled
run reads the press from the remote `main` branch, so a press that exists only
in a working tree publishes nothing. Then continue to
[scheduled-runtime verification](first-run.md) if you want to test the
automation before relying on it.
