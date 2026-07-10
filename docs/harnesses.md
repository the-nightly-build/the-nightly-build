# Harnesses: which agents can run the night shift, and what they cost

The scheduling model lives in [scheduling.md](scheduling.md) and names no
provider: the night shift is any agent that can check out your repo, browse the
web, and open a pull request on a nightly cron. This page is the provider-specific
companion, the agents verified to do it, how to invoke each one headless, and
whether a run is included in a subscription or metered on top.

Provider capabilities move fast. The universal GitHub Actions path in
scheduling.md always works regardless of anything on this page.

## Coverage and cost

Which agents can run the night shift laptop-off, how you invoke them headless, and
whether tonight's run is already paid for or metered on top. Verified 2026-07.

| Agent           | Native laptop-off scheduler                           | Headless entrypoint               | Cost of the automated run                                     |
| --------------- | ----------------------------------------------------- | --------------------------------- | ------------------------------------------------------------- |
| **Claude Code** | Yes: Routines                                         | `anthropics/claude-code-action`   | Routine: included in Pro/Max usage. Actions path: metered key |
| **Jules**       | Yes: Scheduled Tasks                                  | `google-labs-code/jules-action`   | Included in your Jules plan (daily task quota)                |
| **Codex**       | No (Automations need machine on)                      | `openai/codex-action`             | Metered `OPENAI_API_KEY`                                      |
| **Cursor**      | Not verified                                          | `cursor-agent -p`                 | Draws on your Cursor plan credits                             |
| **opencode**    | Via its own Action on cron                            | `opencode run`                    | Metered: your own model key (BYOK)                            |
| **Devin**       | Yes: Schedules                                        | `devin -p` / REST                 | Included in your Devin plan                                   |
| **Copilot**     | Yes: Automations                                      | server-side / Copilot CLI         | Included in your Copilot plan                                 |
| **Antigravity** | Not verified (native schedule runs via the local app) | IDE/CLI                           | Depends on the entrypoint you script                          |
| **pi**          | No                                                    | CLI (no documented headless flag) | Metered: your own model key (BYOK)                            |

Invoke one-liners for the marked step in `nightly.yml` (each needs its key as a
repo secret and web access enabled): `openai/codex-action` with `OPENAI_API_KEY`;
`cursor-agent -p "<prompt>"` with `CURSOR_API_KEY`; `opencode run "<prompt>"`
with your model key; `anthropics/claude-code-action` with `ANTHROPIC_API_KEY`
(though a native Routine is cheaper, below). Each action's own README is the
current source for inputs.

## Native shortcuts

Skip the cron entirely when your provider hosts the scheduler. Paste the same
schedule prompt (in [scheduling.md](scheduling.md)) into these.

### Claude Code (Routines)

Create one Routine for the whole paper: type `/schedule` in the CLI, or use
[claude.ai/code/routines](https://claude.ai/code/routines). Connect the fork
once (grant contents and pull-requests access), set a nightly cron, paste the
prompt, and pick the model. Also set the environment's **Network access** to
**Full** (or Custom with your series' sources): Routines sandbox outbound web by
default, so without it the night shift researches nothing and publishes nothing.
Routines run in Anthropic's cloud, so your laptop can be off, and they **draw on
your Pro/Max subscription like an interactive session**, so a nightly run costs
nothing extra within your plan limits. Use **Run now** for tonight's first
article instead of waiting.

### Jules (Scheduled Tasks)

Install the Jules GitHub app on your fork, then create a Scheduled Task with the
prompt and a nightly cadence. It runs server-side in Jules's cloud VM against the
connected repo. Runs **draw on your plan's daily task quota** rather than a
metered key, and the model tier is fixed by your plan. The equivalent CI path is
`google-labs-code/jules-action` on `on: schedule` with a `JULES_API_KEY` secret.

### Codex (the universal path, worked)

Codex's in-product Automations need your machine powered on, so the laptop-off
path is the GitHub Actions workflow in scheduling.md with `openai/codex-action`
in the marked step. It runs `codex exec` with a **metered `OPENAI_API_KEY`** (a
repo secret), billed per token on top of any ChatGPT plan. Enable agent internet
access on the environment, since it is **off by default**, or research fails.
(The interactive cloud tasks at chatgpt.com/codex are a separate, plan-gated
surface; the Action is what runs unattended.)

## Choosing, for the setup agent

Ask the user what they already pay for, then match it. State plainly which case
applies and whether tonight's run is subscription-included or metered.

- **Claude Pro/Max** → a Routine. Included in the plan, zero infra, laptop-off.
- **Jules Pro/Ultra** → a Scheduled Task. Included in the task quota, zero infra.
- **Devin or Copilot** → their native schedule.
- **An OpenAI or Anthropic API key, or any agent with a headless command** → the
  universal Actions path. Say when it bills a metered key (Codex and the Claude
  Actions path both do; the native Routine does not).
- **No verified laptop-off native scheduler** (Codex, Cursor, Antigravity, pi) →
  the universal Actions path with that agent's headless entrypoint.

If you (the setup agent) can create the schedule and fire the first run yourself,
do it and confirm the run started. If you cannot, hand the user the filled prompt
and the exact place to paste it, and say that pasting it is the one manual step.
