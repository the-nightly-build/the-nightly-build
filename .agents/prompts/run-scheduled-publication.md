# Run scheduled publication

Complete every article returned by `nb duty`. The run is not successful until
each one is published.

## Resolve scheduled work

Work from the configured paper's current `main` checkout and ensure you are up
to date with the remote. Use that checkout's `nb` executable for every system
operation, and do not invoke files under `engine/` directly. If the checkout is
stale or `uv` is unavailable, update the checkout or install `uv` from its
official source, then continue.

Run `nb sync`. When it exits 3 with `NB_SYNC_PR_REQUIRED`, carry the printed
request to the runtime's connected GitHub tool, wait for validation and merge,
then rerun `nb sync`. A configuration migration error is the paper owner's
decision: report it with the printed message and do not edit the press to clear
it. Diagnose and repair any other recoverable failure. For an external
permission or service failure, report the evidence, exact manual action, and
command to resume. Never report an unpublished run as successful.

Refresh a separate checkout of `library`, then run:

```text
nb duty --library <library-checkout>
```

When it exits 2, it has rejected the library checkout and printed the reason on
stderr. Repair exactly that and rerun the command. A missing press is an error.
`examples/` is documentation, never live configuration. If no work is due,
finish without opening a PR.

## Load the orchestrator skill

When work is due, the current agent is the orchestrator. Load the
[orchestrator skill](../skills/nb-orchestrator/SKILL.md) into this agent and
follow it. Do not launch another orchestrator. Supply the exact `nb duty` result
as the authorized work. Do not add another series or article, and process at
most one article per returned series.
