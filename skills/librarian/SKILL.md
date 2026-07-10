---
name: librarian
description: >
  Setup and curation for The Nightly Build. Use when a human asks to be set up,
  to add/change/remove a series ("make me a course on X", "add a watchlist",
  "track Y nightly"), to adjust series settings, or to schedule the night shift.
  Not for producing articles — that is the correspondent skill.
---

# The Librarian

You configure the paper; you never run it. Your output is configuration on
`main`, a rehearsal (press check), and the night-shift schedule. If your harness
lets you create the schedule and fire the first run yourself, do it; otherwise
emit the filled prompt for the human to paste. Say which case applies plainly.
`docs/scheduling.md` holds the scheduling model; `docs/harnesses.md` lists which
agents can run it and their costs.

## 0. The ownership model (say it once, early)

`press/` is the user's side of the repo; everything else is the engine,
upstream-owned. Users only ever edit `press/` — that's what makes engine
updates conflict-free (see §7).

**Fresh paper?** The shipped `press/` contents are the **upstream project's
own dogfood assignments**, not starter content. Reset them before the
interview — don't offer to keep them, and never let them reach a schedule:

```sh
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
  ongoing briefings (**rolling**), or an editor-run section (**open** — they
  describe a beat, the night shift picks each night's topic and genre)?
  Nearly everything is the `article` template; the genre (dossier, chronicle,
  lesson, appraisal, essay...) is something the series prompt describes, not an
  engine setting. `brief` is for itemized nightly roundups. For structure the
  proof should enforce, a series can point at a custom `press/templates/`
  template (see §6).
- Rhythm: nightly everything, or should some series breathe? Per-series
  `cadence:` takes `daily`, `weekdays`, `weekends`, or a day list
  (`[mon, thu]`) — a weekly deep dive plus a daily brief is a classic paper.

**The hands-off paper** (they say "just give me ~N good reads a day about X
and surprise me"): propose a masthead of open sections instead of enumerating
items — e.g. a daily rolling brief, plus open sections with distinct beats
(deep dives, explainers, history, papers, a wildcard), each with a template
choice list and a cadence so the nightly mix varies. One article per section per
night is the invariant, so "six things a day" = six sections. They govern later
with words, not YAML: commissioning drops an item into a section's queue,
steering edits the section's `prompt.md`.

- **Voice** (two questions, written into `press/editorial.md`): how should the
  paper sound — register, wit, language? And what should it assume they
  already know? This is a paper-wide layer composed into every article.
- Depth and per-series emphases; those go in the series prompt, not the voice
  file.
- Must-read documents or must-check sites? These become `required_docs`
  (committed files, must be read and cited) and `consult` (URL prefixes read
  first; citing optional). If they want articles built ONLY from their
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
with the user before writing anything. For an open section, the beat description
in `prompt.md` IS the config — invest the interview time there. Show the
plan; get a yes.

Then write:

- `press/series/<id>/series.yaml` — crib from `examples/series/` for
  the canonical shapes. Defaults: `autopublish: true`, `strict: false`.
- `press/series/<id>/prompt.md` — the series' editorial instructions: subject
  frame, emphases, recurring angles, and the section's GENRE: the outline
  conventions it keeps and the furniture that carries it (see
  `templates/FURNITURE.md`). Crib the genre briefs from
  `examples/series/*/prompt.md`. It specializes the voice layers; it never
  contradicts PROTOCOL.md.
- Tag fragments under `press/series/_tags/` if shared angles apply.
- Sources for `required_docs` under `press/series/<id>/sources/`.

Validate: `python3 engine/validate_config.py`. Fix anything it flags before
proceeding. Commit the configuration to `main` (via the user's normal review
flow — configuration is code review territory, not an agent PR to `library`).

## 3. Bootstrap

If the repo has no `library` branch yet, run `./setup.sh` (idempotent: creates
the orphan `library` branch, enables Pages and auto-merge, clears the library
branch to deploy, re-validates). Two human-only prerequisites for a live site,
flag both when they apply: the repo must be **public** (GitHub Pages needs it
on the free plan, or Pro), and for a cloud harness it must be **connected** so
the night shift can reach it (the Connect step for the chosen path in
`docs/scheduling.md`).

## 4. Offer a press check (default next step)

Before any scheduling, offer a rehearsal: _"want to see what the first article
would look like tonight?"_ Follow `skills/correspondent/SKILL.md` § Press
check. It consumes the same usage as a real run — it IS one, minus
publication — and it is the editorial loop for tuning the prompt: read the
draft, adjust `prompt.md`, re-run, compare.

## 5. Harness handoff

**One schedule per paper, ever.** The schedule prompt is paper-level: each
night the run derives its work list from the repo, so adding, retiring, or
completing series never requires touching the harness again. If the paper
already has its schedule, say so and skip this section — configuring the new
series on `main` was the whole job.

For a first-time handoff, read `docs/scheduling.md` (the model) and
`docs/harnesses.md` (which agents work and their costs). Ask what agent or
subscription the user already pays for, match it to a harness there (a native
scheduler when the provider hosts one, else the universal GitHub Actions cron),
and cover four things:

1. **Connect** — the one-time GitHub connection for the chosen path.
2. **Schedule** — one nightly schedule for the whole paper, using the canonical
   prompt in `docs/scheduling.md` with `<repo>` and `<checkout>` filled in.
3. **Model and cost** — pick the strongest model available; nb-meta records what
   actually ran. Say plainly whether the run is included in a subscription or
   bills a metered key (the coverage table in `docs/harnesses.md` has it per agent).
4. **First run now** — do not make them wait for tonight. If your harness lets
   you fire a one-off run yourself, do it and watch today's article publish;
   otherwise tell them exactly how. Setting up in the morning should mean a paper
   by lunch, then a fresh one every night.

If you (the running agent) can create the schedule and fire the first run
yourself, do it. Otherwise the human pastes the filled prompt into their
scheduler; say that plainly. The prompt lives in `docs/scheduling.md` and the
per-agent paths in `docs/harnesses.md`, so they are not repeated here.

## 6. Curation verbs

On request: add/remove/reorder items (reordering a sequence only reorders the
_unpublished_ tail — published articles are permanent); **pause/resume** a
series (`paused: true` — the archive stays up, the proof refuses new
articles); **change its rhythm** (`cadence:`); **commission** ("have the
wildcard section cover X next") — append an item to an open section's `items:`
queue, which the night shift must clear before freestyling again; **steer an
open section** ("less policy for a while") — edit its `prompt.md` beat;
**extra articles on demand** ("write me a piece on X right now") — make sure
the topic has a home first (a commission, a new item, or a new series —
the proof rejects articles for unconfigured series), then hand off to the
correspondent's _Commissioned work_ flow; let a
collection surprise them (`selection: random`); adjust `words:` bands (may
tighten, never loosen below the registry floor) and `min_sources`; flip
`autopublish` (false ⇒ the editor approves, a human merges) and `strict`
(true ⇒ WARNs become BLOCKs — warn that a missed night then beats a thin
article). Re-validate after every change.

**Customization verbs:**

- _"Change the look"_ — copy `engine/assets/themes/newspaper.css` to
  `press/themes/<name>.css`, edit ONLY the token variables, point
  `press/site.yaml` `theme:` at it. Never edit engine CSS.
- _"Change the voice"_ — edit `press/editorial.md`. Series-specific tone goes
  in that series' prompt instead.
- _"Make a new genre"_ — usually no new template: write the genre into the
  series `prompt.md` (outline conventions, furniture) and rely on `article`'s
  flex sections. That is how the examples run chronicles, lessons, and
  appraisals.
- _"Make a new template"_ — for structure the proof should ENFORCE: add an
  entry to `press/templates/registry.yaml` (class, band, `sections` anchors
  incl. `sources`, optional `flex_sections: [min, max]` for an agent-named
  middle, cite_rule, modes) and a `press/templates/<id>.html` scaffold (crib
  a shipped template's head and chrome; keep the asset links and sandbox
  rules). Omit `flex_sections` for a fully fixed outline. Two optional fields
  declare requirements the engine reads from the entry (never from a template
  name): `cite_exempt: [names]` for sections that carry no citations (on top
  of the always-exempt `sources`) and `require_why: true` to require a
  `data-nb-why` line on each item. The build-your-own walkthrough in
  `docs/customization.md` rebuilds the classic lesson template this way.
  Validate, then press check before scheduling.
- _"Give my paper its own furniture"_ — add component classes to the paper's
  theme CSS (it restyles the whole library on every publish) and instruct
  the sections to use them in `prompt.md`; see `docs/customization.md`.

## 7. Update my engine (plain git)

```sh
git remote add upstream https://github.com/the-nightly-build/the-nightly-build.git  # once
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
for a bad published article is deleting its file on `library` (the night shift
rewrites it next run) — that is a human decision, offer it, don't do it
unprompted.
