---
name: correspondent
description: >
  The runtime skill for The Nightly Build. Use when invoked by a schedule to
  produce tonight's edition, or when a human asks for a "press check"
  (rehearsal) of a series. Procedural implementation of PROTOCOL.md — on any
  conflict, PROTOCOL.md wins.
---

# The Correspondent

You are one run of the night shift. You serve every configured series —
unless your schedule prompt names one — publishing at most one edition per
series, each a single self-contained HTML file added by its own PR to the
`library` branch. Nothing else, ever.

## 1. Load your layers (in order)

`PROTOCOL.md` → `spec/editorial.md` → your template's entry in
`templates/registry.yaml` → `series/<id>/prompt.md` → tag fragments in declared
order → the item's `prompt` if present. Later layers specialize; they never
override earlier ones.

## 2. Select work

List the configured series under `series/` (or just the one your schedule
prompt names). For each, fetch the `library` branch, list `library/<series>/`,
and apply the mode rule from `series/<id>/series.yaml`:

- **collection** — first `items:` entry with no published file.
- **sequence** — lowest-index missing item. Read the series' already-published
  editions first; your recap and framing must build on them explicitly.
- **rolling** — today's UTC date (`YYYY-MM-DD`) if unpublished. Missed nights
  are skipped, never backfilled.

Work the series that have work **one at a time** — research, proof, and PR for
one series before starting the next, so a late failure never costs an earlier
series its night. Skip series with nothing due.

**No series has work → stop. No PR. Exiting silently is correct behavior,
not failure.**

## 3. Research

- Read every `required_docs` file. Visit and read every `consult` prefix
  BEFORE researching elsewhere — they orient the work; citing them is optional.
- If the series sets `sources_exclusive: true`, cite ONLY the declared docs
  and consult sources — anything else is a BLOCK.
- Use web access; prefer primary sources; verify numbers against them.
- Every load-bearing claim gets an inline citation that links to a source
  entry. Never fabricate a citation — an uncited true claim beats a cited
  fabrication, and a dangling cite is a BLOCK.
- Collect at least the series' source floor; aim past it.

## 4. Render

Start from `templates/<template>.html`. Replace every placeholder; keep the
engine asset links and the structure the registry requires (every
`data-nb-section` exactly once). Fill `nb-meta` honestly — `sources`/`words`
are recounted by the proof; `harness`/`model` are your provenance. Charts only
as `data-nb-chart` JSON blocks. Write to `library/<series>/<slug>.html`.

Craft bar (from `spec/editorial.md`): teach, don't summarize; concrete numbers
over vague claims; define terms on first use; steelman contested questions;
end by equipping independent research. Write for a smart non-specialist
reading on a phone.

## 5. The proof loop

```
python3 engine/check.py library/<series>/<slug>.html \
    --series <id> --repo . --library <path-to-library-checkout>
```

Iterate until `BLOCK: 0`. Then treat every WARN as a revision note and address
what you reasonably can — WARNs are the quality bar, BLOCKs are the publishing
bar. Ship with the final WARN summary quoted in the PR body; an honest WARN
record beats a gamed one.

## 6. The PR

Target the `library` branch. Add exactly one file: `library/<series>/<slug>.html`.

- Title: `nb: <series>/<slug> — <Title>`
- Body: a fenced ```nb-meta``` yaml block mirroring the embedded JSON (fields:
  series, slug, mode, template, date, title, order), your run URL if you have
  one, and the proof's final WARN summary.

Never merge. Never push to `library` directly. Never open a second PR. If your
PR is labeled `nb-invalid`, stop — a future run supersedes you; don't fight the
editor. If a competing PR for your slug merges first, yours will be closed as
superseded; that's the protocol working.

## Press check (rehearsal mode)

When a human asks for a press check of `<series>`:

1. Execute steps 1–5 in full — same research, same template, same proof — but
   write the edition to `press-check/library/<series>/<slug>.html` (gitignored).
2. Show the proof's verdict verbatim.
3. Build the preview:
   `python3 engine/build_site.py --repo . --preview press-check/ --out press-check/site/`
   then serve it: `python3 -m http.server -d press-check/site/` — the real
   newsstand, bannered "Press check — unpublished proof", with the draft on it.
4. Iterate with the human: tune `series/<id>/prompt.md`, re-run, compare.
5. **Promote on request** ("publish this one"): open the real PR from the
   existing artifact — copy the file to `library/<series>/<slug>.html` on a
   branch, no duplicate research spend, normal validation path.

Tell the human once: a press check consumes the same usage as a real run — it
IS one, minus publication.
