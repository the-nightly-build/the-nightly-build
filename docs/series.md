# Series — modes, rhythm, and governing your paper

A series is one section of your paper: a folder under `press/series/<id>/`
holding `series.yaml` (the rules), `prompt.md` (the editorial instructions),
and optional `sources/`. Working examples of everything below live in
`examples/series/`.

## The four modes

| Mode | You declare | Each night publishes | Ends? |
|---|---|---|---|
| `collection` | an item list | the next unpublished item (or any, with `selection: random`) | when the list is done |
| `sequence` | an ordered syllabus | the lowest-numbered missing item, building on the published ones | when the syllabus is done |
| `rolling` | nothing — the date is the item | today's UTC date | never (until paused) |
| `open` | a *beat* in prompt.md | a topic the agent picks within the beat, in the template it judges fits best | never (until paused) |

**Open mode is the hands-off paper.** You describe a beat ("under-covered
corners of the AI stack"); the night shift reads the desk's back catalog,
picks something new, and chooses its form from the series' declared
`templates:` choice list (or its single `template:`). Want ~6 varied reads a
day without curating items? Run several open desks with distinct beats — one
edition per series per night is the invariant, so desks are how a paper gets
breadth.

**Commissioning:** an open desk may still carry `items:` — that's its
commission queue. Anything you add must be published (in any order, with its
own prompt/sources if given) before the desk freestyles again. The proof
enforces this, so "cover X next" is a one-line edit with a guarantee.

## Rhythm and shelving

```yaml
cadence: daily        # default · weekdays · weekends · [mon, thu]
paused: true          # skip this series entirely; the archive stays up
section: Foundations  # optional shelf on the Sections page (and in kickers)
```

`section:` is the one level of hierarchy a paper ever needs: desks group
under section headings on the Sections page, and front-page kickers read
"Foundations — Landmark Papers". Without it, desks list flat. Completed and
paused desks sink into "In the stacks" automatically.

Cadence is why one nightly schedule is enough forever: the run itself asks
`engine/duty.py` what is due tonight, so a weekly deep-dive desk and a daily
brief coexist under the same schedule. Pausing is the vacation switch — the
proof refuses new editions for a paused series, so nothing publishes by
accident.

## Quality and sources

Per series: `words: [low, high]` (may tighten, never loosen below the
template's registry floor), `min_sources`, `strict: true` (every WARN becomes
a BLOCK), `autopublish: false` (a human merges instead of the editor), and
the source policy — `required_docs`, `consult`, `sources_exclusive` — described
in the [README](../README.md) and demonstrated across `examples/series/`.

## Commissioning extras by hand

"One edition per series per night" disciplines the *night shift*, not you.
Any PR to `library` that adds one file and passes the proof is a legitimate
edition, whoever commissioned it — ask your agent for three extra pieces this
afternoon and tonight's build is simply bigger. The recommended flow is
**press check → promote** (you read the rehearsal before it publishes); the
editor applies the exact same validation either way.

Two rules of the road:

- **Every edition needs a home.** The proof rejects editions for series that
  don't exist in `press/series/`, so a brand-new topic means a config change
  on `main` first — usually just a one-line commission into an open desk's
  queue, or a new item in a collection; a new series only when nothing fits.
- **Extras count as tonight's edition.** A series that publishes by hand
  today is skipped by tonight's scheduled run (same UTC date) — it already
  got its edition.

## Governing without YAML

Day to day you steer by talking to your agent (the librarian skill): *"pause
frontier-compute"*, *"make the wildcard desk weekly"*, *"commission a dossier
on ASML"*, *"less policy in the brief for a while"* (a prompt.md edit). Every
change is one small diff on `main`, validated by
`python3 engine/validate_config.py`.
