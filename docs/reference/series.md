# Series: modes, cadence, and governing your paper

A series is one section of your paper: a directory under
`press/series/<id>/` holding `series.yaml` (the rules), `prompt.md` (the
editorial instructions), and an optional `sources/` directory. Working
examples of everything below live in `examples/series/`.

Role model and effort guidance lives paper-wide in `press/production.yaml` and
may be overridden for one section under `series.yaml`'s `production:` key. See
[production.md](production.md). It is separate from editorial `strict` and
never removes a role.

## The four modes

| Mode         | You declare                   | Each scheduled UTC date publishes                                        | Ends                      |
| ------------ | ----------------------------- | ------------------------------------------------------------------------ | ------------------------- |
| `collection` | an item list                  | the next unpublished item, or any of them with `selection: random`       | when the list is done     |
| `sequence`   | an ordered syllabus           | the lowest-numbered missing item, building on the published ones         | when the syllabus is done |
| `rolling`    | nothing; the date is the item | today's UTC date                                                         | never, until paused       |
| `open`       | a beat in prompt.md           | a topic the agent picks within the beat, in one of the series' templates | never, until paused       |

The mode controls scheduling only. Every mode may declare one `template:` or
several `templates:`, and the two keys are mutually exclusive. A
multi-template series lets the orchestrator choose the best package for each
article, and the per-article choice is recorded in `nb-meta`. There is no
template-level mode allowlist.

An open series needs the least curation. You describe a beat, the
orchestrator reads the section's back catalog, picks something new, and
chooses a template from the series' declared choices. One article per series
per UTC date is the invariant, so a paper that wants several varied reads a
day runs several open sections with distinct beats.

The engine does not define genres. Nearly every section runs the `article`
template. What makes its articles dossiers, chronicles, lessons, or
appraisals is the series prompt: the outline conventions it keeps and the
furniture that carries them (`templates/FURNITURE.md`). Every section in
`examples/` defines its genre this way.

An open section may still carry `items:`. That list is its commission queue.
Anything you add must be published, in any order, before the section returns
to picking its own topics. The proof enforces the queue, so "cover X next" is
a one-line edit.

## Cadence, pausing, and sections

```yaml
cadence: daily # default | weekdays | weekends | manual | [mon, thu]
paused: true # skip this series entirely; the archive stays up
section: Foundations # optional shelf on the Sections page and in kickers
```

One schedule can run the whole paper because each series owns its cadence.
The scheduled run asks `nb duty` what is due for the selected UTC date, so a
weekly deep-dive section and a daily brief coexist under the same schedule.

Duty uses UTC everywhere. A `[mon, thu]` cadence means the run's UTC weekday,
and `rolling` slugs the article by the run's UTC date, so a cron hour near
midnight can land a "Monday" run on your local Sunday evening.

`paused: true` stops new articles while the archive stays published. The
proof refuses new articles for a paused series.

`cadence: manual` is valid for every mode and is never scheduled by `nb duty`.
Collection and sequence keep their configured-item rules, and rolling keeps
its date identity. An open manual series requires the article slug to match a
configured `items` entry in both initialization and CI.

`section:` groups series under a heading on the Sections page, and front-page
kickers show the heading before the series' name. It is the only level of
grouping. Without it, series list flat. Completed and paused series appear
under "Completed and paused" automatically.

## Quality and sources

Per series, `bands:` optionally replaces template defaults field by field:

```yaml
bands:
  words: [900, 3000]
  items: [3, 8]
  flex_sections: [1, 5]
```

Template bands are recommendations. A series may loosen or tighten any
supplied band, add a band where the template has no default, or omit `bands`
for no geometry default.

`min_sources` is a separate source floor. It defaults to `8` for a longread
template and `5` for a shortread one, and an explicit `min_sources: 0`
disables that default. `strict: true` promotes proof warnings to blocks,
except the few advisory warnings the proof marks non-promotable.

The source policy keys are `required_docs`, `consult`, and
`sources_exclusive`. Required documents must be cited. Consulted documents
must be read but need not appear. An exclusive source set forbids research
beyond the configured files. Working configurations live under
`examples/series/`.

A `required_docs` citation stores the file's repo-relative path. The
published site links that path to the file on the fork's `main` branch.
Private repository links use GitHub's normal authentication, and the file is
never copied into Pages.

## Source composition

