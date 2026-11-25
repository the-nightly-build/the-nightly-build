# Documentation

The Nightly Build turns a configured press into a published paper.

## Getting started

- [Ask your AI](getting-started/ask-your-ai.md): shortest path to a first
  published article
- [Set up your paper](getting-started/setup.md): terminal vs. ChatGPT Work setup
  and `./nb setup`
- [Your first article](getting-started/first-article.md): what happens from
  request to live page
- [Create your paper](getting-started/create-your-paper.md): personalize the
  default press or design one from scratch
- [Agent integrations](integrations/README.md): setup and scheduling for Claude
  Code, Codex, and ChatGPT Work

## Guides

- **Operate:** [schedule publication](guides/operate/schedule.md),
  [manage your paper](guides/operate/manage-your-paper.md),
  [update the engine](guides/operate/update-engine.md),
  [verify the scheduled runtime](guides/operate/verify-scheduled-runtime.md)
- **Publish:** [publish an article now](guides/publish/publish-now.md),
  [revise a published article](guides/publish/revise-an-article.md)
- **Customize:**
  [appearance and voice](guides/customize/appearance-and-voice.md),
  [furniture](guides/customize/furniture.md),
  [templates](guides/customize/templates.md)

## Concepts

- [Architecture](concepts/architecture.md): orchestrator, editorial roles,
  engine checks, and PR boundary
- [Ownership and branches](concepts/ownership-and-branches.md): `press/`, engine
  files on `main`, and `library`
- [Publishing and security](concepts/publishing-and-security.md): trust
  boundaries, auto-merge, and branch protection

## Reference

- [Feature catalog](reference/README.md): map of supported capabilities and
  where each is configured
- [Site](reference/site.md) · [Series](reference/series.md) ·
  [Templates](reference/templates.md) · [Furniture](reference/furniture.md) ·
  [Production](reference/production.md) · [Delivery](reference/delivery.md)

## Troubleshooting

- [Setup and scheduling](troubleshooting/setup-and-scheduling.md)
- [Article PRs](troubleshooting/article-prs.md)

---

Agent instructions live in `.agents/`, where your assistant loads the skill for
each task. Contributor specifications for article quality and the engine live in
`spec/`.
