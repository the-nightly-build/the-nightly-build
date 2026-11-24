# Feature catalog

Map of supported capabilities and where each is configured.

## Shape the paper

| Capability                | What it supports                                                    | Configure or learn more                                                                                      |
| ------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Paper identity            | Masthead, footer, description, and paper-wide editorial direction   | `press/site.yaml`, `press/editorial.md`, [Appearance and voice](../guides/customize/appearance-and-voice.md) |
| Default paper             | Three starter series; edit each prompt's opening paragraph          | `nb setup`, [Create your paper](../getting-started/create-your-paper.md)                                     |
| Recurring series          | Independent beats, genres, prompts, quality rules, and schedules    | `press/series/<id>/`, [Series reference](series.md)                                                          |
| Series modes              | `collection`, `sequence`, `rolling`, and `open`                     | `mode` in `series.yaml`, [The four modes](series.md#the-four-modes)                                          |
| Sections                  | Single-level grouping on the home page, Sections page, and kickers  | `section` in `series.yaml`, [Cadence, pausing, and sections](series.md#cadence-pausing-and-sections)         |
| Commissions and queues    | Required items (`collection`/`sequence`) or priority queue (`open`) | `items` (with optional prompts/tags) in `series.yaml`                                                        |
| Shared prompt fragments   | Reusable editorial rules attached by item tag                       | `tags` in `series.yaml`, `press/series/_tags/*.md`                                                           |
| Multiple article packages | One fixed template or per-article selection from a list             | `template` or `templates` in `series.yaml`, [Template reference](./templates.md)                             |

## Control timing and publication

| Capability              | What it supports                                                    | Configure or learn more                                                                              |
| ----------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Mixed cadences          | `daily`, `weekdays`, `weekends`, UTC weekday lists, and `manual`    | `cadence` in `series.yaml`, [Cadence, pausing, and sections](series.md#cadence-pausing-and-sections) |
| Pause and resume        | Halt new scheduled articles while keeping the archive live          | `paused` in `series.yaml`                                                                            |
| Deterministic duty list | Computes due work from `main` press config and `library` state      | `nb duty`, [Schedule publication](../guides/operate/schedule.md)                                     |
| Manual publication      | Commission an article from a topic, URL, docs, or brief anytime     | [Publish an article now](../guides/publish/publish-now.md)                                           |
| Hold before publish     | Open a draft PR that CI validates and merges only when marked ready | `nb prepare-pr --hold`, [Your first article](../getting-started/first-article.md)                    |
| Reviewed revisions      | Update one published article and/or assets through proof and render | [Revise an article](../guides/publish/revise-an-article.md)                                          |
| Retraction              | Delete one article, its assets, and records via owner-reviewed PR   | [Manage your paper](../guides/operate/manage-your-paper.md)                                          |
| Automatic publication   | Auto-merges clean new articles and exact workflow syncs             | [Publishing and security](../concepts/publishing-and-security.md)                                    |

## Govern editorial quality

| Capability                    | What it supports                                                      | Configure or learn more                                                                                |
| ----------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Paper and series voice        | Paper-wide register plus series territory, structure, and moves       | `press/editorial.md`, `prompt.md`, [Appearance and voice](../guides/customize/appearance-and-voice.md) |
| Four editorial roles          | Writing coach, researcher, writer, and editor with saved records      | [Architecture](../concepts/architecture.md)                                                            |
| Deterministic proof           | Checks diff shape, metadata, structure, citations, rubrics, rendering | `nb check`, [Publishing and security](../concepts/publishing-and-security.md)                          |
| Strict mode                   | Promotes proof warnings to blocks (except non-promotable advisories)  | `strict` in `series.yaml`                                                                              |
| Geometry guidance             | Recommended ranges for words, repeated items, and flexible sections   | `bands` in `series.yaml`, [Quality and sources](series.md#quality-and-sources)                         |
| Source floors                 | Minimum cited sources with template-aware defaults                    | `min_sources` in `series.yaml`                                                                         |
| Source composition            | Primary/secondary source counts per article or per item               | `sources_by_kind`, `per_item_sources`, [Source composition](series.md#source-composition)              |
| Required and bounded research | Mandatory citations, background docs, or closed-world source sets     | `required_docs`, `consult`, `sources_exclusive` in `series.yaml`                                       |
| Enforced review rubrics       | Pinned criteria, 0–5 score integrity, and cited justifications        | `rubric` in `series.yaml`, [Rubrics](series.md#rubrics)                                                |
| Banned prose patterns         | Engine vocabulary/prose rules plus press overrides and additions      | `press/banned-terms.yaml`, [Appearance and voice](../guides/customize/appearance-and-voice.md)         |

## Choose models and execution

| Capability                       | What it supports                                                     | Configure or learn more                                                     |
| -------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Portable cost profiles           | `inherit`, `economy`, `balanced`, and `quality`                      | `profile` in `press/production.yaml`, [Production](production.md)           |
| Portable model tiers             | `efficient`, `capable`, `premium`, or `inherit`                      | `model` on a stage                                                          |
| Exact model selection            | Pin a provider-specific model ID                                     | Set stage `model` to the exact provider model ID                            |
| Per-role reasoning effort        | Provider-supported effort level per stage                            | `effort` on a stage                                                         |
| Required or best-effort routing  | Enforce stage model/effort or allow logged orchestrator judgment     | `required` paper-wide or per stage                                          |
| Per-series production overrides  | Override profile, stage model/effort, or `required` for one series   | `production` in `series.yaml`                                               |
| Isolated or sequential execution | Isolated child roles when supported; sequential fallback with parity | Selected by runtime capability, [Architecture](../concepts/architecture.md) |

Production policy applies to article roles only. Configure the orchestrator's
model in your scheduler, and check provider reports for actual usage and cost.

## Design articles and the site

| Capability               | What it supports                                                      | Configure or learn more                                                                                   |
| ------------------------ | --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Theme and color mode     | Shipped or press-owned CSS with `auto`, `light`, or `dark` appearance | `theme`, `appearance` in `site.yaml`, [Appearance and voice](../guides/customize/appearance-and-voice.md) |
| Front-page density       | Compact cells or comfortable cells with deks                          | `front` in `site.yaml`, [Site reference](site.md)                                                         |
| Reusable furniture       | Timelines, tables, figures, pull quotes, rubrics, reading/quote cards | `templates/FURNITURE.md`, `press/furniture/`, [Furniture reference](furniture.md)                         |
| Custom templates         | Press-owned skeletons with enforced sections, chrome, and citations   | `press/templates/<id>/`, `examples/templates/`, [Customize templates](../guides/customize/templates.md)   |
| Figures and charts       | Local images and charts stored with each article; revisable later     | `library/SERIES/SLUG/`, [Architecture](../concepts/architecture.md)                                       |
| Trusted external assets  | Owner-declared HTTPS scripts and styles with exact SRI hashes         | `assets` in `site.yaml`, [Site reference](site.md)                                                        |
| Accessible static output | Script-free semantic articles checked in a headless browser           | [Template reference](./templates.md), [Publishing and security](../concepts/publishing-and-security.md)   |

## Operate and deliver

| Capability                         | What it supports                                                     | Configure or learn more                                              |
| ---------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Guided setup                       | Initializes `press/`, `library`, workflows, and GitHub settings      | `./nb setup`, [Set up](../getting-started/setup.md)                  |
| Separate setup and schedule agents | Pair any interactive agent with ChatGPT Work or Claude Code Routines | [Integrations](../integrations/README.md)                            |
| Engine updates                     | Merge upstream engine changes cleanly and sync `library` workflows   | `nb sync`, [Update the engine](../guides/operate/update-engine.md)   |
| Static GitHub Pages paper          | Full static site with zero backend or database                       | [Delivery](delivery.md)                                              |
| Full-text search and catalog API   | `search-index.json` and machine-readable `catalog.json`              | [Delivery](delivery.md#catalogjson-the-api)                          |
| Atom feeds                         | Paper-wide and per-series feeds with full recent article HTML        | [Delivery](delivery.md#feeds-zero-setup)                             |
| Shared directory                   | Automatic listing on the Nightly Build directory with opt-out        | `directory` in `site.yaml`, [Delivery](delivery.md#the-directory)    |
| Article history search             | Targeted prior-coverage lookup without loading the full archive      | `nb history`, [Architecture](../concepts/architecture.md)            |
| Pinned series voice guide          | Fixed series voice standard that skips the writing coach stage       | `voice_guide` in [Series reference](series.md#pinning-a-voice-guide) |

Browse `examples/` for a complete sample press (never read as live config). The
reference pages above are the complete contract.