`min_sources` only counts. It cannot see what kind of sources came in, so six
items lifted from a single day's arXiv listing clear a floor of six. Two keys
constrain the mix instead. They read the kind each source declares in the
markup (`data-nb-kind`). A **primary** owns the claim (the filing, the
ruling, the paper). A **secondary** reports on a primary from outside it.
What separates them is independence: a lab's post about its own paper is an
extension of that paper, never a second source.

```yaml
sources_by_kind: # the composition of what the article cites, any series
  primary: [4, null] # at least four primaries; null means no ceiling
  secondary: [2, null]

per_item_sources: # only when every selected template uses cite_rule: per-item
  primary: [1, 1] # every item: exactly one document that owns its claim
  secondary: [1, 2] # and one or two independent reads of it
```

`per_item_sources` applies uniformly to every item, however many items the
article's writer chose. Both bands are BLOCKs regardless of `strict`. Two
configurations are errors caught by `nb validate` before a scheduled run
trips on them: a `per_item_sources` on a series that may cite per section,
and a source-composition band on a series whose template ships source entries
without `data-nb-kind`. Once either band is set, a source that declares no
kind blocks, because an undeclared kind cannot be counted against the mix. A
series that sets neither band has no kind requirements.

The proof counts the kinds the article declares. It does not judge them, and
there is no rule about hosts or domains: a paper and its own lab's write-up
can sit on two websites, and a journal's reporters covering a paper it
published are genuinely independent of that paper's authors while sharing
their domain. No counter can tell those apart. The researcher's evidence
record makes the call and records the reason, and the editor's skeptic read
audits it. A source labeled `secondary` that is the primary's own author
speaking again is a broken claim about the sourcing, and only that review
catches it.

## Rubrics

A reviewing series can pin the criteria every one of its articles must score:

```yaml
rubric: # every article scores these; the writer adds fit-for-subject rows
  - id: capability # the slug rubric rows carry in data-nb-criterion
    name: Capability # what the reader sees
    note: Judged against its own claims. # optional brief to the writer
  - id: evidence
    name: Evidence
    note: Independent tests, never the vendor's demo.
```

An article renders the rubric as rows carrying `data-nb-criterion` (the
pinned id, or a fit-for-subject slug the writer adds) and `data-score`, an
integer 0–5. The rendered `nb-rubric-score` text must agree with the
attribute, and each row's one-line justification carries an inline citation.

Row integrity BLOCKs regardless of `strict` (`B-RUBRIC`): a dropped pinned
criterion, no rows at all, a duplicate or malformed slug, a score off the
scale, or a meter text that disagrees with its attribute. These are contract
failures, so `strict` cannot relax them. An uncited row is `W-RUBRIC`, a
BLOCK under `strict`. Whether a score is deserved is editorial judgment,
carried by the cited justification and audited by the editor.

The contract is attribute-driven, so it works on any template. A review
series is a genre: run the `article` template, pin the criteria here, and let
the prompt name the rubric furniture (`templates/FURNITURE.md`). A series
with no `rubric:` pins nothing, but any rubric rows an article renders are
still integrity-checked.

## Pinning a voice guide

By default the writing coach studies exemplars for every article and writes
that article's voice guide. A series whose sound is already settled can state
the standard once instead:

```yaml
voice_guide: voice-guide.md # a path under press/series/<id>/
```

The coach does not run for a series that pins a guide. `nb start-article`
copies the pinned file into the article's `writing-coach/01/voice-guide.md`
with a brief recording where it came from, so the production record still
names the standard that governed the article. `nb validate` fails when the
path names a missing file, because a silently absent guide would cost the
series the voice it had settled on.

The writing coach is the only optional role, and it is the largest usage
reduction available to a press. See
[Appearance and voice](../guides/customize/appearance-and-voice.md) for how to
write one and [Production](production.md) for what it saves.

A pinned guide is durable and says nothing about any single article. The
habits an article should avoid inheriting from recent work reach the writer
through its brief instead, so pinning never weakens the repetition guard.

## Manual commissions

Every manually triggered article still belongs to a configured series and,
where that mode requires it, a configured item. It uses the normal production
and Article PR contract. A merged article whose nb-meta date is today's UTC
date causes that series to idle for the rest of the date. An open PR is not
published state and does not deduplicate the next run. See
[Publish an article now](../guides/publish/publish-now.md).

## Governing without YAML

Day to day you steer by talking to your agent: "pause frontier-compute",
"make the wildcard section weekly", "commission a deep dive on ASML", "less
policy in the brief for a while" (a prompt.md edit). Every change is one
small diff on `main`, validated by `nb validate`.
