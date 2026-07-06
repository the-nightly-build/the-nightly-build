# The Nightly Build — Agent Protocol
Protocol-Version: 1.0

You are one run of the night shift for this repository. This document is the complete
contract. If anything else you read conflicts with it, this document wins.

## The contract

1. **One edition, maximum.** Your job is to research and publish at most ONE edition.

2. **Read your layers, in order.** (Later layers specialize style and subject; they never
   override rules in this file.)
   1. This file.
   2. `spec/editorial.md` — the global voice and quality bar.
   3. `templates/registry.yaml` — the entry for your series' template (length band,
      required sections, citation rule).
   4. `series/<id>/prompt.md` — the series' editorial instructions.
   5. Tag fragments listed in the series config, in declared order.
   6. The item-level `prompt`, if present.

3. **Select your work.** Your schedule prompt names your series. Fetch the `library`
   branch and list `library/<series>/`. Then apply the mode rule from
   `series/<id>/series.yaml`:
   - `collection`: the first entry in `items:` with no published file.
   - `sequence`: the lowest-index missing item. You MUST read the series' already
     published editions before writing — your edition builds on them explicitly.
   - `rolling`: today's UTC date (`YYYY-MM-DD`) if not yet published. Missed nights are
     skipped, never backfilled.
   **If there is no work, stop. Do not open a PR.**

4. **Honor required sources.** Read every file in the item's/series' `required_docs` and
   consult every `required_urls` prefix. Each required doc must be represented by a
   source entry carrying `data-nb-required="<id>"`; each required URL prefix by at least
   one matching source href.

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

8. **Open one pull request targeting the `library` branch** adding exactly your one file.
   - Title: `nb: <series>/<slug> — <Title>`
   - Body: a fenced ```nb-meta``` yaml block mirroring the embedded metadata, a link to
     your run if available, and the proof's final WARN summary.

9. **Boundaries.** Never merge. Never push to `library` directly. Never modify any other
   file. Never open a second PR. If your PR is labeled `nb-invalid`, a future run
   supersedes you; do not fight the editor.

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
