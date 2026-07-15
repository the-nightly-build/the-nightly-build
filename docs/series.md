# Series: modes, rhythm, and governing your paper

A series is one section of your paper: a directory under
`press/series/<id>/` holding `series.yaml` (the rules), `prompt.md` (the
editorial instructions), and an optional `sources/` directory. Working
examples of everything below live in `examples/series/`.

## The four modes

| Mode         | You declare                   | Each night publishes                                                         | Ends                      |
| ------------ | ----------------------------- | ---------------------------------------------------------------------------- | ------------------------- |
| `collection` | an item list                  | the next unpublished item, or any of them with `selection: random`           | when the list is done     |
| `sequence`   | an ordered syllabus           | the lowest-numbered missing item, building on the published ones             | when the syllabus is done |
| `rolling`    | nothing; the date is the item | today's UTC date                                                             | never, until paused       |
| `open`       | a beat in prompt.md           | a topic the agent picks within the beat, in the template it judges fits best | never, until paused       |

Open mode is the hands-off paper. You describe a beat, the night shift
reads the section's back catalog, picks something new, and chooses its template
from the series' declared `templates:` list (or its single `template:`).
For several varied reads a day without curating items, run several open
sections with distinct beats. One article per series per night is the
invariant, so sections are how a paper gets breadth.

Genre lives in the prompt, not the engine. Nearly every section runs on the
`article` template; what makes its articles dossiers, chronicles, lessons, or
appraisals is the series prompt: the outline conventions it keeps and the
furniture that carries them (`templates/FURNITURE.md`). Every section in
`examples/` demonstrates a genre this way.

Commissioning: an open section may still carry `items:`. That list is its
commission queue. Anything you add must be published, in any order, before
the section freestyles again. The proof enforces this, so "cover X next" is a
one-line edit with a guarantee.

## Rhythm and shelving

```yaml
cadence: daily # default | weekdays | weekends | [mon, thu]
paused: true # skip this series entirely; the archive stays up
section: Foundations # optional shelf on the Sections page and in kickers
```

Cadence is why one nightly schedule is enough forever: the run asks
`engine/duty.py` what is due tonight, so a weekly deep-dive section and a
daily brief coexist under the same schedule. Duty reckons in UTC: a
`[mon, thu]` cadence means the run's UTC weekday, and `rolling` slugs the
article by the run's UTC date, so a cron hour near midnight can land a
"Monday" run on your local Sunday evening. Pausing is the vacation switch: the
proof refuses new articles for a paused series.

`section:` is the one level of hierarchy a paper needs. Series group under
their `section:` heading on the Sections page, and front-page kickers show the
`section:` heading before the series' name. Without it, series list flat. Completed and
paused series sink into "In the stacks" automatically.

## Quality and sources

Per series: `words: [low, high]` (may tighten, never loosen below the
template's registry floor), `min_sources` (the citation floor; defaults to
`8` for a longread template and `5` for a shortread one, so you only set it to
raise the bar), `strict: true` (every WARN becomes a BLOCK), `autopublish: true`
(the desk auto-merges a clean PR; the default is a human merge), and the source
policy: `required_docs`, `consult`, and
`sources_exclusive`, described in the [README](../README.md) and
demonstrated across `examples/series/`.

## Source composition

`min_sources` counts. It cannot see what kind of sources came in, so six items
lifted from a single day's arXiv listing clear a floor of six. Two keys constrain
the mix instead. They read the kind each source declares in the markup
(`data-nb-kind`), which PROTOCOL step 4 defines: a **primary** owns the claim
(the filing, the ruling, the paper), and a **secondary** reports on a primary
from outside it. The distinction is independence, not document type, so a lab's
post about its own paper is an extension of that paper, never a second source.

```yaml
sources_by_kind: # the composition of what the article cites, any series
  primary: [4, null] # at least four primaries; null means no ceiling
  secondary: [2, null]

per_item_sources: # only on a per-item template (the brief's cite_rule)
  primary: [1, 1] # every item: exactly one document that owns its claim
  secondary: [1, 2] # and one or two independent reads of it
```

`per_item_sources` applies uniformly to every item, so it holds however many
items the night's writer chose. Both bands are BLOCKs regardless of `strict`,
and a `per_item_sources` on a series that may cite per section is a
configuration error, caught by `engine/validate_config.py` rather than at 2am —
as is a band set on a series whose template ships source entries without
`data-nb-kind`. Once either band is set, a source that declares no kind blocks:
a source that will not say what it is escapes every rule written about the mix.
A series that sets neither band never asks.

The proof counts the kinds the article declares. It does not judge them, and
there is no rule here about hosts or domains: a paper and its own lab's write-up
of it can sit on two websites, and a journal's news desk reporting on a paper it
published is genuinely independent of that paper's authors while sharing their
domain. No counter can tell those apart. The research log makes the call and
records the reason, and the editor's skeptic read audits it. A source labeled
`secondary` that is the primary's own author speaking again is a broken claim
about the sourcing, and it is caught by a reader or not at all.

## Commissioning extras by hand

"One article per series per night" disciplines the night shift, not you.
Any PR to `library` that adds one isolated article bundle and passes the proof is a legitimate
article, whoever commissioned it. Ask your agent for three extra pieces
this afternoon and tonight's build is simply bigger. The recommended flow
is press check, then promote, so you read the rehearsal before it
publishes. The desk applies the same validation either way.

Three rules of the road:

- Every article needs a home. The proof rejects articles for series that do
  not exist in `press/series/`, so a brand-new topic means a config change
  on `main` first. Usually that is a one-line commission into an open
  section's queue or a new item in a collection. A new series is the last
  resort.
- Extras count as tonight's article, on the same UTC day. The scheduled run
  skips a series only when a hand-published article's nb-meta date equals the
  run's own UTC date. Publish an extra late in the afternoon your time and a
  cron that fires after UTC midnight sees a new date: the series reads as due
  again and the run publishes a second item that night. Commission close to the
  run, or expect the automatic piece as well.
- Merge the night's PR before the next run. Duty dedupes against merged
  `library` state, not open PRs, so a series whose PR is still unmerged when the
  next run fires is re-selected and produces a second PR for the same work. Once
  the first PR merges the duplicate becomes a file modification and the proof
  BLOCKs it, but the wasted research and the open-PR pileup are real.
  `autopublish` series merge themselves; a human-merge series needs you to merge
  it in time.

## Governing without YAML

Day to day you steer by talking to your agent: "pause frontier-compute",
"make the wildcard section weekly", "commission a deep dive on ASML", "less
policy in the brief for a while" (a prompt.md edit). Every change is one
small diff on `main`, validated by `uv run engine/validate_config.py --repo .`.
