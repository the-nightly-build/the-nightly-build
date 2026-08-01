# Troubleshoot setup and scheduling

## Setup cannot create or configure the fork

Confirm the current assistant is connected to the intended GitHub account and
repository. If it lacks authority, complete the one requested GitHub action or
use the manual path in [Set up](../getting-started/setup.md). Do not paste a
token into chat.

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
against `library`. On GitHub Actions, the job needs `contents: write` and
`pull-requests: write`. Provider-hosted schedulers may need separate repository
app permissions.

## The first run worked locally but fails on schedule

The local run proved the wrong boundary. Trigger the test article in the exact
scheduled environment with `autopublish: false`; fix its first failed
requirement and resume there.
