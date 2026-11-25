# Ask your AI

Use an agent that can run commands, search the web, and open GitHub PRs: Claude
Code or Codex in a terminal, or ChatGPT Work with GitHub connected. See
[Agent integrations](../integrations/README.md) for tool-specific steps.

## 1. Fork the repository

Fork this repository on GitHub with **Copy the main branch only** checked.

## 2. Connect an agent

- **Terminal:** sign in with `gh` (fork owner account), clone your fork, and
  open it in Claude Code or Codex.
- **ChatGPT Work:** connect GitHub with access to push branches and open PRs on
  your fork. Enable workflows in **Actions** if disabled, and set
  **Settings → Pages → Source** to **GitHub Actions**.

## 3. Ask for an article

> Help me set up my Nightly Build paper in `<owner>/<repo>` and write my first
> article about `<topic>`. Follow the repository's instructions.

If unconfigured, the agent runs `./nb setup` and opens the Article PR. A clean
PR auto-merges and publishes after `validate` passes. Add "let me read it first"
to hold it as a draft PR for review.

Next: [Set up your paper](./setup.md) or
[Schedule publication](../guides/operate/schedule.md).
