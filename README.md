# The Nightly Build

![The Nightly Build](assets/the-nightly-build-banner.png)

The Nightly Build is an engine for running a personal, AI-researched
newspaper. You fork this repository, describe what you want to read, and a
scheduled agent researches and publishes cited articles to your own GitHub
Pages site every night. Git is the entire protocol: any agent that can open
a pull request can be your night shift.

Articles are original research artifacts, not summaries: each is a deeply
researched, fully cited piece, shaped to fit its topic. You describe what you
want covered and how deep to go; the night shift does the research, holds the
sourcing and quality bar, and publishes. Over weeks the output accumulates into
a permanent, searchable library that you own and that GitHub serves for free.

## What it looks like

One clean column, a ruled index, and every card carrying its reading time and
source count. The reader's front page and a single article, on a phone:

<p>
<img src="assets/screenshots/front-phone.png" width="48%" alt="The front page on a phone">
<img src="assets/screenshots/article-phone.png" width="48%" alt="An article on a phone">
</p>

## Quickstart

1. Fork this repository (keep GitHub's "Copy the main branch only" box
   checked). Keep it public if you want the published site: GitHub Pages needs
   a public repo on the free plan.
2. Clone your fork and tell your agent "set me up", or run `./setup.sh` and
   edit `press/` by hand. Setup scaffolds your configuration, creates the
   `library` branch, and enables Pages and auto-merge. Enable workflows once
   in your fork's Actions tab. A complete working configuration ships in
   `examples/` to copy from.
3. Rehearse. Ask your agent for a "press check": a full research run
   rendered to a locally served site, with no PR, so you can tune prompts
   before scheduling anything.
4. Connect and schedule. Pick a path in [docs/scheduling.md](docs/scheduling.md):
   a provider's native scheduler (often included in a plan you already pay for)
   or the universal GitHub Actions cron that runs any headless agent. Schedule one nightly job for the whole
   paper and trigger it once now for today's first article. Each run derives its
   work list from the repo, so you never touch the schedule again.
5. Read. The night shift opens one PR per series, CI validates and (for
   `autopublish` series, which the examples enable) merges, the site rebuilds,
   and the Atom feed delivers it.

## How it works

