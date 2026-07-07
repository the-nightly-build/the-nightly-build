# The Nightly Build Agent Protocol
Protocol-Version: 1.1

You are one run of the night shift for this repository. This document is the complete
contract. If anything else you read conflicts with it, this document wins.

Runtime requirement: the engine scripts need Python 3.9+ and PyYAML. If a
script reports PyYAML missing, run `pip install pyyaml` and retry. With uv
available, `uv run engine/<script>.py` manages the dependency itself.

## The contract

1. **One edition per series, maximum.** A run serves the whole press, every
   series configured under `press/series/`, unless your schedule prompt names one
   specific series. For each series you serve, research and publish at most ONE
   edition, as its own pull request. Work series one at a time, completing each
   PR before starting the next, so a late failure never costs an earlier series
   its night.

2. **Read your layers, in order.** (Later layers specialize style and subject; they never
   override rules in this file.)
   1. This file.
   2. `spec/editorial.md`: the house voice and quality bar.
   3. `press/editorial.md`: the press owner's voice, if present. It specializes
      the house style.
   4. The registry entry for your series' template: `templates/registry.yaml`,
      overlaid by `press/templates/registry.yaml` (press entries win). The
      template file itself is `press/templates/<t>.html` if it exists, else
      `templates/<t>.html`.
   5. `press/series/<id>/prompt.md`: the series' editorial instructions.
   6. Tag fragments listed in the series config, in declared order.
   7. The item-level `prompt`, if present.

3. **Select your work.** Fetch the `library` branch, then run the duty oracle:
   `python3 engine/duty.py --repo . --library <path-to-library-checkout>`
   It applies every scheduling rule deterministically (per-series `cadence`,
   `paused`, completion, already-published-tonight) and prints the series due,
   with what to publish:
   - `collection`: one of the listed `candidates` (the next item in config
     order; every unpublished item when the series sets `selection: random`).
   - `sequence`: the listed `slug`. You MUST read the series' already published
     editions before writing; your edition builds on them explicitly.
   - `rolling`: today's UTC date (the listed `slug`). Missed nights are skipped,
     never backfilled.
   - `open`: an editor-run desk. If `commissions` lists slugs, publish one of
     them (its `items:` entry may carry a prompt and sources). Otherwise invent
     tonight's edition within the series' beat: read the desk's published
     editions first (never repeat a topic, build continuity), then choose the
     template that best fits from the series' declared choices (`templates:`,
     or its single `template:`) and coin a fresh slug (`[a-z0-9-]{1,64}`).
   **Serve only the series duty.py lists as due. If nothing is due, stop. Do
   not open a PR. Exiting silently is correct behavior.**

4. **Honor the source policy.** Three controls, per series and per item:
   - `required_docs`: committed files you MUST read; each must be represented
     by a source entry carrying `data-nb-required="<id>"`.
   - `consult`: URL prefixes you MUST visit and read BEFORE researching
     elsewhere; they orient the work. Citing them is optional.
   - `sources_exclusive: true`: every source entry must come from the declared
     set (required docs and consult prefixes). Cite nothing else; an outside
     source is a BLOCK.

5. **Research properly.** Use web access. Verify claims against primary sources. Every
   load-bearing claim carries an inline citation that links to a source entry. Never
   fabricate a citation. Meet the source floor for your series.

6. **Render exactly one self-contained HTML file** from your series' template:
   - Fill every `data-nb-section` the registry requires for the template.
   - Embed the `nb-meta` JSON block (schema below).
   - Charts only as declarative `<script type="application/json" data-nb-chart>` blocks.
   - No scripts other than those JSON blocks and the template's own
     `<script src="../../assets/nb.js">` (the engine runtime; keep it, never add
     others). No iframes/objects/embeds. No inline event handlers. No `javascript:`
     URLs. External references only to the engine assets path and Google Fonts.
   - File path: `library/<series>/<slug>.html`.

7. **Run the proof and iterate:**
   `python3 engine/check.py library/<series>/<slug>.html --series <id> --repo . --library <path-to-library-checkout>`
   Revise until `BLOCK: 0`. Treat every WARN as a revision note and address what you
   reasonably can. WARNs are the quality bar; BLOCKs are the publishing bar.

8. **Open one pull request per edition, targeting the `library` branch**, each
   adding exactly one file.
   - Title: `nb: <series>/<slug> - <Title>`
   - Body: a fenced ```nb-meta``` yaml block mirroring the embedded metadata, a link to
     your run if available, and the proof's final WARN summary.

9. **Boundaries.** Never merge. Never push to `library` directly. Never modify any other
   file. Never open a second PR for the same series. If your PR is labeled
   `nb-invalid`, a future run supersedes you; do not fight the editor.

## nb-meta

Embed in `<head>`:

```html
<script type="application/json" id="nb-meta">
{
  "protocol": "1.0",
  "series": "semiconductors",
  "slug": "micron",
  "template": "dossier",
  "title": "Micron Technology: The Scarcest Commodity in AI",
  "mode": "collection",
  "order": null,
  "date": "2026-07-06",
  "tags": ["equity"],
  "sources": 24,
  "words": 4100,
  "reading_minutes": 18,
  "dek": "One-sentence teaser shown on the newsstand card.",
  "harness": "claude-code-routine",
  "model": "claude-fable-5"
}
```

Field notes: `mode` is one of `collection | sequence | rolling | open`. `order` is the
1-based item index for `sequence` mode, else null. `date` is the UTC date of your run.
For `open` mode, `template` must be one of the series' declared choices. `sources` and
`words` are your self-measurements (the proof recounts; >20% deviation is a WARN).
`harness`/`model` are honest provenance.

## Quality creed

Editions teach rather than summarize. Every load-bearing claim carries a citation the
reader can follow. The goal is to equip the reader to go deeper on their own.
