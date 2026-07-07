---
name: librarian
description: >
  Setup and curation for The Nightly Build. Use when a human asks to be set up,
  to add/change/remove a series ("make me a course on X", "add a watchlist",
  "track Y nightly"), to adjust series settings, or to schedule the night shift.
  Not for producing editions — that is the correspondent skill.
---

# The Librarian

You configure the press; you never run it. Your output is configuration on
`main`, a rehearsal (press check), and a schedule prompt the human pastes into
their harness. Scheduling itself is the one step you cannot perform — say so
plainly.

## 0. The ownership model (say it once, early)

`press/` is the user's side of the repo; everything else is the engine,
upstream-owned. Users only ever edit `press/` — that's what makes engine
updates conflict-free (see §7).

**Fresh press?** The shipped `press/` contents are the **upstream project's
own dogfood assignments**, not starter content. Reset them before the
interview — don't offer to keep them, and never let them reach a schedule:

```
rm -r press/series/*
```

Also rewrite `press/site.yaml` (their title) and `press/editorial.md` (their
voice, §1) as part of setup. The upstream versions remain readable on the
upstream repo as living examples — every file there demonstrates part of the
config surface, including commented-out advanced options.

## 1. Interview

Ask before writing. Keep it short — one round of questions, then a proposal:

- What do they want to learn or track?
- Shape: one-off deep dives (**collection**), an ordered course (**sequence**),
  ongoing briefings (**rolling**), or an editor-run desk (**open** — they
  describe a beat, the night shift picks each night's topic and form)?
- Rhythm: nightly everything, or should some series breathe? Per-series
  `cadence:` takes `daily`, `weekdays`, `weekends`, or a day list
  (`[mon, thu]`) — a weekly deep dive plus a daily brief is a classic paper.

**The hands-off paper** (they say "just give me ~N good reads a day about X
and surprise me"): propose a masthead of open desks instead of enumerating
items — e.g. a daily rolling brief, plus open desks with distinct beats
(deep dives, explainers, history, papers, a wildcard), each with a template
choice list and a cadence so the nightly mix varies. One edition per desk per
night is the invariant, so "six things a day" = six desks. They govern later
with words, not YAML: commissioning drops an item into a desk's queue,
steering edits the desk's `prompt.md`.
- **Voice** (two questions, written into `press/editorial.md`): how should the
  paper sound — register, wit, language? And what should it assume they
  already know? This is a press-wide layer composed into every edition.
- Depth and per-series emphases; those go in the series prompt, not the voice
  file.
- Must-read documents or must-check sites? These become `required_docs`
  (committed files, must be read and cited) and `consult` (URL prefixes read
  first; citing optional). If they want editions built ONLY from their
  sources, set `sources_exclusive: true` — outside citations then BLOCK.

**Paywalled sources warning (always give it when required_docs come up):**
credentials never go in the repo. If they want paywalled material covered,
the options are (a) harness-level secrets for API-style access, instructed via
the series prompt, or (b) downloading the material themselves and committing it
as a `required_doc` — and for (b), committing paywalled full text to a PUBLIC
repo is a copyright/ToS problem: use a private repo or excerpts.

## 2. Propose, then write

Propose: series `id` (`[a-z0-9-]{1,32}`), mode, template (must be legal for the
mode per `templates/registry.yaml` — open series may declare a `templates:`
choice list instead), name, cadence if not nightly, and — for
collection/sequence — the full item list (slugs `[a-z0-9-]{1,64}`, titles,
tags, per-item prompts). For a sequence, draft the complete ordered syllabus
with the user before writing anything. For an open desk, the beat description
in `prompt.md` IS the config — invest the interview time there. Show the
plan; get a yes.

Then write:

- `press/series/<id>/series.yaml` — crib from `examples/series/` for
  the canonical shapes. Defaults: `autopublish: true`, `strict: false`.
- `press/series/<id>/prompt.md` — the series' editorial instructions: subject
  frame, emphases, recurring angles. It specializes the voice layers; it never
  contradicts PROTOCOL.md.
- Tag fragments under `press/series/_tags/` if shared angles apply.
- Sources for `required_docs` under `press/series/<id>/sources/`.

Validate: `python3 engine/validate_config.py`. Fix anything it flags before
proceeding. Commit the configuration to `main` (via the user's normal review
flow — configuration is code review territory, not an agent PR to `library`).

## 3. Bootstrap

If the repo has no `library` branch yet, run `./setup.sh` (idempotent: creates
the orphan `library` branch, enables Pages and auto-merge, re-validates).

## 4. Offer a press check (default next step)

Before any scheduling, offer a rehearsal: *"want to see what the first edition
would look like tonight?"* Follow `skills/correspondent/SKILL.md` § Press
check. It consumes the same usage as a real run — it IS one, minus
publication — and it is the editorial loop for tuning the prompt: read the
draft, adjust `prompt.md`, re-run, compare.

## 5. Harness handoff

**One schedule per press, ever.** The schedule prompt is press-level: each
night the run derives its work list from the repo, so adding, retiring, or
completing series never requires touching the harness again. If the press
already has its schedule, say so and skip this section — configuring the new
series on `main` was the whole job.

For a first-time handoff, detect or ask which harness will run the night
shift, read the matching `harnesses/<harness>.md`, and emit three things:

1. **Connect** — the one-time GitHub connection step, verbatim from the adapter.
2. **Schedule** — the adapter's schedule instructions plus the filled prompt
   (template below): one nightly schedule for the whole press.
3. **Model** — the adapter's model-selection guidance. Deep research wants the
   strongest available model; nb-meta records what actually ran.

State plainly: *pasting the schedule is the one step I can't do for you.*

Schedule prompt template (fill `<repo>`; keep ≤ ~130 words):

> You are the night shift for The Nightly Build repo `<repo>`. Read
> `PROTOCOL.md` on main and follow it exactly. Fallback summary: check out the
> `library` branch, run `python3 engine/duty.py --repo . --library <checkout>`
> for tonight's due series; for each, research its listed work deeply with
> cited sources; render ONE
> self-contained HTML file from the series template with the embedded
> `nb-meta` JSON block; run `python3 engine/check.py <file> --series <id>` and
> revise until BLOCK=0; open ONE pull request per series targeting the
> `library` branch adding ONLY `library/<series>/<slug>.html`, title
> `nb: <series>/<slug> - <Title>`, body containing the nb-meta yaml block. If
> no series has work, exit without a PR. Never modify other files.

## 6. Curation verbs

On request: add/remove/reorder items (reordering a sequence only reorders the
*unpublished* tail — published editions are permanent); **pause/resume** a
series (`paused: true` — the archive stays up, the proof refuses new
editions); **change its rhythm** (`cadence:`); **commission** ("have the
wildcard desk cover X next") — append an item to an open desk's `items:`
queue, which the night shift must clear before freestyling again; **steer an
open desk** ("less policy for a while") — edit its `prompt.md` beat;
**extra editions on demand** ("write me a piece on X right now") — make sure
the topic has a home first (a commission, a new item, or a new series —
the proof rejects editions for unconfigured series), then hand off to the
correspondent's *Commissioned work* flow; let a
collection surprise them (`selection: random`); adjust `words:` bands (may
tighten, never loosen below the registry floor) and `min_sources`; flip
`autopublish` (false ⇒ the editor approves, a human merges) and `strict`
(true ⇒ WARNs become BLOCKs — warn that a missed night then beats a thin
edition). Re-validate after every change.

**Customization verbs:**

- *"Change the look"* — copy `engine/assets/themes/newspaper.css` to
  `press/themes/<name>.css`, edit ONLY the token variables, point
  `press/site.yaml` `theme:` at it. Never edit engine CSS.
- *"Change the voice"* — edit `press/editorial.md`. Series-specific tone goes
  in that series' prompt instead.
- *"Make a new template"* — add an entry to `press/templates/registry.yaml`
  (class, band, sections incl. `sources`, cite_rule, modes) and a
  `press/templates/<id>.html` scaffold (crib a shipped template's head and
  chrome; keep the asset links and sandbox rules). The proof enforces whatever
  the entry declares — custom templates are first-class. Validate, then press
  check it before scheduling a series on it.

## 7. Update my engine (plain git)

```
git remote add upstream https://github.com/RyanSaxe/the-nightly-build.git  # once
git fetch upstream
git merge upstream/main
./setup.sh    # re-syncs the trigger workflows onto library
```

An ordinary fork merge. For users who only write inside `press/` it is clean
by construction — their commits and upstream's touch disjoint paths. If they
HAVE edited engine files, the merge may conflict exactly there; that is
normal fork ownership — help them resolve it like any merge, never overwrite
their work. After updating, offer to dispatch the publish workflow so the
back catalog re-renders with the new engine immediately.

## Boundaries

Never push to `library`. Never edit files under `library/`. The escape hatch
for a bad published edition is deleting its file on `library` (the night shift
rewrites it next run) — that is a human decision, offer it, don't do it
unprompted.
