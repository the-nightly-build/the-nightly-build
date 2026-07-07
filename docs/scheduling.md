# Scheduling the night shift

The night shift is just an agent that runs on a clock. Any agent that can check
out your repo, browse the web, and open a pull request can be it. This page is
how you put one on a nightly schedule.

Two choices are involved, and they are independent:

1. **The setup agent** is whatever you are talking to right now (Claude Code,
   Cursor, opencode, Codex, anything). It configures `press/` and wires up the
   schedule. It does not have to be the same product that runs the night shift.
2. **The night-shift runtime and its scheduler** is what actually fires nightly.
   You can do setup in one agent and schedule the night shift on another.

The scheduler comes in two shapes. Some providers host their own (Claude
Routines, Jules Scheduled Tasks); when yours does, that is the shortcut, and for
some it is included in a plan you already pay for. When it does not, the
universal path below runs the same night shift on a GitHub Actions cron. That
path always works.

## What the night shift needs

Four requirements. Everything past them lives in `PROTOCOL.md`.

1. A scheduler that fires on a nightly cron.
2. A checkout of `main` (the engine and `press/`) with the `library` branch
   available separately.
3. Web access for research.
4. Permission to open a pull request to `library`.

## The universal path: GitHub Actions

This runs the night shift on GitHub's runners with your machine off, using any
agent that has a headless command. No vendor scheduler required. Copy this into
your fork as `.github/workflows/nightly.yml` and fill in the one marked step:

```yaml
name: nightly-build
on:
  schedule:
    - cron: "0 6 * * *" # 06:00 UTC nightly; pick your hour
  workflow_dispatch: {} # run tonight's first edition on demand
permissions:
  contents: write # push the work branch
  pull-requests: write # open the PR to library
jobs:
  night-shift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4 # main: engine + press/
      - uses: actions/checkout@v4 # library, checked out separately
        with:
          ref: library
          path: library-checkout
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pyyaml
      # Invoke your agent here with the prompt below. It needs web access, your
      # agent's API key as a repo secret, and the two permissions declared above.
      # Per-agent one-liners are under the coverage table.
```

The trigger lives on `main` (or in a separate repo). Never put it on the
`library` PR path: the editor validates untrusted edition PRs with read-only
permissions and no secrets, and that boundary is the security model. A scheduled
workflow on `main` holding your API key is the trusted side of the same line the
morning mailer already sits on.

### The schedule prompt

This is the whole assignment. Paste it verbatim wherever your scheduler takes a
prompt (a Routine, a Scheduled Task, or the invoke step above), with `<repo>`
and `<checkout>` filled in. Do not trim it.

> You are the night shift for The Nightly Build repo `<repo>`. Read
> `PROTOCOL.md` on main and follow it exactly. Runtime: needs Python 3.9+ and
> PyYAML; if a script reports it missing, `pip install pyyaml` (or use
> `uv run`). Work from the `main` checkout (it carries the engine and `press/`)
> with the `library` branch checked out separately at `<checkout>`, then run
> `python3 engine/duty.py --repo . --library <checkout>` for tonight's due
> series. For each: research deeply with cited primary sources; render ONE
> self-contained HTML file from the series' template (whichever it declares),
> using components from `templates/FURNITURE.md`; run
> `python3 engine/check.py library/<series>/<slug>.html --series <id> --repo .
--library <checkout>` and revise until `BLOCK: 0`; then write the PR body to a
> file and re-run check with `--pr-body <file>` so it passes too. Open ONE PR
> per series targeting `library`, adding ONLY `library/<series>/<slug>.html`,
> title `nb: <series>/<slug> - <Title>`, body containing the nb-meta yaml block.
> Nothing due: exit without a PR. Never merge, push to `library`, or modify
> other files.

One schedule runs the whole press. Each night the run derives its work list from
the repo, so adding, retiring, or completing a series never touches the
schedule. To run series on different models or in parallel, add a second
schedule and append one line: `Work ONLY series <series-id>.`

## Coverage and cost

Which agents can run the night shift laptop-off, how you invoke them headless,
and whether tonight's run is already paid for or metered on top. Verified
2026-07; provider capabilities move fast, and the universal path always works.

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
schedule prompt into these.

### Claude Code (Routines)

Create one Routine for the whole press: type `/schedule` in the CLI, or use
[claude.ai/code/routines](https://claude.ai/code/routines). Connect the fork
once (grant contents and pull-requests access), set a nightly cron, paste the
prompt, and pick the model. Routines run in Anthropic's cloud, so your laptop
can be off, and they **draw on your Pro/Max subscription like an interactive
session**, so a nightly run costs nothing extra within your plan limits. Use
**Run now** for tonight's first edition instead of waiting.

### Jules (Scheduled Tasks)

Install the Jules GitHub app on your fork, then create a Scheduled Task with the
prompt and a nightly cadence. It runs server-side in Jules's cloud VM against the
connected repo. Runs **draw on your plan's daily task quota** rather than a
metered key, and the model tier is fixed by your plan. The equivalent CI path is
`google-labs-code/jules-action` on `on: schedule` with a `JULES_API_KEY` secret.

### Codex (the universal path, worked)

Codex's in-product Automations need your machine powered on, so the laptop-off
path is the GitHub Actions workflow above with `openai/codex-action` in the
marked step. It runs `codex exec` with a **metered `OPENAI_API_KEY`** (a repo
secret), billed per token on top of any ChatGPT plan. Enable agent internet
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
