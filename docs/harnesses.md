# Harnesses

The night shift needs a repository checkout, web access, and permission to
open pull requests. [Scheduling](scheduling.md) defines that contract. This
page maps it to current agent products.

Provider features and prices move quickly. The links below are the source of
truth. A documented entrypoint means the integration is possible; it does not
mean this project has stress-tested that harness end to end.

## Current paths

| Agent                                                                                             | Laptop-off schedule                            | Unattended entrypoint           | Billing                                                        |
| ------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ------------------------------- | -------------------------------------------------------------- |
| [Claude Code](https://code.claude.com/docs/en/routines)                                           | Routines                                       | `anthropics/claude-code-action` | Routines use plan allowance; the Actions path uses API billing |
| [Jules](https://jules.google/docs/scheduled-tasks/)                                               | Scheduled Tasks                                | Hosted task                     | Daily task quota for the plan                                  |
| [Codex](https://learn.chatgpt.com/docs/automations)                                               | Cloud scheduled tasks                          | `openai/codex-action@v1`        | Cloud tasks use plan allowance; the Action uses API billing    |
| [Cursor](https://docs.cursor.com/en/cli/headless)                                                 | Cloud Agents and Automations, plan-dependent   | `cursor-agent -p --force`       | Included usage, then on-demand usage where enabled             |
| [OpenCode](https://dev.opencode.ai/docs/github/)                                                  | GitHub Action on cron                          | `opencode run`                  | The model provider you connect                                 |
| [Devin](https://docs.devin.ai/product-guides/scheduled-sessions)                                  | Automations                                    | API or CLI                      | Devin plan usage                                               |
| [GitHub Copilot](https://docs.github.com/en/copilot/how-tos/github-copilot-app/using-automations) | Automations                                    | Hosted coding agent             | Included premium requests, then usage-based billing if enabled |
| [Antigravity](https://codelabs.developers.google.com/getting-started-google-antigravity)          | Local schedules; laptop-off is not established | CLI                             | Plan-dependent                                                 |
| [Pi](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/README.md)               | No hosted scheduler                            | `pi -p`                         | The model provider you connect                                 |

## Hosted schedulers

Use a hosted scheduler when it can check out the fork, browse the web, and
open a PR. Paste the canonical prompt from [Scheduling](scheduling.md) and run
one task for the whole paper.

- **Claude Code:** create a Routine and enable full, or suitably scoped,
  network access. It runs in Anthropic's cloud and consumes your plan usage.
- **Jules:** install its GitHub app, create a Scheduled Task, and select the
  fork. Runs count against the plan's daily task quota.
- **Codex:** choose a cloud environment for the scheduled task. Local tasks
  need the computer; cloud tasks continue without it.
- **Cursor, Devin, and Copilot:** use their hosted automation surface when
  your plan includes it. Confirm repository permissions and usage limits in
  the provider before scheduling.

## GitHub Actions

The universal workflow in [Scheduling](scheduling.md) works with an agent that
has a non-interactive command or Action. Typical invoke steps are:

- Codex: `openai/codex-action@v1` with `OPENAI_API_KEY`.
- Claude Code: `anthropics/claude-code-action` with `ANTHROPIC_API_KEY`.
- Cursor: `cursor-agent -p --force "<prompt>"` with `CURSOR_API_KEY`.
- OpenCode: `opencode run "<prompt>"` with the chosen model credentials.
- Pi: `pi -p "<prompt>"` with the chosen model credentials.

Use each provider's current documentation for installation and Action inputs.
Give the runtime web access, keep credentials in repository secrets, and say
plainly whether the run consumes a subscription allowance or a metered API.
