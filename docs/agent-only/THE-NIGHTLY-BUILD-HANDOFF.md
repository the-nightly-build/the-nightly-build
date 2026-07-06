# The Nightly Build — Final Implementation Handoff

**Tagline:** *Built while you sleep.*

This is the complete, self-contained specification for **The Nightly Build**: an open-source,
forkable, harness-agnostic system in which cloud AI agents research topics on a schedule and
publish deep, cited, beautifully rendered editions to a personal GitHub Pages library. No other
document is required. Where you must make a judgment call not covered here, prefer: simplicity,
statelessness, security, and reader experience — in that order.

---

## 0. Product vision

A person forks one repo, tells their AI agent "set me up," answers a few questions, pastes one
schedule command into their harness — and every morning they open their phone to **tonight's
build**: one or more researched, cited editions on the things they want to learn. Over weeks this
accumulates into a personal library: courses that progress in order, ongoing briefings,
collections of deep dives — permanent, searchable, owned by them, served free from GitHub Pages.

Differentiations (validated against prior art — GPT-Researcher, STORM, GPT Newspaper, RSS-digest
pipelines, LLM-wiki systems — none combine these):
- **Research, not summarization.** Editions are original cited research artifacts.
- **Git as the protocol.** Any agent that can open a pull request can participate.
- **A safety gate, not a quality gate.** CI guarantees the site can never break; quality pressure
  happens *inside the agent's loop* via a repo-shipped tool (§6). A missed night is worse than a
  thin edition.
- **Permanence and forkability.** `main` contains zero content; a fork is a blank press.
- **~95% of reads happen on a phone.** Mobile is the primary design surface everywhere.

### Vocabulary (use consistently in code, docs, UI)
| Term | Meaning |
|---|---|
| **The Nightly Build** | The system; also each night's set of published editions |
| **edition** | One published HTML artifact |
| **series** | A configured collection of editions (course, watchlist, news topic) |
| **build** (noun) | All editions published on a given night |
| **library** | The content branch and the published site |
| **template** | A functional layout an edition is rendered from (dossier, lesson, brief, deck, paper, chronicle) |
| **the night shift** | The agents |
| **the editor** | The CI check (BLOCK tier) |
| **the proof** | `engine/check.py` — the agent's in-loop self-review tool |
| **newsstand** | The site front page |
| **press check** | A local rehearsal run: full contract, no PR (§9.5) |
| **Librarian / Correspondent** | The setup skill / the runtime skill |

---

## 1. Repository architecture

One repository, two long-lived branches.

### `main` — the engine (forkable, never contains content)
```
/
├── README.md                  # pitch + 5-minute quickstart + screenshots
├── PROTOCOL.md                # THE agent contract (§3)
├── AGENTS.md                  # auto-read by Claude Code / Codex / Jules (§9.0)
├── LICENSE                    # MIT
├── setup.sh                   # idempotent bootstrap (§10)
├── site.yaml                  # site title, theme file, default appearance (auto|light|dark)
├── spec/
│   ├── editorial.md           # global voice & quality bar (§4.3)
│   └── meta.schema.json       # JSON Schema for nb-meta (§5)
├── series/
│   ├── _tags/                 # shared tag prompt fragments
│   └── semiconductors/        # shipped example series (§12)
│       ├── series.yaml
│       ├── prompt.md
│       └── sources/           # optional committed required_docs
├── templates/
│   ├── registry.yaml          # template registry: the short-vs-long contract (§8.1)
│   ├── dossier.html
│   ├── lesson.html
│   ├── brief.html
│   ├── paper.html             # phase 4b
│   ├── chronicle.html         # phase 4b
│   └── deck.html              # phase 4b
├── engine/
│   ├── check.py               # THE PROOF: two-tier checker, used by agents AND CI (§6)
│   ├── build_site.py          # static site builder (§7)
│   ├── assets/
│   │   ├── nb.js              # contextual nav + declarative chart renderer (§7.4, §8.4)
│   │   ├── nb.css             # site chrome styles
│   │   └── themes/newspaper.css  # default token theme (§8.3, verbatim below)
│   └── tests/                 # fixtures for every BLOCK and WARN code
├── skills/
│   ├── librarian/SKILL.md     # setup & curation (§9.1)
│   └── correspondent/SKILL.md # runtime contract + craft (§9.2)
├── harnesses/
│   ├── claude.md              # Connect / Schedule / Model / Verify (§9.3)
│   ├── jules.md
│   └── codex.md
├── .gitignore                 # includes press-check/
└── .github/workflows/
    ├── check.yml              # PR editor: runs check.py --pr (§6.4)
    └── publish.yml            # post-merge site build + Pages deploy (§7)
```

