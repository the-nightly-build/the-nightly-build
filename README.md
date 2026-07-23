# The Nightly Build

![The Nightly Build](assets/the-nightly-build-banner.png)

> Your own AI-researched morning paper, published while you sleep.

The Nightly Build turns a GitHub repository into a personal newspaper. Describe
what you want to read, connect an agent, and get original, cited articles on
your own GitHub Pages site every morning.

No backend. No accounts. No analytics. Your paper and its archive live in your
fork.

## How it works

```text
main
  your engine and paper configuration
          ↓
night shift
  researches, writes, and opens a pull request
          ↓
library
  validates and publishes the article
          ↓
GitHub Pages
  rebuilds your paper, search, and feeds
```

You configure the paper in `press/`. The scheduled agent reads that
configuration, selects the sections due that night, and opens one pull request
per section. The proof checks the article's structure, sources, and safety
before a clean pull request is merged into `library`.

`main` holds the engine and your configuration. `library` holds published
articles. Keeping those branches separate makes engine updates and paper
ownership straightforward.

## Get started

### 1. Fork and bootstrap

Fork this repository with **Copy the main branch only** enabled. Keep the fork
public if you want to use GitHub Pages on the free plan.

Clone the fork and run the setup script:

```sh
git clone https://github.com/<you>/<your-paper>.git
cd <your-paper>
./setup.sh
```

The script scaffolds `press/`, creates the empty `library` branch, seeds its
workflows, and configures GitHub Pages and auto-merge. It requires `git`,
`gh` (authenticated), Python 3.10+, and PyYAML.

### 2. Configure your paper

Ask your agent to **set me up**, or copy a starting point from [`examples/`](examples/README.md).
Your paper lives in one small configuration tree:

```text
press/
├── site.yaml                 # title and appearance
├── editorial.md              # paper-wide voice
└── series/<id>/
    ├── series.yaml           # cadence and publishing rules
    └── prompt.md             # what this section covers
```

See [Your paper](docs/press.md) and [Series](docs/series.md) for the full
configuration model.

### 3. Rehearse once

Ask your agent for a **press check**. It runs the article workflow locally,
builds a preview, and lets you tune your paper before anything is published.

### 4. Schedule the night shift

Connect one agent with repository access and schedule one nightly run. The run
derives its work from `press/`, so you do not need to update the schedule when
you add or pause a section.

Choose a provider schedule or the universal GitHub Actions path in
[Scheduling](docs/scheduling.md). [Harnesses](docs/harnesses.md) lists the
supported agents and how their usage is billed.

### 5. Read your paper

The night shift opens pull requests against `library`. Once the first article
merges, GitHub Pages publishes the newsstand, archive, search index, and feeds.
See [Delivery](docs/delivery.md) for the URLs and feed formats.

## Make it yours

- Change the title and appearance in `press/site.yaml`.
- Set the paper-wide voice in `press/editorial.md`.
- Add sections, beats, cadence, and source requirements under `press/series/`.
- Customize themes, furniture, and templates in `press/`.

The [examples](examples/README.md) are a living reference. [Customization](docs/customization.md)
covers the extension points without requiring engine changes.

## Development

The engine targets Python 3.10+ and uses `uv`:

```sh
uv sync --group figure-capture
uv run pytest
uv run engine/validate_config.py --repo .
```

Web and documentation checks use the tools in `package.json`:

```sh
npm install
npm run lint
```

Read [PROTOCOL.md](PROTOCOL.md) for the complete article contract and
[Updating the engine](docs/press.md#updating-the-engine) for the fork update
flow.

MIT licensed. The catalog and Atom feeds are the API.
