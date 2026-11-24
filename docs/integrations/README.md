# Choose an agent

The Nightly Build works with any coding agent that can follow repository
instructions, run commands, browse the web, and use GitHub.

## On-demand articles

| Agent                             | Where it runs                | Best for                                  |
| --------------------------------- | ---------------------------- | ----------------------------------------- |
| [Claude Code](./claude-code.md)   | Local clone in terminal      | Interactive setup, articles, and Routines |
| [Codex](./codex.md)               | Local clone with Codex CLI   | Interactive setup and articles            |
| [ChatGPT Work](./chatgpt-work.md) | Cloud session via GitHub app | No local terminal, cloud tasks            |

Each path runs `./nb setup` and opens validated Article PRs. See
[Set up your paper](../getting-started/setup.md) for the general flow.

## Scheduled publication

- **[ChatGPT Work scheduled task](./chatgpt-work.md#schedule-publication):**
  recurring cloud task with GitHub access and a fresh checkout.
- **[Claude Code Routine](https://code.claude.com/docs/en/routines):** scheduled
  cloud routine connected to your fork and required tools.

Point your scheduler at
[`run-scheduled-publication.md`](../../.agents/prompts/run-scheduled-publication.md)
rather than copying workflow steps. See
[Schedule publication](../guides/operate/schedule.md) for the canonical prompt.
