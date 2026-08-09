# Documentation

The Nightly Build turns a configured press into a published paper. Start with
the path that matches what you are trying to do.

## Start here

- [Ask your AI](getting-started/ask-your-ai.md) is the shortest path from this
  repository to a working paper.
- [Set up](getting-started/setup.md) explains the accounts, tools, permissions,
  and handoffs involved.
- [Create your paper](getting-started/create-your-paper.md) describes the
  editorial decisions worth making before configuration.
- [Verify the scheduled runtime](getting-started/first-run.md) runs a
  non-publishing smoke test in the actual automation environment.

## Operate your paper

- Operate: [manage your paper](guides/operate/manage-your-paper.md),
  [schedule publication](guides/operate/schedule.md), or
  [update the engine](guides/operate/update-engine.md)
- Publish: [publish an article now](guides/publish/publish-now.md) or
  [revise a published article](guides/publish/revise-an-article.md)
- Customize [appearance and voice](guides/customize/appearance-and-voice.md),
  [furniture](guides/customize/furniture.md), or
  [templates](guides/customize/templates.md)

## Understand and reference the system

- Start with the [feature catalog](reference/README.md) for the complete map of
  supported capabilities and their configuration.
- Concepts: [architecture](concepts/architecture.md),
  [ownership and branches](concepts/ownership-and-branches.md), and
  [publishing and security](concepts/publishing-and-security.md)
- Reference details: [site](reference/site.md), [series](reference/series.md),
  [templates](reference/templates.md), [furniture](reference/furniture.md),
  [production](reference/production.md), and [delivery](reference/delivery.md)
- [Agent and scheduler integrations](integrations/README.md)
- Troubleshoot [setup and scheduling](troubleshooting/setup-and-scheduling.md)
  or [Article PRs](troubleshooting/article-prs.md)

These pages explain how the system works and which decisions are yours. The
skills under `.agents/` are where agents learn to execute the work, sometimes
autonomously and sometimes with you, depending on the skill. These pages point
at skill files by path, and your assistant reads them itself.

Files under `spec/` are production contracts for article-making agents and the
engine. They are useful to contributors, but they are not the user manual.
