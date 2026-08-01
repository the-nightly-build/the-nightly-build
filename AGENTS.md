# The Nightly Build

The Nightly Build turns a configured press into a cited static paper. Agents
research and propose articles; the repository-owned engine and CI decide what
is safe to publish.

## Start with the right map

- Human documentation begins at `docs/README.md`.
- `docs/concepts/architecture.md` explains the production and publication flow.
- `docs/reference/README.md` is the complete feature and configuration catalog.
- `press/` is the paper owner's specification on `main`; `examples/` is
  documentation, never live configuration.
- `library` is protected publication state. Never commit, push, or merge to it
  directly.
- `spec/editorial.md` and `spec/headlines.md` govern article quality.
  `spec/prompting.md` governs changes to shipped or press-owned prompts.

## Route by invocation

- **A human paper owner** asking for setup, configuration, publication,
  revision, design, curation, or maintenance: load
  `.agents/skills/nb-user-assistant/SKILL.md`.
- **An actual unattended scheduled run:** follow
  `.agents/prompts/run-scheduled-publication.md` in this agent. It resolves
  scheduled work, loads the orchestrator skill, and remains the orchestrator.
- **An explicit bounded editorial assignment:** load the named role under
  `.agents/skills/nb-<role>/SKILL.md` and use only its supplied brief and inputs.
- **An engine, documentation, or test contribution:** work from the public
  docs and repository normally; do not load a production role.

Use this checkout's `nb` command for deterministic operations. Article
publication and revision go through the validated PR paths owned by the
relevant workflow.