| Piece             | Where                   | Purpose                                                                                                                                                                                                   |
| ----------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PROTOCOL.md`     | main                    | The complete agent contract                                                                                                                                                                               |
| the proof         | `engine/check.py`       | Validates articles. BLOCK findings stop publication; WARN findings drive revision                                                                                                                         |
| the desk          | `check.yml`             | Validates every PR to `library`; auto-merges clean ones from `autopublish` series (otherwise a human merges); supersedes competitors                                                                      |
| the press         | `engine/build_site.py`  | Rebuilds the site on every merge: front page, night archive, sections, search, feeds                                                                                                                      |
| duty              | `engine/duty.py`        | Deterministic nightly work selection: cadence, pauses, completion, commissions                                                                                                                            |
| templates         | `templates/<id>/`       | Two citation geometries, each a self-contained folder package (manifest, skeleton, brief, optional furniture), plus a shared furniture catalog. User templates in `press/templates/<id>/` are first class |
| the correspondent | `skills/correspondent/` | The night desk: reads duty, commissions every due article, hands each to its own desk, sees the PRs through CI                                                                                            |
| a desk            | `skills/desk/`          | One article, end to end: runs the role chain below in its own worktree, proves the draft, opens the PR                                                                                                    |
| the writing coach | `skills/writing-coach/` | Studies how the best writers in a topic actually write, then hands the drafter a per-article voice brief                                                                                                  |
| the editor        | `skills/editor/`        | A surgical editorial pass over each draft: cuts and tightens in place or asks for a redraft, never rewrites                                                                                               |
| the librarian     | `skills/librarian/`     | Setup interview and ongoing curation of `press/`                                                                                                                                                          |

Two branches with disjoint jobs: `main` holds the engine and your
configuration, `library` holds published articles, which the press builds into
the live Pages site on each merge.
`press/` is the only directory you edit. It does not exist upstream, so
pulling engine updates is an ordinary merge with nothing to conflict.

## Configuration

Series live in `press/series/<id>/` as a `series.yaml` plus a prompt file.
Four modes: `collection` (an item list, published front to back or at
random), `sequence` (an ordered course), `rolling` (one article per date),
and `open` (you describe a beat, the agent picks each night's topic and
genre). Cadence, pausing, sections, source requirements, and quality bands
are one-line settings. See [docs/series.md](docs/series.md).

Sources can be constrained per series: `required_docs` are committed files
the agent must read and cite, `consult` lists must-read starting points, and
`sources_exclusive: true` restricts citations to the declared set. The three
sit at different tiers of the proof: `sources_exclusive` is an unconditional
BLOCK (a citation outside the declared set fails the PR); a missing
`required_docs` citation is a WARN that a `strict` series promotes to a BLOCK;
`consult` is a read-first instruction the proof does not verify (citing a
consulted source is optional).

A count says nothing about what kind of sources came in, so a series can also
constrain the mix: `sources_by_kind` and `per_item_sources` set `[low, high]`
bands over primary and secondary sources, and both BLOCK. The proof counts the
kinds the article declares; whether a source is truly independent of the primary
is a judgment the research log makes and the editor audits. See
[docs/series.md](docs/series.md).

The proof also verifies that every cited source link resolves. It probes each
URL by default and BLOCKs only on a definitive dead link: a 404/410
response or a domain that does not resolve. A restricted, slow, rate-limited,
bot-blocking (403), or timing-out source is treated as unverified and never
blocks, so a real-but-gated source cannot fail an article.

## Security

No executable logic ever lives on the `library` branch. Articles are
sandboxed: no scripts beyond JSON data blocks and the engine runtime, no
iframes, no event handlers, and external references only to the engine
assets path and Google Fonts. The desk validates untrusted PRs with
read-only permissions and no secrets. Auto-merge is squash-only, into
`library` only, for BLOCK-clean PRs only. Your agent's API key exists only as
an Actions secret on the trusted scheduled path, never where PR validation runs.

Anyone can open a pull request to a public site, but no stranger can publish
through one. The desk runs on the `pull_request` event, so a PR from a fork
receives a read-only token and cannot merge itself; only a branch pushed to the
site's own repository (the night shift, holding that repository's token) opens
a same-repo PR that auto-merge can act on. The guarantee is the token split
between fork and same-repo PRs, not article validation, so the trigger is
`pull_request` and never `pull_request_target`, and a test enforces that so it
cannot silently regress.

A site may load libraries to power its furniture (a syntax highlighter, say)
by declaring them in `press/site.yaml`. That surface preserves the boundary:
the list is owner-authored on `main`, never by an auto-merged article; every
entry is version-pinned and Subresource-Integrity-hashed; and articles stay
script-free, so the sandbox above is unchanged. See
[docs/customization.md](docs/customization.md).

## Development

uv is required for every local, CI, and harness Python invocation. Install it
from [the official installer](https://docs.astral.sh/uv/getting-started/installation/),
then run `uv sync --group figure-capture`. The engine has one runtime dependency,
PyYAML; its scripts
carry PEP 723 metadata, so `uv run engine/check.py` resolves it without a
separate environment. Local development and CI use `pyproject.toml` and target
Python 3.10+.

```sh
uv run pytest                                  # proof, builder, and end-to-end suites
uv run engine/validate_config.py --repo .      # validate press/ configuration
```

Engine changes go through a lint, type-check, format, and test gate that CI
enforces on `main`. Set it up once:

```sh
uv sync --group figure-capture # Python tools and capture dependencies
npm install                 # web tools: prettier, eslint, stylelint, markdownlint
uv run pre-commit install   # run the same checks on every commit
```

Figure capture is an optional authoring toolchain. Its bootstrap installs the
repo-pinned Python packages and Playwright's Chromium browser in one step:

```sh
./scripts/install-figure-capture.sh
```

Chromium is not committed and never runs in site CI or in a reader's browser.
Re-run the command after updating the lockfile or when Playwright reports that
its browser revision is missing.

`pre-commit` runs exactly what CI runs (the Rust drop-in `prek` reads the same
config). The shell hooks also need `shellcheck` and `shfmt` on your PATH;
install them from your package manager.

This repository is engine-only. It runs no site and publishes no library;
the maintainer dogfoods by copying it like any other user. `examples/`
contains a complete working configuration as documentation.

## Docs

- [Your site: ownership, forks, updates](docs/press.md)
- [Series: modes, open sections, cadence, commissioning](docs/series.md)
- [Scheduling: native schedulers, the universal Actions cron](docs/scheduling.md)
- [Harnesses: which agents can run the night shift, and the cost](docs/harnesses.md)
- [Customization: themes, voice, your own templates](docs/customization.md)
- [Source figures: capture and article bundles](docs/figures.md)
- [Delivery: feeds, the directory, the catalog API](docs/delivery.md)

Published sites are listed automatically on
[the-nightly-build.github.io](https://the-nightly-build.github.io/), a shared
front page over every paper (set `directory.publish: false` to opt out). See
[docs/delivery.md](docs/delivery.md).

MIT licensed. No accounts, no backend, no analytics. `catalog.json` and the
Atom feeds are the API.