### `library` — the content (created empty by setup.sh)
```
/
├── library/<series-id>/<slug>.html    # editions — the ONLY files agents ever add
└── site/                              # builder output, regenerated every publish
    ├── index.html                     # the newsstand = tonight's build
    ├── builds/<YYYY-MM-DD>/index.html
    ├── series/<id>/index.html
    ├── tags/<tag>/index.html
    ├── catalog.json                   # machine-readable library state (§7.1)
    ├── feed.xml, series/<id>/feed.xml # Atom feeds
    └── assets/                        # copied from main's engine/assets at build time
```

Invariants (enforce always):
1. **No executable logic ever lives on `library`.** publish.yml checks out `engine/` and
   `templates/` from `main` and runs them against `library` content. Security spine.
2. **Agents add exactly one file per PR**, always under `library/<series>/`.
3. **No state exists except published files.** "What's next" is derived by listing
   `library/<series>/`. Runs are idempotent and crash-safe; multiple harnesses can share a repo
   (first valid PR wins, §6.5).
4. Pages serves the `library` branch `/site` folder (or Actions-based Pages deploy — implementer's
   choice; URL structure in §7 must hold).

---

## 2. Modes

| Mode | Use case | Next-work rule | Slug | Site ordering |
|---|---|---|---|---|
| `collection` | watchlists, topic sets | first `items:` entry with no published file | from config, `[a-z0-9-]{1,64}` | config order, card grid |
| `sequence` | courses | lowest-index missing item; **agent MUST read the series' already-published editions first** | same | numbered, progress, "continue here" |
| `rolling` | news/briefings | today's UTC date if unpublished; **missed nights are skipped, never backfilled** | `YYYY-MM-DD` | reverse-chron + calendar archive |

---

## 3. PROTOCOL.md — the agent contract

The single document a scheduled agent needs; write it fully self-contained. Contents, in order:

1. **Version header:** `Protocol-Version: 1.0` (semver; editions embed it; the editor accepts the
   current major).
2. **The contract, numbered:**
   1. You are one run of the night shift. Publish at most ONE edition.
   2. Read, in order: this file → `spec/editorial.md` → `templates/registry.yaml` entry for your
      template → `series/<id>/prompt.md` → tag fragments (declared order) → item `prompt` if
      present. Later layers specialize; they never override this file.
   3. Determine your series (named in your schedule prompt). Fetch the `library` branch, list
      `library/<series>/`, apply the mode rule (§2 table reproduced here). **No work → stop; no PR.**
   4. Sequence mode: read the series' published editions before writing.
   5. Read every `required_docs` file and consult every `required_urls` prefix declared for your
      item/series (§4.2). Research thoroughly with web access; verify against primary sources;
      never fabricate citations. Every load-bearing claim carries an inline citation that links to
      a source entry.
   6. Render exactly one self-contained HTML file from the template: fill every
      `data-nb-section`; embed the `nb-meta` JSON block (§5); charts only as declarative
      `data-nb-chart` JSON blocks (§8.4); no scripts other than those JSON blocks, no iframes, no
      inline event handlers, no external resources beyond the template's own.
   7. **Run the proof:** `python3 engine/check.py <your-file> --series <id>`. Iterate until
      `BLOCK: 0`. Treat every WARN as a revision note and address what you reasonably can — WARNs
      are the quality bar; BLOCKs are the publishing bar.
   8. Open a PR **targeting `library`** adding exactly `library/<series>/<slug>.html`. Title:
      `nb: <series>/<slug> — <Title>`. Body: the `nb-meta` yaml block + run URL if available +
      the proof's final WARN summary (transparency).
   9. Never merge, never push to `library` directly, never touch other files, never open a second
      PR. If labeled `nb-invalid`, a future run supersedes you; don't fight the editor.
3. **The nb-meta schema** inline with a filled example (§5).
4. **A quality creed** (three sentences): editions teach rather than summarize; every load-bearing
   claim carries a citation the reader can follow; the goal is to equip the reader to go deeper.

### 3.1 The self-sufficient schedule prompt (belt-and-suspenders — REQUIRED)
The copy-paste prompt users put into their harness must itself contain a minimal contract so an
agent that never loads AGENTS.md or the Correspondent skill still behaves. Template (Librarian
fills repo + series; keep ≤ ~130 words):

