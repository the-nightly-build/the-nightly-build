---
name: librarian
description: >
  Setup and curation for The Nightly Build. Use when a human asks to be set up,
  to add/change/remove a series ("make me a course on X", "add a watchlist",
  "track Y nightly"), to adjust series settings, or to schedule the night shift.
  Not for producing articles; that is the correspondent skill.
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
upstream-owned. Users only ever edit `press/`, which is what makes engine updates
conflict-free (see §7).

**Fresh paper?** A fresh fork has no `press/` content of its own to reset.
Upstream ships no `press/` at all (the directory does not exist there, which keeps
engine updates conflict-free), and `setup.sh` scaffolds an empty one. So the
interview writes `press/site.yaml` (their title), `press/editorial.md` (their
voice, §1), and `press/series/` from scratch. The complete working configuration
in `examples/` is the living reference: every file there demonstrates part of the
config surface, including commented-out advanced options, so crib from it rather
than copy it wholesale.

## 1. Interview

Ask before writing, and make it a real conversation, not a form. The goal is to
understand what this person actually wants to read: their interests, their taste,
what they already follow and what they wish existed. Follow the thread where it
leads and let it run before you converge on a shape to propose. By the end you
need enough to design the masthead:

- What they want to learn or track, and what they would genuinely read every day.
- Shape: one-off deep dives (**collection**), an ordered course (**sequence**),
  ongoing briefings (**rolling**), or an editor-run section (**open**: they
  describe a beat, the night shift picks each night's topic and genre)?
  Nearly everything is the `article` template; the genre (dossier, chronicle,
  lesson, appraisal, essay...) is something the series prompt describes, not an
  engine setting. `brief` is for itemized nightly roundups. For structure the
  proof should enforce, a series can point at a custom `press/templates/`
  template (see §6).
- Rhythm: nightly everything, or should some series breathe? Per-series
  `cadence:` takes `daily`, `weekdays`, `weekends`, or a day list (`[mon, thu]`);
  a weekly deep dive plus a daily brief is a common pairing.

**The hands-off paper** (they say "just give me ~N good reads a day about X and
surprise me"): propose a masthead of open sections instead of enumerating items.
For example a daily rolling brief plus open sections with distinct beats (deep
dives, explainers, history, papers, a wildcard), each with a template choice list
and a cadence so the nightly mix varies. One article per section per night is the
invariant, so "six things a day" means six sections. They govern it later in
prose, not YAML: commissioning drops an item into a section's queue, steering
edits the section's `prompt.md`.

- **Voice** (written into `press/editorial.md`): how should the paper sound
  (register, wit, language), and what should it assume they already know? This is
  a paper-wide layer composed into every article.
- Depth and per-series emphases; those go in the series prompt, not the voice
  file.
- Must-read documents or must-check sites? These become `required_docs`
  (committed files, must be read and cited) and `consult` (URL prefixes read
  first; citing optional). If they want articles built ONLY from their sources,
  set `sources_exclusive: true`, and any outside citation then BLOCKs. Paywalled
  material is not cleanly supported yet (see below).

**Paywalled sources.** Treat full support as a future feature. A public repo
(which GitHub Pages needs) rules out committing paywalled full text, and
credentials never go in the repo. If it comes up, say so honestly rather than
improvising a workaround.

## 2. Propose, then write

Propose: series `id` (`[a-z0-9-]{1,32}`), mode, template (must be legal for the
mode per the template's `manifest.yaml`; open series may declare a `templates:`
choice list instead), name, cadence if not nightly, and, for collection/sequence,
the full item list (slugs `[a-z0-9-]{1,64}`, titles, tags, per-item prompts). For
a sequence, draft the complete ordered syllabus with the user before writing
anything. For an open section, the beat description in `prompt.md` IS the config,
so invest the interview time there. Show the plan; get a yes.

Then write:

- `press/series/<id>/series.yaml`: crib from `examples/series/` for the canonical
  shapes. Defaults: `autopublish: true`, `strict: false`.
- `press/series/<id>/prompt.md`: the series' editorial instructions. Subject
  frame, emphases, recurring angles, and the section's GENRE (the outline
  conventions it keeps and the furniture that carries it, see
  `templates/FURNITURE.md`). Crib the genre briefs from
  `examples/series/*/prompt.md`. It specializes the voice layers; it never
  contradicts PROTOCOL.md.
- Tag fragments under `press/series/_tags/` if shared angles apply.
- Sources for `required_docs` under `press/series/<id>/sources/`.

Validate: `python3 engine/validate_config.py`. Fix anything it flags before
proceeding. Commit the configuration to `main` (via the user's normal review
flow; configuration is code-review territory, not an agent PR to `library`).

## 3. Bootstrap

If the repo has no `library` branch yet, run `./setup.sh` (idempotent: creates
the orphan `library` branch, enables Pages and auto-merge, clears the library
branch to deploy, re-validates). Two human-only prerequisites for a live site,
flag both when they apply: the repo must be **public** (GitHub Pages needs it on
the free plan, or Pro), and for a cloud harness it must be **connected** so the
night shift can reach it (the Connect step for the chosen path in
`docs/scheduling.md`).

## 4. Offer a press check (default next step)

Before any scheduling, offer a rehearsal: _"want to see what the first article
would look like tonight?"_ Follow `skills/correspondent/SKILL.md` § Press check.
It costs the same usage as a real run (it runs the full pipeline and only skips
publishing), and it is the editorial loop for tuning the prompt: read the draft,
adjust `prompt.md`, re-run, compare.

## 5. Harness handoff

**One schedule per paper, ever.** The schedule prompt is paper-level: each night
the run derives its work list from the repo, so adding, retiring, or completing
series never requires touching the harness again. If the paper already has its
schedule, say so and skip this section; configuring the new series on `main` was
the whole job.

For a first-time handoff, read `docs/scheduling.md` (the model) and
`docs/harnesses.md` (which agents work and their costs). Ask what agent or
subscription the user already pays for, match it to a harness there (a native
scheduler when the provider hosts one, else the universal GitHub Actions cron),
and cover four things:

1. **Connect**: the one-time GitHub connection for the chosen path.
2. **Schedule**: one nightly schedule for the whole paper, using the canonical
   prompt in `docs/scheduling.md` with `<repo>` and `<checkout>` filled in.
3. **Model and cost**: pick the strongest model available; nb-meta records what
   actually ran. Say plainly whether the run is included in a subscription or
   bills a metered key (the coverage table in `docs/harnesses.md` has it per agent).
4. **First run now**: do not make them wait for tonight. If your harness lets you
   fire a one-off run yourself, do it and watch today's article publish; otherwise
   tell them exactly how.

If you (the running agent) can create the schedule and fire the first run
yourself, do it. Otherwise the human pastes the filled prompt into their
scheduler; say that plainly. The prompt lives in `docs/scheduling.md` and the
per-agent paths in `docs/harnesses.md`, so they are not repeated here.

## 6. Curation verbs

On request:

- **Add, remove, or reorder items.** Reordering a sequence only reorders the
  unpublished tail; published articles are permanent.
- **Pause or resume a series** (`paused: true`). The archive stays up and the
  proof refuses new articles.
- **Change its rhythm** (`cadence:`).
- **Commission** ("have the wildcard section cover X next"): append an item to an
  open section's `items:` queue, which the night shift clears before choosing its
  own topic again.
- **Steer an open section** ("less policy for a while"): edit its `prompt.md` beat.
- **Extra articles on demand** ("write me a piece on X right now"): give the topic
  a home first (a commission, a new item, or a new series, since the proof rejects
  articles for unconfigured series), then hand off to the correspondent's
  _Commissioned work_ flow.
- **Let a collection surprise them** (`selection: random`).
- **Adjust `words:` bands** (may tighten, never loosen below the template's floor)
  **and `min_sources`.**
- **Flip `autopublish`** (false means the desk approves and a human merges) **or
  `strict`** (true means WARNs become BLOCKs; warn that a skipped night is better
  than a thin article).

Re-validate after every change.

## Customization verbs

- _"Change the look"_: copy `engine/assets/themes/newspaper.css` to
  `press/themes/<name>.css`, edit ONLY the token variables, point
  `press/site.yaml` `theme:` at it. Never edit engine CSS.
- _"Change the voice"_: edit `press/editorial.md`. Series-specific tone goes in
  that series' prompt instead.
- _"Make a new genre"_: usually no new template. Write the genre into the series
  `prompt.md` (outline conventions, furniture) and rely on `article`'s flex
  sections. That is how the examples run chronicles, lessons, and appraisals.
- _"Make a new template"_: for structure the proof should ENFORCE, create a
  package folder `press/templates/<id>/` (the folder name is the id) with a
  `manifest.yaml` (`class`, `words` size band, `sections` anchors incl. `sources`,
  optional `flex_sections: [min, max]` for an agent-named middle, `cite_rule`,
  `modes`) and a `skeleton.html` scaffold (crib a shipped template's head and
  chrome; keep the asset links and sandbox rules). A press package replaces a
  shipped one of the same id wholesale. Omit `flex_sections` for a fully fixed
  outline. Two optional manifest fields declare requirements the engine reads
  (never from a template name): `cite_exempt: [names]` for sections that carry no
  citations (on top of the always-exempt `sources`) and `require_why: true` to
  require a `data-nb-why` line on each item. The build-your-own walkthrough in
  `docs/customization.md` rebuilds the classic lesson template this way. An
  optional `<id>/identity.md` gives the template its voice and character (crib
  `templates/article/identity.md`): specific about stance and craft, permissive
  about structure. A `<id>/furniture.md` + `furniture.css` adds bespoke furniture
  only this template renders. Validate, then press check before scheduling.
- _"Give my paper its own furniture"_: for pieces shared across sections, add
  component classes to `press/furniture/styles.css` and catalogue them in
  `press/furniture/catalog.md`; for a piece only one template renders, put it in
  that template's folder (`furniture.md` + `furniture.css`). Either restyles the
  whole library on every publish. Instruct the sections to use them in
  `prompt.md`; see `docs/customization.md`.

## 7. Update my engine (plain git)

```sh
git remote add upstream https://github.com/the-nightly-build/the-nightly-build.git  # once
git fetch upstream
git merge upstream/main
./setup.sh    # re-syncs the trigger workflows onto library
```

An ordinary fork merge. For users who only write inside `press/` it is clean by
construction: their commits and upstream's touch disjoint paths. If they HAVE
edited engine files, the merge may conflict exactly there; that is normal fork
ownership, so help them resolve it like any merge, never overwriting their work.
After updating, offer to dispatch the publish workflow so the back catalog
re-renders with the new engine immediately, and ask to see their schedule
prompt: it lives outside the repo, so no merge can fix it. Diff it against the
canonical prompt in `docs/scheduling.md` and replace anything that restates
what the repo owns; a trigger that recites the pipeline is stale the day after
it is written.

## Boundaries

Never push to `library`. Never edit files under `library/`. The escape hatch for
a bad published article is deleting its file on `library` (the night shift
rewrites it next run). That is a human decision: offer it, do not do it
unprompted.
