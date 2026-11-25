# Series: modes, cadence, and governing your paper

Each series lives in `press/series/<id>/` with `series.yaml` (rules),
`prompt.md` (editorial instructions), and an optional `sources/` directory. See
`examples/series/` for working configurations.

Per-series model and effort overrides live under `production:` in `series.yaml`
(see [Production](production.md)). `production:` is independent of `strict` and
never removes an editorial role.

## The four modes

| Mode         | You declare           | Each scheduled UTC date publishes                                   | Ends                 |
| ------------ | --------------------- | ------------------------------------------------------------------- | -------------------- |
| `collection` | An `items` list       | Next unpublished item, or a random one with `selection: random`     | When list finishes   |
| `sequence`   | An ordered syllabus   | Lowest-numbered missing item, building on earlier published lessons | When syllabus ends   |
| `rolling`    | Nothing (date-keyed)  | Today's UTC date                                                    | Never (until paused) |
| `open`       | A beat in `prompt.md` | A new topic picked by the orchestrator within the beat              | Never (until paused) |

- **Templates:** every mode declares either `template: <id>` or
  `templates: [<id>, ...]` (mutually exclusive). With multiple templates, the
  orchestrator picks the best fit per article and records it in `nb-meta`.
- **Genres:** most sections use the `article` template and define their genre
  (dossier, chronicle, appraisal) via `prompt.md` and `templates/FURNITURE.md`.
- **Daily cap:** scheduled runs produce at most one article per series per UTC
  date. Configure separate `open` series to publish multiple pieces per night.
  Requested articles have no per-day cap.
- **Open commission queue:** an `open` series may declare `items:`. Queued items
  must publish (in any order) before the series resumes picking its own topics;
  the proof enforces this queue.

## Cadence, pausing, and sections

```yaml
cadence: daily # default | weekdays | weekends | manual | [mon, thu]
paused: true # skip in scheduled runs; keep archive published
section: Foundations # optional shelf on Sections page and front-page kickers
```

| Key       | Contract                                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------- |
| `cadence` | Evaluated in **UTC** by `nb duty` (`rolling` slugs also use UTC date). One schedule runs all series.          |
| `paused`  | Halts scheduled work; proof rejects new articles while `true`. Archive stays live.                            |
| `section` | Single-level shelf grouping on the Sections page and in kickers. Completed/paused series group automatically. |

`cadence: manual` works with any mode and is never scheduled by `nb duty`.
`collection`, `sequence`, and `rolling` keep their item/date rules; an `open`
manual series accepts any slug, treating `items` as unenforced suggestions.

## Quality and sources

```yaml
bands:
  words: [900, 3000]
  items: [3, 8]
  flex_sections: [1, 5]
min_sources: 8
strict: true
```

| Key                 | Default / behavior                                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------------------ |
| `bands`             | Replaces template recommendations field by field (or omits defaults).                                  |
| `min_sources`       | Floor on cited sources. Defaults to `8` (`longread`) or `5` (`shortread`); set `0` to disable.         |
| `strict`            | Promotes proof warnings to blocks, except advisory warnings marked non-promotable.                     |
| `required_docs`     | Repo-relative paths that **must** be cited. Links resolve to `main` on GitHub (never copied to Pages). |
| `consult`           | Repo-relative background docs agents must read but need not cite.                                      |
| `sources_exclusive` | Restricts research exclusively to configured files (forbids external web research).                    |

## Source composition

`min_sources` only counts total citations. To constrain the mix of primary vs.
secondary evidence, use `sources_by_kind` and `per_item_sources`, which count
the `data-nb-kind` attribute on each source entry:

- **Primary:** directly supports the claim (filing, ruling, paper).
- **Secondary:** reports on a primary independently (a lab's blog post about its
  own paper is not independent).

```yaml
sources_by_kind: # article-wide mix, any series
  primary: [4, null] # null = no upper bound
  secondary: [2, null]

per_item_sources: # requires every allowed template to use cite_rule: per-item
  primary: [1, 1]
  secondary: [1, 2]
```

Rules enforced by `nb validate` and `nb check`:

- Both keys always **BLOCK** on violation regardless of `strict`.
- `per_item_sources` fails `nb validate` if any allowed template uses
  `per-section` citations.
- Either key fails `nb validate` if any allowed template omits `data-nb-kind` in
  its skeleton.
- Once either key is set, any source without `data-nb-kind` blocks.

The proof counts declared kinds without judging domain names (since a lab blog
and paper can live on different domains, while an independent journalist can
share a journal's domain). The researcher records the classification rationale
and the editor's skeptic read audits it.

## Rubrics

Reviewing series can pin scored criteria in `series.yaml`:

```yaml
rubric:
  - id: capability # matches data-nb-criterion in article HTML
    name: Capability # visible label
    note: Judged against its own claims. # optional writer brief
  - id: evidence
    name: Evidence
    note: Independent tests, never the vendor's demo.
```

- **Markup:** rows carry `data-nb-criterion` (a pinned `id` or a fit-for-subject
  slug added by the writer) and integer `data-score` (`0`–`5`). Rendered
  `nb-rubric-score` text must match `data-score`, and each row's justification
  carries an inline citation.
- **Checks:** `B-RUBRIC` always blocks (regardless of `strict`) on a missing
  pinned criterion, zero rows, duplicate/malformed slug, out-of-range score, or
  mismatched meter text. Uncited rows raise `W-RUBRIC` (blocks under `strict`).
- **Scope:** attribute-driven, so it works on any template (typically `article`
  plus rubric furniture from `templates/FURNITURE.md`). Even without `rubric:`
  configured, any rendered rubric rows are still integrity-checked.

## Pinning a voice guide

```yaml
voice_guide: voice-guide.md # path relative to press/series/<id>/
```

Pinning a guide skips the writing coach for every article in the series (the
largest available usage reduction). `nb start-article` copies the pinned file
into `writing-coach/01/voice-guide.md` with provenance metadata so the article
record remains complete. `nb validate` fails if the file is missing.

Keep pinned guides timeless and article-agnostic; repetition guards against
recent articles still reach the writer via the commission brief. See
[Appearance and voice](../guides/customize/appearance-and-voice.md) and
[Production](production.md).

## Manual commissions and day-to-day edits

Every manual article belongs to a configured series (and item, when required by
its mode) and crosses the normal Article PR gate. A merged article dated today
(UTC) marks that series complete for today's scheduled run; an open PR does not.
See [Publish an article now](../guides/publish/publish-now.md).

Day-to-day changes ("pause frontier-compute", "make the wildcard section
weekly", "commission a deep dive on ASML") are small validated diffs on `main`
checked with `nb validate`.