> You are the night shift for The Nightly Build repo `<repo>`. Work series: `<series-id>`. Read
> `PROTOCOL.md` on main and follow it exactly. Fallback summary: list `library/<series-id>/` on
> the `library` branch; pick the next unpublished item per `series/<series-id>/series.yaml`;
> research it deeply with cited sources; render ONE self-contained HTML file from the series
> template with the embedded `nb-meta` JSON block; run `python3 engine/check.py <file> --series
> <series-id>` and revise until BLOCK=0; open ONE pull request targeting the `library` branch
> adding ONLY `library/<series-id>/<slug>.html`, title `nb: <series-id>/<slug> — <Title>`, body
> containing the nb-meta yaml block. If nothing is unpublished, exit without a PR. Never modify
> other files.

---

## 4. Configuration

### 4.1 `site.yaml`
```yaml
title: "The Nightly Build"        # masthead text; forks personalize
theme: engine/assets/themes/newspaper.css   # token file (§8.3)
appearance: auto                  # auto | light | dark. auto = follow system; base/no-JS fallback is LIGHT (§8.3)
```

### 4.2 `series/<id>/series.yaml`
```yaml
name: Semiconductors
mode: collection                  # collection | sequence | rolling
template: dossier                 # key into templates/registry.yaml
prompt: prompt.md
autopublish: true                 # false => editor approves, human merges
strict: false                     # true => WARNs are promoted to BLOCKs (opt-in only)
min_sources: 8                    # WARN floor override (registry provides default)
words: [3000, 5500]               # optional band override; may tighten, never loosen below registry
tags:
  equity: ../_tags/equity.md
required_urls:                    # WARN-tier: each prefix must match ≥1 source href
  - https://www.sec.gov/
items:
  - slug: micron
    title: Micron Technology
    tags: [equity]
    prompt: "Emphasize the HBM supply-agreement structure and the cycle debate."
    required_docs:                # WARN-tier: committed source material the agent must read
      - id: mu-10k-2025
        path: sources/mu-10k-2025.txt
rolling:                          # rolling mode only
  cadence: daily
```
Ship a schema; `setup.sh` and the Librarian validate against it. `id` = directory name,
`[a-z0-9-]{1,32}`.

**Required sources — semantics and the paywalled-source stance:**
- `required_docs`: files committed under `series/<id>/sources/`. Contract: agent reads each; the
  edition includes a source entry carrying `data-nb-required="<id>"`. Checked as `W-REQ-DOC`.
- `required_urls`: URL prefixes the agent must consult; satisfied by ≥1 source href matching each
  prefix. Checked as `W-REQ-URL`.
- **Paywalled/subscription sources are explicitly out of protocol scope.** Never put credentials
  in the repo. Two documented escape hatches, engineered by nobody: (a) harness-level secrets
  (Claude Routine environments / Codex cloud env vars) injected for API-style access, instructed
  via the series prompt; (b) the user downloads the material and commits it as a `required_doc`.
  The Librarian must warn on (b): committing paywalled full text to a PUBLIC repo is a
  copyright/ToS problem — use a private repo or excerpts.

### 4.3 `spec/editorial.md`
Global voice, composed into every prompt: teach-don't-summarize; structure follows the template's
sections; citation standards (primary sources preferred; every load-bearing claim cited inline;
citations link out; steelman opposing views on contested questions); "go deeper" endings that
equip independent research; concrete numbers over vague claims; define terms on first use;
write for an intelligent non-specialist reading on a phone.

### 4.4 Prompt composition order (deterministic)
`PROTOCOL.md` → `spec/editorial.md` → registry entry → series `prompt.md` → tag fragments → item
`prompt`. Later layers specialize, never override.

---

## 5. Metadata

