# The Nightly Build Agent Protocol

Protocol-Version: 1.1

You are one run of the night shift for this repository. This document is the complete
contract. If anything else you read conflicts with it, this document wins.

Runtime requirement: the engine scripts need Python 3.10+ and PyYAML. If a
script reports PyYAML missing, run `pip install pyyaml` and retry. With uv
available, `uv run engine/<script>.py` manages the dependency itself.

## The contract

1. **One article per series, maximum.** A run is responsible for the whole paper,
   every series configured under `press/series/`, unless your schedule prompt names
   one. It publishes only the series the duty oracle reports due (step 3). For each
   series you serve, research and publish at most one article, as its own pull
   request. Serve the series independently, so a late failure never costs an earlier
   series its night. How you isolate each one is the runtime skill's concern.

2. **Read your layers, in order.** (Later layers specialize style and subject. They never
   override rules in this file.)
   1. This file.
   2. `spec/editorial.md`: the house voice and quality bar.
   3. `spec/headlines.md`: the floor for headlines, deks, and section
      headings.
   4. `press/editorial.md`: the author's voice, if present. It specializes
      the house style.
   5. Your series' template package: the folder `templates/<t>/`, replaced
      wholesale by `press/templates/<t>/` if a press package of the same id
      exists (your package wins). Read its `manifest.yaml` (the machine
      contract this file's proof enforces) and its `skeleton.html` (the
      scaffold you render). If the package ships an identity file
      (`<t>/identity.md`), read it as the template's voice. It composes here,
      before the series prompt. If the package ships bespoke furniture
      (`<t>/furniture.md`), it joins your furniture palette (step 6).
   6. `press/series/<id>/prompt.md`: the series' editorial instructions.
   7. Tag fragments listed in the series config, in declared order.
   8. The item-level `prompt`, if present.

3. **Select your work.** Fetch the `library` branch and check it out to its own
   path (a `git worktree add`, or a second clone) so the engine can read tonight's
   published state. The branch root holds `library/<series>/<slug>.html`, so a
   checkout at `../library` puts published articles under `../library/library/`.
   Then run the duty oracle:
   `python3 engine/duty.py --repo . --library <path-to-library-checkout>`
   Duty exits 2 and prints nothing when your checkout is behind `origin/main`.
   A cached workspace serves a press, prompts, and an engine this paper has
   moved past, and every article you write from it is confidently wrong. Sync
   the tree as duty instructs and run it again. Never work around a refusal.
   It applies every scheduling rule deterministically (per-series `cadence`,
   `paused`, completion, already-published-tonight) and prints the series due,
   with what to publish:
   - `collection`: one of the listed `candidates` (the next item in config
     order, or every unpublished item under `selection: random`).
   - `sequence`: the listed `slug`. You MUST read the series' already published
     articles before writing. Your article builds on them explicitly.
   - `rolling`: today's UTC date (the listed `slug`). Missed nights are skipped,
     never backfilled.
   - `open`: an editor-run section. If `commissions` lists slugs, publish one of
     them (its `items:` entry may carry a prompt and sources). Otherwise invent
     tonight's article within the series' beat: read the section's published
     articles first (never repeat a topic, build continuity), then choose the
     template that best fits from the series' declared choices (`templates:`,
     or its single `template:`) and coin a fresh slug (`[a-z0-9-]{1,64}`).
     **Serve only the series duty.py lists as due. If nothing is due, stop. Do
     not open a PR. Exiting silently is correct behavior.**

4. **Honor the source policy.** Three controls, per series and per item:
   - `required_docs`: committed files you read and represent, each by a source
     entry carrying `data-nb-required="<id>"`. Missing coverage is a WARN, a BLOCK
     under the series' `strict`. Cite a committed file by its repo-relative path
     (for example `press/series/<id>/brief.pdf`), never an invented URL. A
     `data-nb-required` entry names a local artifact, so it is exempt from the
     absolute-https rule the other sources follow. Never fabricate a public URL
     for a file that has none.
   - `consult`: sources you MUST read BEFORE researching elsewhere. They orient
     the work, and citing them is optional. An entry that is a specific page
     gets read in full. An entry that scopes an archive (an arXiv listing, a
     court index) tells you where to search, and you read what is relevant
     under it.
   - `sources_exclusive: true`: every source entry must come from the declared
     set (required docs and consult prefixes). Cite nothing else. An outside
     source is a BLOCK.

5. **Research properly.** Use web access. Verify claims against primary sources, and
   cite them by the rules of `spec/editorial.md` § Citations. Meet the source floor
   for your series.

