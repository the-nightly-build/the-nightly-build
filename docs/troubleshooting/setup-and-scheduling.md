# Troubleshoot setup and scheduling

## Setup cannot create or configure the fork

Confirm the current assistant is connected to the intended GitHub account and
repository. If it lacks authority, complete the one requested GitHub action or
use the manual path in [Set up](../getting-started/setup.md). Do not paste a
token into chat.

## Article PR checks never register

If an Article PR sits with no `validate` check and never merges, the fork's
workflows are probably disabled: forks start that way, and GitHub runs no
Actions until they are enabled. Enable workflows from the fork's Actions tab (or
re-run `nb setup`, which enables them when it can), then close and reopen the
stalled PR so the check triggers.

## The schedule starts but produces no work

Run `nb duty` in the scheduled checkout and read its idle reasons. Confirm the
runtime has current `main`, a sibling `library` checkout, and a non-manual,
non-paused series due on the current UTC day. `cadence: manual` is supposed to
remain idle.

## Research cannot reach sources

Test outbound access inside the scheduled environment. Changing access in the
setup chat or local machine does not change the schedule. Enable the provider's
network capability for that runtime, then rerun the failed test step.

## The run cannot push or open a PR

Verify the scheduled identity can push a generated branch and create a PR
against `library`. Provider-hosted schedulers may need separate repository app
permissions. A runtime authenticated with a GitHub Actions `GITHUB_TOKEN` also
cannot trigger the `validate` check on PRs it opens. Scheduled runtimes need an
identity whose PRs run checks.

## Verification works locally but fails on schedule

The local run proved the wrong boundary. Trigger the non-publishing smoke check
in the exact scheduled environment, then fix its first failed requirement and
resume there.