### 5.1 In-file `nb-meta` block (single source of truth for the builder)
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
</script>
```
Ship `spec/meta.schema.json`. `harness`/`model` are self-reported provenance — displayed in the
byline; a multi-harness library doubles as a model-quality comparison corpus.

### 5.2 PR body block (ephemeral coordination)
Fenced ```nb-meta``` yaml mirroring §5.1 core fields + optional `run_url` + the proof's WARN
summary. The editor cross-checks PR body ↔ file path ↔ embedded JSON; disagreement is a BLOCK.

---

## 6. The proof — `engine/check.py` (two tiers, one tool)

**Design principle:** quality pressure happens inside the agent's loop, where iteration against
the model is cheap; CI blocks only what could break the site or the protocol. A conforming
agent's CI failure rate should be ~zero because CI runs the identical tool the agent already ran.

One dependency-light script (Python stdlib + PyYAML + jsonschema + an HTML parser). Invocations:
- `check.py <file> --series <id>` — agent loop / press check. Exit 0 iff BLOCK=0.
- `check.py --pr` — CI mode: additionally performs diff-shape checks against the PR.
Output: human summary + machine JSON (`--json`), listing each finding with code, message, and a
concrete suggestion (e.g. `W-LENGTH-LOW  dossier band 2500–6000; found 2210 — consider deepening
§analysis`).

### 6.1 BLOCK tier (site/protocol integrity — the editor's veto)
| Code | Check |
|---|---|
| `B-DIFF-SHAPE` | (CI) exactly one added file at `library/<series>/<slug>.html`; nothing else touched |
| `B-SERIES` | series config exists on main and parses |
| `B-SLUG` | slug legal for mode; rolling: valid date ≤ today, not already published |
| `B-META-PARSE` | nb-meta present, parses, validates against schema; protocol major matches |
| `B-META-MATCH` | (CI) embedded JSON ↔ PR body ↔ path agree |
| `B-MODE` | sequence: order == next expected; rolling date rule |
| `B-HTML` | parses; every `data-nb-section` required by the registry entry present exactly once; ≤ 2 MB |
| `B-SANDBOX` | no `<script>` except `application/json` blocks (`nb-meta`, `data-nb-chart`); chart JSON parses; no iframes/objects/embeds; no `on*=` attributes; no `javascript:` URLs; external refs only: engine assets path + Google Fonts |
| `B-SOURCES-FORM` | ≥ 1 source entry (`data-nb-source`), all hrefs well-formed absolute https |
| `B-CITES-RESOLVE` | every inline cite anchor resolves to an existing source entry — a dangling citation is a broken link, i.e. a broken site |

### 6.2 WARN tier (quality bar — revision notes, never blocks)
| Code | Check |
|---|---|
| `W-LENGTH-LOW / W-LENGTH-HIGH` | outside the registry/series word band (or item/slide count band) |
| `W-SOURCES-MIN` | fewer than the series/registry source floor |
| `W-CITE-DENSITY` | registry `cite_rule` unmet (per-section / per-item / per-slide) |
| `W-WHY-MISSING` | brief template: an item lacks its "why it matters" line |
| `W-REQ-DOC` | a declared `required_docs` id has no `data-nb-required` source entry |
| `W-REQ-URL` | a declared `required_urls` prefix matches no source href |
| `W-SELF-COUNT` | self-reported `sources`/`words` deviate >20% from measured |

`strict: true` on a series promotes all WARNs to BLOCKs (opt-in for users who prefer a missed
night over a thin edition; default off).

### 6.3 Agent loop
The Correspondent (and PROTOCOL step 7) runs the proof, revises, repeats until BLOCK=0, and
addresses WARNs as far as reasonable — then ships, quoting the final WARN summary in the PR body.

### 6.4 CI (`check.yml`)
Trigger `pull_request` (NEVER `pull_request_target`) with base `library`; permissions
`contents: read`, `pull-requests: write` (labels/comments). No secrets. Runs `check.py --pr`.
- BLOCK=0 + `autopublish: true` → auto-squash-merge (separate minimal job gated on the check;
  commit message `nb: <series>/<slug> — <title>`); WARNs posted as a PR comment + `nb-warnings`
  label so published editions carry an honest quality record.
- BLOCK=0 + `autopublish: false` → label `nb-approved`, comment "ready — merge when you like."
- BLOCK>0 → label `nb-invalid`, comment with codes; PR stays open for human inspection.

### 6.5 Concurrency & supersession
First valid PR per slug wins; on merge, close other open PRs adding the same path with a
`superseded by #N` comment. Sequence races self-resolve: the loser now fails `B-MODE`.

### 6.6 Tests
`engine/tests/` fixtures for every BLOCK and WARN code + happy paths per mode and per template.

---

## 7. The builder & the site (`engine/build_site.py` + `publish.yml`)

Trigger: push to `library`. Checkout `library`; checkout `main` into a subdir; run the builder
(from main) over `library/`; write `site/`; commit with `[skip ci]` guard; Pages deploys.

### 7.1 `site/catalog.json` — the load-bearing artifact
```json
{
  "generated": "2026-07-06T09:00:00Z",
  "protocol": "1.0",
  "site_title": "The Nightly Build",
  "series": [ { "id": "...", "name": "...", "mode": "...", "template": "...", "count": 4, "total": 12 } ],
  "editions": [ { ...nb-meta fields..., "path": "/library/semiconductors/micron.html" } ],
  "builds": { "2026-07-06": ["semiconductors/micron", "ai-semis/2026-07-06"] },
  "tags": { "equity": ["semiconductors/micron"] }
}
```
Search, tag filters, series progress, prev/next nav, and future tooling (hosted readers) all read
this file. Keep it stable and documented.

### 7.2 The newsstand (`site/index.html`) — the default page
Masthead: site title (serif, accent period), tonight's date, appearance toggle (**◐ auto → ○
light → ● dark**, persisted in localStorage), and a swipeable nav row: Tonight · Archive · Series
· Tags · Search.