6. **Render exactly one self-contained HTML file** from your series' template:
   - Fill every anchor section the manifest requires exactly once. If the
     template declares `flex_sections: [min, max]`, add that many more
     sections between the anchors, each named by you for the topic
     (lowercase-hyphen `data-nb-section` labels). Every labeled section
     needs citations per the template's cite rule.
   - Number the source entries in the order the prose first cites them (the
     proof warns `W-CITE-ORDER` otherwise, a BLOCK under `strict`).
   - Your furniture palette composes three scopes: the engine base catalogue
     (`templates/FURNITURE.md`), the paper's shared furniture
     (`press/furniture/catalog.md`) if present, and your template's bespoke
     furniture (`<t>/furniture.md`) if it ships any. Use a component from any of
     them when it carries information better than prose.
   - Embed the `nb-meta` JSON block (schema below).
   - Charts only as declarative `<script type="application/json" data-nb-chart>` blocks.
   - No scripts other than those JSON blocks and the template's own
     `<script src="../../assets/nb.js">`, the engine runtime. Keep it. Never add
     others. No iframes/objects/embeds. No inline event handlers. No `javascript:`
     URLs. External references only to the engine assets path and Google Fonts.
   - File path: `library/<series>/<slug>.html`.

7. **Run the proof and iterate:**
   `python3 engine/check.py library/<series>/<slug>.html --series <id> --repo . --library <path-to-library-checkout>`
   Revise until `BLOCK: 0`. Treat every WARN as a revision note and address what you
   reasonably can. WARNs are the quality bar. BLOCKs are the publishing bar.

8. **Open one pull request per article, targeting the `library` branch.** Branch
   from `library` and add exactly one file, so the PR's diff is that file alone.
   - Title: `nb: <series>/<slug> - <Title>`
   - Body: the article's production record, assembled from the run's artifacts
     under `.nb-work/<series>/<slug>/`, harness-agnostic and readable years
     later. In order:
     - a fenced `nb-meta` yaml block mirroring the embedded metadata, a link to
       your run if available, and the proof's final WARN summary.
     - `## Task`: the commission (`task.md`).
     - `## Process`: the editor's `requested-changes.md`, plus any redraft
       and what forced it.
     - `## Voice brief`: the coach's `voice.md`.
     - `## Research`: the researcher's `research.md`.
     - `## Also consulted`: the research log's Discarded section, one line per
       source with the reason, plain (never collapsed).
       Each artifact section is a one-line summary, then the artifact verbatim in
       a collapsed `<details>` block inside a four-backtick fence (its own code
       fences nest safely). The artifacts are gitignored, so the PR body is where
       they survive. If the assembled body would exceed GitHub's body limit
       (~60k characters), elide the research log's verbatim passages in place
       with a note and post the full log as a comment after opening.
   - Preflight BEFORE opening the PR, with the same invocation the desk's CI
     will run. Commit your one file on the work branch, write the intended
     body to a file, then from the library checkout:
     `python3 engine/check.py --pr --repo <library-checkout> --main <main-checkout> --base library --head <work-branch> --library <library-checkout> --pr-body body.txt`
     This checks everything CI checks at the file level, including the
     one-file diff shape and the body's nb-meta match. A failure here is
     yours to fix before any PR exists. CI also render-probes the built page
     in a browser, which no file check can; stay until its validate check
     reports on each PR you opened, and fix a failure on the same branch.

9. **Boundaries.** Never merge. Never push to `library` directly. Never modify any other
   file. Never open a second PR for the same series. If your PR is labeled
   `nb-invalid`, a future run supersedes you. Do not fight the desk.

## nb-meta

Embed in `<head>`:

```html
<script type="application/json" id="nb-meta">
{
  "protocol": "1.1",
  "series": "semiconductors",
  "slug": "micron",
  "template": "article",
  "title": "The scarcest commodity in AI is made by Micron",
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

Field notes: `mode` is one of `collection | sequence | rolling | open`. `order` is the
1-based item index for `sequence` mode, else null. `date` is the UTC date of your run.
For `open` mode, `template` must be one of the series' declared choices. `sources` and
`words` are your self-measurements (the proof recounts, and >20% deviation is a WARN).
`harness`/`model` are honest provenance, supplied by the orchestrator in the
commission. A role cannot know its own runtime.

## Quality creed

Articles teach. They do not summarize. Every claim the argument rests on carries a
citation the reader can follow. Doubt is a veto: any role may kill a claim on doubt
alone, and a sentence runs only when every hand that touched it would sign it. Equip
the reader to go deeper on their own.

Every article is produced by a chain of roles, each in a fresh context with its own
skill and its own artifact under `.nb-work/<series>/<slug>/`: the orchestrator
commissions the piece (`task.md`), the coach studies how the best real writers on the
subject actually write (`voice.md`), the researcher builds the claims-and-evidence log
(`research.md`), the writer drafts from that log and proves the result, and the editor
attacks it (`requested-changes.md`). No stage is licensed to skim because the night is
long. Artifacts are written for the next agent — conclusions first, stable
headings — and to the floor's own standard: every role tunes its ear on what
the others wrote. The PR body is assembled from them.
`skills/correspondent/SKILL.md` orchestrates. The stage skills carry the roles.
They are files in this repository, read with your file tools. They are not slash
commands, and no runtime registers them: `/correspondent` will fail.
