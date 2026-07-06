# The Nightly Build

*Built while you sleep.*

Fork one repo. Tell your AI agent **"set me up."** Paste one schedule prompt
into your harness. Every morning, open your phone to **tonight's build**: deep,
cited, beautifully rendered research editions on the things you want to learn —
published to your own GitHub Pages library.

Over weeks this accumulates into a personal library: **courses** that progress
in order, ongoing **briefings**, **collections** of deep dives — permanent,
searchable, owned by you, served free from GitHub Pages.

- **Research, not summarization.** Editions are original cited research
  artifacts: dossiers, lessons, briefs, paper appraisals, chronicles, decks.
- **Git as the protocol.** Any agent that can open a pull request can be your
  night shift — Claude Code, Jules, and Codex adapters ship in `harnesses/`.
- **A safety gate, not a quality gate.** CI (the **editor**) guarantees the
  site can never break; quality pressure happens inside the agent's loop via a
  repo-shipped checker (the **proof**). A missed night is worse than a thin
  edition.
- **Forkable and permanent.** `main` contains zero content; a fork is a blank
  press. Your editions live on the `library` branch forever.
- **Mobile first.** ~95% of reads happen on a phone; every surface is designed
  for one.

## Five-minute quickstart

1. **Fork** this repo (public or private — Pages on private repos needs a paid
   GitHub plan). Leave GitHub's **"Copy the `main` branch only"** box checked:
   you get the engine and the example series, never the upstream library —
   your press starts blank.
2. **Clone it and say "set me up"** to your agent (Claude Code, etc.) in the
   checkout. The Librarian skill clears the upstream dogfood series, interviews
   you, writes your series config, and runs `./setup.sh` (creates the `library`
   branch, seeds its trigger workflows, enables Pages and auto-merge). No agent
   handy? Delete `series/semiconductors`, `series/ai-briefs`, and
   `series/_tags`, configure your own `series/<id>/series.yaml` (the deleted
   ones are complete examples — crib from them on GitHub), then run
   `./setup.sh`.
3. **Rehearse:** ask for a **press check** — a full research run rendered to a
   locally served newsstand, no PR, so you can tune the prompt before
   scheduling.
4. **Schedule:** open your harness's adapter in `harnesses/` and paste the
   filled schedule prompt it gives you. **One nightly schedule for the whole
   press, ever** — each run derives its work list from the repo, so adding or
   finishing series never touches the schedule again. (On a fork, also visit
   the Actions tab once and enable workflows — GitHub disables them on forks
   by default.)
5. **Sleep.** The night shift opens a PR; the editor validates and merges; the
   press deploys. Subscribe to `feed.xml` for morning delivery.

## How it works

| Piece | Where | What it does |
|---|---|---|
| `PROTOCOL.md` | main | The complete agent contract; self-sufficient |
| the proof | `engine/check.py` | Two tiers: BLOCK (publishing bar, CI-enforced) and WARN (quality bar, agent-iterated) — the same tool in both places |
| the editor | `.github/workflows/check.yml` | Validates every PR to `library`; auto-merges clean ones; supersedes competitors |
| the press | `engine/build_site.py` + `publish.yml` | Rebuilds the site on every merge: newsstand, per-night builds, series pages, tags, search, Atom feeds |
| templates | `templates/` | Six registry-defined layouts: dossier, lesson, brief, paper, chronicle, deck |
| skills | `skills/` | Librarian (setup & curation) and Correspondent (the night shift runtime) |

**Security spine:** no executable logic ever lives on the `library` branch;
editions are sandboxed (no scripts beyond JSON data blocks and the engine's own
runtime, no iframes, no event handlers); CI runs with read-only contents and no
secrets against untrusted diffs; auto-merge is squash-only, into `library`
only, for BLOCK-clean PRs only.

## Try the engine locally

```
python3 engine/tests/run_tests.py        # the proof + builder suites
python3 engine/validate_config.py        # validate site + series configs
```

## Repository layout

```
PROTOCOL.md            the agent contract        spec/         editorial voice + schemas
AGENTS.md              agent entry point         series/       your series configs
templates/             the six edition layouts   engine/       check.py, build_site.py, assets
skills/                librarian + correspondent  harnesses/   claude / jules / codex adapters
setup.sh               idempotent bootstrap      .github/      the editor + the press
```

**This repo dogfoods itself.** The shipped series are the upstream night
shift's real assignments, so the maintainer's Pages site is a live demo of
exactly what a fork produces. Your fork inherits those *configs* only, and
setup always clears them — they exist as living examples, not starter content.

MIT licensed. No accounts, no backend, no analytics — `catalog.json` and the
Atom feeds *are* the API.