**Tonight's build:** a "Tonight's build · N editions · built HH:MM UTC" rule-label, then cards.
- **Desktop (>640px):** front-page grid — the **lead card** (longest `reading_minutes` of the
  night) spans a double slot; others tile around it.
- **Mobile (≤640px, the primary surface):** a **vertical feed** — lead first at full width, then
  the rest stacked. No grid gymnastics on a phone.
Card contents: template badge (pill), series context line ("Foundations of Cryptography · Ed. 3
of 10"), serif title, italic dek, meta row (● new, reading time, source count, model).
States: (a) tonight's build; (b) "last night's build" header when nothing yet today; (c) fresh-
fork empty state ("The presses are ready — set up your first series").
Below the fold: per-series strips (continue-here / latest / progress) and a date navigator.

### 7.3 Other pages
`builds/<date>/` (every night, permanent, prev/next + calendar archive); `series/<id>/`
(sequence: numbered + progress bar + "continue here"; rolling: reverse-chron with month grouping;
collection: grid in config order); `tags/<tag>/`; client-side search over catalog.json from the
masthead; Atom feeds global + per-series (the push channel — subscribing recreates morning
delivery).

### 7.4 `engine/assets/nb.js` — engine-owned runtime
Loaded by every edition and site page. Duties: (1) contextual nav injected into editions
(back-to-tonight, series progress, prev/next edition, tag links) from catalog.json; (2) the
**declarative chart renderer** (§8.4) — finds `data-nb-chart` JSON blocks and renders them with
Chart.js loaded from cdnjs (the ONLY third-party script, loaded by nb.js itself, version-pinned);
(3) the appearance toggle behavior. Must degrade gracefully: no JS → clean readable document,
charts show their caption + a "chart requires JS" note, no broken UI.

### 7.5 Responsive rules (mobile is primary — bake these into site AND templates)
Base font ~15.5–16px; single reading column max-width 720px; tap targets ≥ 40px (nav links,
pills, series rows, toggle); horizontally scrollable pill rows instead of wrapping; grids
collapse to one column ≤640px; deck slides 88% width / 4:3 on mobile with scroll-snap; charts
max-height ~180px on mobile; brief item tags stack above headlines on mobile; test everything at
390px width in both appearances.

---

## 8. Templates & design system

### 8.1 `templates/registry.yaml` — the short-vs-long contract (verbatim)
Single source of truth agents read and the proof enforces. Bands are quality calibration (WARN),
not law; series may tighten (`words:` override) but never loosen below registry floors.
```yaml
dossier:
  class: longread
  words: [2500, 6000]
  sections: [orientation, foundations, analysis, debate, go-deeper, sources]
  cite_rule: per-section          # every content section ≥1 inline citation
  modes: [collection, sequence]
  furniture: [jump-nav, stat-strip, charts]
lesson:
  class: longread
  words: [1500, 4000]
  sections: [objectives, recap, teach, check, bridge, sources]
  cite_rule: per-section
  modes: [sequence]
  furniture: [objectives-box, callouts, self-check, next-bridge]
brief:
  class: shortread
  items: [4, 8]                   # item-count band instead of words
  sections: [items, sources]
  cite_rule: per-item             # every item cites; "why it matters" line expected (W-WHY-MISSING)
  modes: [rolling]
  furniture: [tagged-items, why-it-matters]
paper:                            # phase 4b
  class: shortread
  words: [1200, 2500]
  sections: [abstract, findings, appraisal, verdict, sources]
  cite_rule: per-section
  modes: [collection, rolling]
  furniture: [plain-abstract, holds-up-grid, verdict-box]
chronicle:                        # phase 4b
  class: longread
  words: [2000, 4500]
  sections: [orientation, timeline, echoes, sources]
  cite_rule: per-section          # timeline events count as the timeline section's citations
  modes: [sequence, collection]
  furniture: [timeline-spine, echoes-today]
deck:                             # phase 4b
  class: shortread
  slides: [8, 15]
  sections: [slides, sources]
  cite_rule: per-slide            # exempt slide kinds: title, divider
  modes: [collection, sequence]
  furniture: [scroll-snap-slides, big-stat, print-one-per-page]
```

**Build order:** phase 4a = dossier, lesson, brief (one canonical template per mode → full
end-to-end). Phase 4b = paper, chronicle, deck (deck last: scroll-snap, arrow keys,
print-one-slide-per-page are the only nontrivial interactions).

### 8.2 Shared edition chrome (all templates)
Series eyebrow (mono, uppercase, accent) with progress fragment → serif title
(clamp 24–32px, -0.015em) → italic serif dek → mono byline row (reading time · sources · date ·
model) over a 2px ink rule → body → sources → engine footer nav. Inline citations render as small
mono chips (`<sup class="nb-cite"><a href="#sN">N</a></sup>`); sources are a numbered list of
`<li id="sN">` entries each containing `<a data-nb-source href="...">` (+
`data-nb-required="<id>"` when satisfying a required doc).

### 8.3 Design system — default theme "modern digital newspaper" (verbatim tokens)
One token file restyles everything; `site.yaml` points at it. **Base tokens are LIGHT** — light is
the fallback for every degraded case (no JS, no media-query support, print). Dark applies only
when the system requests it (auto) or the user forces it. Default appearance state is `auto`.
Ship exactly this as `engine/assets/themes/newspaper.css`:
```css
:root{  /* LIGHT — the base and universal fallback */
  --bg:#FCFBF9; --panel:#FFFFFF; --wash:#F3F1EC;
  --ink:#171614; --ink-soft:#57554F; --faint:#94918A;
  --accent:#C63D17; --accent-2:#33608F;
  --line:#E2DFD8; --hair:#ECEAE4;
  --serif:"Newsreader",Georgia,serif;
  --sans:"Inter",system-ui,sans-serif;
  --mono:"IBM Plex Mono",monospace;
  --radius:6px;
}
@media (prefers-color-scheme: dark){  /* auto: dark only when the system asks */
  :root{
    --bg:#111213; --panel:#1A1B1D; --wash:#202124;
    --ink:#ECEAE6; --ink-soft:#A9A6A0; --faint:#6F6D68;
    --accent:#E4572E; --accent-2:#7FA8D9;
    --line:#2C2D30; --hair:#242528;
  }
}
:root[data-mode="light"]{ /* manual override; beats the media query by specificity */
  --bg:#FCFBF9; --panel:#FFFFFF; --wash:#F3F1EC;
  --ink:#171614; --ink-soft:#57554F; --faint:#94918A;
  --accent:#C63D17; --accent-2:#33608F;
  --line:#E2DFD8; --hair:#ECEAE4; color-scheme:light;
}
:root[data-mode="dark"]{
  --bg:#111213; --panel:#1A1B1D; --wash:#202124;
  --ink:#ECEAE6; --ink-soft:#A9A6A0; --faint:#6F6D68;
  --accent:#E4572E; --accent-2:#7FA8D9;
  --line:#2C2D30; --hair:#242528; color-scheme:dark;
}
```
Fonts via Google Fonts: Newsreader (display/body serif), Inter (UI/sans), IBM Plex Mono (data).
Usage grammar: serif for titles/deks/article prose; sans for UI and short-form bodies; mono for
eyebrows, bylines, badges, figures. One red-orange accent used sparingly; `--accent-2` reserved
for data/links-secondary. Alternate themes are welcome later; the theme contract is: define
exactly these variables.

### 8.4 Declarative charts (SANDBOX-safe rich content)
Agents never write executable code. A chart is a JSON block; engine-owned nb.js renders it with
version-pinned Chart.js from cdnjs, themed from the CSS tokens.
```html
<figure class="nb-chart" data-nb-section="evidence">
  <figcaption>Fig. 1 · EUV systems shipped per year</figcaption>
  <canvas></canvas>
  <script type="application/json" data-nb-chart>
  {
    "type": "line",                     // line | bar | scatter
    "labels": ["2019","2021","2023","2025","2026e"],
    "series": [ { "name": "EUV systems shipped", "values": [26,42,53,68,74] } ],
    "y": { "scale": "log", "label": "units" }   // scale optional: linear|log
  }
  </script>
</figure>
```
Ship a JSON schema for the chart spec; `B-SANDBOX` verifies every `data-nb-chart` block parses
(malformed JSON = BLOCK). nb.js renders series colors from `--accent` / `--accent-2` /
`--ink-soft`, mono axis type, and re-renders on appearance toggle. The same pattern is the
extension point for future rich blocks (timelines, maps) without ever loosening the sandbox.

### 8.5 Per-template structural notes (signature furniture)
- **dossier** — pill jump-nav (horizontally scrollable on mobile) → cited stat-strip grid →
  numbered sections → a steelmanned `debate` section → `go-deeper`. For companies, technologies,
  institutions, contested questions.
- **lesson** — "In this edition" objectives box → explicit recap referencing the previous edition
  (protocol requires reading it) → concept callouts (accent-left-border) → dashed-rule
  "Check yourself" exercises → "Next edition" bridge callout in `--accent-2`.
- **brief** — stack of tagged items: mono topic tag (above headline on mobile, side column on
  desktop) + serif headline + 1–2 sentence body + a "**Why it matters →**" line; items may
  reference the series' own prior briefs ("we've been tracking…").
- **paper** — "In plain language" abstract panel → two-cell "What holds up" (green label) vs.
  "What to be careful about" (amber label) grid → "Verdict" box in `--accent-2`.
- **chronicle** — timeline spine (2px line, dot per event, filled dots = major) with mono
  date-labels, serif event titles, prose interludes; closes with an "Echoes today" beat.
- **deck** — horizontal scroll-snap slides (16:10 desktop, 4:3 / 88%-width mobile), slide kinds:
  title, statement, big-stat (accent numeral), divider; slide counter top-right; citations in
  slide footers; arrow-key nav on desktop; print = one slide per page.

---

## 9. Skills, AGENTS.md, harness adapters

### 9.0 `AGENTS.md` (auto-read by Claude Code, Codex, Jules)
Short: this repo is The Nightly Build. Scheduled run producing an edition → load
`skills/correspondent/SKILL.md` (fallback: follow `PROTOCOL.md`). Human asking for setup/config →
load `skills/librarian/SKILL.md`. Never push to `library` directly; never edit files under
`library/` in place.

### 9.1 The Librarian (`skills/librarian/SKILL.md`) — setup & curation
Invoked by a human ("set me up", "add a series", "make me a course on X"):
1. Interview: what to learn; one-offs vs. ordered course vs. ongoing briefings; depth; emphases;
   any must-read documents or must-check sites (→ required_docs/required_urls, with the paywalled
   warning from §4.2). Propose series (id, mode, template from the registry, items with
   slugs/titles/tags), show the plan, confirm.
2. Write `series/<id>/series.yaml` + `prompt.md` (+ tag fragments), validating against schemas.
   For sequences, draft the full ordered syllabus with the user.
3. Run `setup.sh` if not bootstrapped.
4. **Offer a press check (§9.5) as the default next step** — see a real edition before scheduling.
5. Harness handoff: detect/ask the harness; read `harnesses/<h>.md`; emit (a) the one-time GitHub
   connection step, (b) the filled §3.1 schedule prompt, (c) model-selection guidance. State
   plainly that scheduling is the one step the skill cannot perform.
6. Curation verbs: add/remove/reorder items, retire series, adjust bands/floors, flip
   autopublish/strict.

### 9.2 The Correspondent (`skills/correspondent/SKILL.md`) — runtime
Procedural implementation of PROTOCOL.md: work selection per mode; prompt-layer order; research
standards; template filling per the registry; nb-meta construction; **the proof loop (run
check.py, revise until BLOCK=0, minimize WARNs)**; PR format; exit-without-PR; supersession
etiquette; rehearsal mode (§9.5) and promotion. Adds craft guidance; PROTOCOL.md wins on conflict.

### 9.3 Harness adapters (`harnesses/*.md`) — docs + one prompt each, not code
Exactly four sections each:
1. **Connect** — one-time GitHub link (Claude: connect the repo at claude.ai/code; Jules: install
   the Jules GitHub app; Codex: connect GitHub in Codex settings).
2. **Schedule** — Claude: `/schedule` or claude.ai/code/routines (a Routine — cloud, laptop-off;
   its default claude/-prefixed branches are fine since semantics live in the PR); Jules: native
   Scheduled Tasks, or the official jules-invoke GitHub Action as a thin cloud trigger; Codex:
   cloud task fired by API/issue-label from a one-line cron workflow (Codex's native automations
   are currently local-machine). Include the filled §3.1 prompt. Recommend one schedule per
   series; document the run-iterates-all-series alternative.
3. **Model** — where model/reasoning choice lives in that harness; nb-meta records what ran.
4. **Verify** — expect a PR titled `nb: ...` in the window; check Actions for the editor's
   verdict; first-run troubleshooting (repo not connected, network access setting, etc).

### 9.5 Press checks — local rehearsal (REQUIRED)
"What would the first generation look like?" — answered minutes after configuration, no
scheduling, no PRs. A Correspondent mode ("run a press check for <series>"):
1. Execute the full contract, diverting at the end: write the edition to
   `press-check/library/<series>/<slug>.html` (gitignored).
2. Run the proof: `check.py <file> --series <id>` — the user sees the exact editor verdict.
3. Preview: `build_site.py --preview press-check/ --out press-check/site/` merges drafts with any
   published library, banners them "PRESS CHECK — unpublished proof," and serves via
   `python3 -m http.server` — the user opens the real newsstand with their draft on it.
4. Iterate: tune prompts → re-run → compare. The intended editorial loop, before and after go-live.
5. **Promote:** "publish this one" → open the real PR from the existing artifact (no duplicate
   research spend), normal validation path.
Both skills note that a press check consumes the same usage as a real run — it IS one, minus
publication.

---

## 10. `setup.sh` (idempotent; callable by the Librarian)
1. Verify `gh` auth + repo context (clear errors if missing).
2. Create orphan `library` branch with `library/.gitkeep` if absent; push.
3. Enable GitHub Pages per §1 invariant 4.
4. Validate `site.yaml` and all `series/*/series.yaml` against schemas; validate registry.
5. Enable repo auto-merge (or print the settings link if API-restricted).
6. Print status + next steps (harness adapters, press check).

## 11. Security model (recap — all mandatory)
- check.yml on `pull_request` with read-only contents; no secrets near untrusted diffs.
- Executable logic only on main; `B-DIFF-SHAPE` prevents PRs from touching it; GitHub separately
  refuses workflow edits without workflow permission.
- `B-SANDBOX` strips all active content from editions; the only agent-authored scripts are
  `application/json` blocks (nb-meta, nb-chart); the only third-party script is version-pinned
  Chart.js, loaded by engine-owned nb.js, never by editions.
- Auto-merge only for BLOCK-clean PRs, only into `library`, only squash.
- Protect `library`: require the check; restrict direct pushes to the publish workflow.
- Credentials never in the repo; paywalled-source stance per §4.2.
- Private-repo operation supported (Pages availability depends on the user's GitHub plan) — README notes it.

## 12. Seed content
No pre-committed editions ship with the project (main stays content-free; the demo library is the
user's own). Ship the `semiconductors` example series config (collection; items: micron, tsmc,
asml, sk-hynix, nvidia; template dossier; a `required_urls` example pointing at sec.gov) as the
canonical first-run: fork → "set me up" → press check on `micron` → the user's own first edition
IS the seed. README screenshots come from a maintainer test library, not committed content.

## 13. Implementation plan (each phase independently verifiable)
1. **Scaffold + protocol** — layout, PROTOCOL.md, AGENTS.md, site.yaml, schemas (meta, series,
   chart, registry), example series, editorial.md.
   ✓ everything schema-validates; PROTOCOL.md alone suffices to hand-write a conforming edition.
2. **The proof** — check.py (both tiers, both invocations), fixtures for every B-/W- code,
   check.yml, auto-merge + supersession jobs.
   ✓ local suite green; hand-crafted valid PR auto-merges on a test repo; every bad fixture yields
   its exact code; a WARN-y valid PR merges with the warnings comment.
3. **Builder + site** — build_site.py, catalog.json, newsstand (mobile feed / desktop grid / lead
   selection), builds/, series/, tags/, search, feeds, nb.js (nav + chart renderer + appearance
   toggle), nb.css, newspaper.css, publish.yml, `--preview` mode.
   ✓ with fixture editions across all modes, every view renders correctly at 390px dark and
   desktop light; toggle persists; charts render and re-theme; press-check preview shows the
   draft banner.
4. **Templates** — 4a: dossier, lesson, brief (registry-complete, chrome per §8.2, furniture per
   §8.5). 4b: paper, chronicle, deck.
   ✓ a sample edition per template passes the proof with BLOCK=0 and renders correctly on mobile.
5. **Skills + adapters + setup.sh + README** — Librarian, Correspondent, three harness docs,
   bootstrap, quickstart.
   ✓ fresh fork + "set me up" in Claude Code reaches "paste this schedule prompt" with no manual
   YAML, and "run a press check" from the same session produces a validated draft on a locally
   served newsstand, promotable to a real PR.
6. **End-to-end** — a real Claude Code Routine on a test fork for two nights (one collection, one
   rolling series).
   ✓ two nightly builds publish unattended; the front page shows a multi-edition build; feeds update.

## 14. Non-goals (v1)
No accounts, backend, or hosted service (catalog.json + feeds ARE the API; a hosted multi-library
reader is a future layer requiring no protocol change). No backfill for rolling series. No
edition-edit/regeneration flow (documented escape hatch: delete the file; the night shift
rewrites). No comments, social, or analytics. Dependency-light forever: Python stdlib + PyYAML +
jsonschema + one HTML parser; hand-rolled static generation; Chart.js is the only runtime
third-party dependency.

## 15. Small decisions delegated to the implementer (decide and document)
Atom vs RSS2 (Atom preferred). `builds/` grouping by nb-meta `date` (recommended) with a
documented tie-break for late merges. gh CLI vs REST for auto-merge/supersession. Exact reading-
time formula. localStorage key names for appearance. Whether the mobile feed truncates non-lead
deks to one line (recommended: yes, with full dek on the edition page).
