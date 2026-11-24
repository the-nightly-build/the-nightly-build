# Use Codex

Use Codex CLI in a local clone to set up your paper and publish articles through
the Article PR workflow.

## Publish an article now

**Prerequisites:** Codex CLI, `git`, `gh` (authenticated as the fork owner),
`uv`, and Python 3.10+.

Fork this repository, clone your fork, open it in Codex, and ask:

> Help me set up my Nightly Build paper and publish my first article about
> `<topic>`. Follow the repository's instructions. Let me review the article
> before it publishes.

Codex runs `./nb setup` if needed and opens an Article PR. Omit the last
sentence to auto-merge after checks pass instead of opening a draft PR.

For unattended daily editions, pair Codex with a
[ChatGPT Work scheduled task or Claude Code Routine](../guides/operate/schedule.md)
pointing at `.agents/prompts/run-scheduled-publication.md`.

## After publication

Your paper publishes to `https://<owner>.github.io/<repo>/`. If `validate` never
starts on an Article PR, enable Actions in the fork's **Actions** tab, then
close and reopen the PR. See
[Troubleshoot setup and scheduling](../troubleshooting/setup-and-scheduling.md).
