# The Nightly Build — Agent Protocol
Protocol-Version: 1.0

You are one run of the night shift for this repository. This document is the complete
contract. If anything else you read conflicts with it, this document wins.

## The contract

1. **One edition per series, maximum.** A run serves the whole press — every
   series configured under `series/` — unless your schedule prompt names one
   specific series. For each series you serve, research and publish at most ONE
   edition, as its own pull request. Work series one at a time, completing each
   PR before starting the next, so a late failure never costs an earlier series
   its night.

2. **Read your layers, in order.** (Later layers specialize style and subject; they never
   override rules in this file.)
   1. This file.
   2. `spec/editorial.md` — the global voice and quality bar.
   3. `templates/registry.yaml` — the entry for your series' template (length band,
      required sections, citation rule).
   4. `series/<id>/prompt.md` — the series' editorial instructions.
   5. Tag fragments listed in the series config, in declared order.
   6. The item-level `prompt`, if present.

3. **Select your work.** For each series you serve, fetch the `library` branch
   and list `library/<series>/`. Then apply the mode rule from
   `series/<id>/series.yaml`:
   - `collection`: the first entry in `items:` with no published file.
   - `sequence`: the lowest-index missing item. You MUST read the series' already
     published editions before writing — your edition builds on them explicitly.
   - `rolling`: today's UTC date (`YYYY-MM-DD`) if not yet published. Missed nights are
     skipped, never backfilled.
   **Skip any series with no work. If no series has work, stop. Do not open a PR.**

4. **Honor the source policy.** Three controls, per series and per item:
   - `required_docs` — committed files you MUST read; each must be represented
     by a source entry carrying `data-nb-required="<id>"`.
   - `consult` — URL prefixes you MUST visit and read BEFORE researching
     elsewhere; they orient the work. Citing them is optional.
   - `sources_exclusive: true` — every source entry must come from the declared
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
     `<script src="../../assets/nb.js">` (the engine runtime — keep it, never add
     others). No iframes/objects/embeds. No inline event handlers. No `javascript:`
     URLs. External references only to the engine assets path and Google Fonts.
   - File path: `library/<series>/<slug>.html`.

7. **Run the proof and iterate:**
   `python3 engine/check.py library/<series>/<slug>.html --series <id> --repo . --library <path-to-library-checkout>`
   Revise until `BLOCK: 0`. Treat every WARN as a revision note and address what you
   reasonably can. WARNs are the quality bar; BLOCKs are the publishing bar.

8. **Open one pull request per edition, targeting the `library` branch**, each
   adding exactly one file.
   - Title: `nb: <series>/<slug> — <Title>`
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

Field notes: `order` is the 1-based item index for `sequence` mode, else null. `date` is
the UTC date of your run. `sources` and `words` are your self-measurements (the proof
recounts; >20% deviation is a WARN). `harness`/`model` are honest provenance.

## Quality creed

Editions teach rather than summarize. Every load-bearing claim carries a citation the
reader can follow. The goal is to equip the reader to go deeper on their own.
