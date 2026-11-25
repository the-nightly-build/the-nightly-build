# Schedule publication

Set up a recurring task to publish articles automatically on each series's
cadence.

## 1. Choose a scheduler

Supported schedulers:

- **[ChatGPT Work scheduled tasks](../../integrations/chatgpt-work.md#schedule-publication):**
  connect GitHub with access to your fork, pick a daily time and timezone, and
  choose automatic merge or draft-only PRs.
- **[Claude Code Routines](https://code.claude.com/docs/en/routines):** create a
  cloud routine connected to your fork with web access and required tools, then
  use the prompt below.

Any scheduler must be able to update `main`, fetch `library`, browse the web,
run `uv` and repository commands non-interactively, push branches, and open PRs
against `library`.

## 2. Use the repository entrypoint prompt

Keep the scheduler prompt short and point to the repository-owned workflow
instead of copying steps into the scheduler:

> Work in The Nightly Build repository `<owner>/<repo>`. Update the checkout to
> the current remote `main` before reading anything. Read
> `.agents/prompts/run-scheduled-publication.md` and follow it in this agent.
> This paragraph is the entire assignment. If that file is missing from
> up-to-date remote `main`, stop and report the missing repository entrypoint.

Choose **automatic publication** (clean Article PRs merge after checks pass) or
**draft-only** (every Article PR waits for your review).

Each scheduled run begins with `nb sync` and `nb duty`. One schedule serves the
entire paper because every series declares its own cadence. Series with
`cadence: manual` never run on a schedule.

## 3. Monitor and troubleshoot

If a run stops, inspect the task log and the Article PR's `validate` check. See
[Troubleshoot setup and scheduling](../../troubleshooting/setup-and-scheduling.md)
or run the optional
[scheduled runtime smoke test](./verify-scheduled-runtime.md) to diagnose a new
provider environment without publishing.

Never put scheduler secrets into the `library` PR workflow. Validation runs on
`pull_request` with no secrets. See
[Publishing and security](../../concepts/publishing-and-security.md).
