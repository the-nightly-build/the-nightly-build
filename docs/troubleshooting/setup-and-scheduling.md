# Troubleshoot setup and scheduling

## Setup cannot create or configure the fork

Verify the assistant is connected to the fork's owner GitHub account and
repository. Without `gh`, `./nb setup` cannot read or change Pages or Actions
settings and lists both under "Still to do" with direct links, even if already
enabled. Apply any missing settings in GitHub directly. Never paste a GitHub
token into chat.

## First article check reports an unknown series

Validation reads `press/` from remote `main`. If `press/` exists locally but was
never pushed, push that commit to `main`, then close and reopen the PR to re-run
the check.

## Article PR checks never start

Forks start with GitHub Actions disabled. Enable workflows in the fork's
**Actions** tab (or rerun `./nb setup` with `gh`), then close and reopen the
stalled PR to trigger `validate`.

## Schedule runs but produces no work

Run `./nb duty` in the scheduled checkout and inspect its idle reasons. A series
produces no due work when it is paused, does not run on the current UTC weekday,
already has an article dated today (UTC), or uses `cadence: manual`.

## Research cannot reach sources

Test outbound web access inside the scheduled runtime itself. Network access in
your local terminal or interactive chat does not apply to a hosted scheduler.
Enable outbound network access in the provider's scheduled-task settings and
retest.

## Run cannot push or open a PR

Confirm the scheduled identity has permission to push branches and open PRs
against `library`, GitHub Actions are enabled on the fork, and its PRs trigger
`validate`. Hosted schedulers may require separate GitHub app repository
permissions.

## Local checks pass, scheduled task fails

Local and hosted environments often differ in credentials, tools, and network
rules. Inspect the scheduled task's run log, then run the
[scheduled runtime smoke test](../guides/operate/verify-scheduled-runtime.md) in
that exact environment.
