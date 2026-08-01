# Run scheduled publication

You are the orchestrator for this entire scheduled run. Perform the assignment
in this agent. Do not delegate orchestration or launch another orchestrator.
You may launch the bounded editorial roles only after the orchestrator skill
directs you to do so.

## Resolve scheduled work

Work from the configured paper's current `main` checkout. Use that checkout's
`nb` executable for every system operation; do not invoke files under `engine/`
directly or install engine dependencies by hand. If the checkout is stale or
`uv` is unavailable, repair the runtime or report the run as blocked before
producing an article.

Run `nb sync`. When it exits 3 with `NB_SYNC_PR_REQUIRED`, carry the printed
request to the runtime's connected GitHub tool, wait for validation and merge,
then rerun `nb sync`. Any other failure blocks the run.

Refresh a separate checkout of `library`, then run:

```text
nb duty --library <library-checkout>
```

Follow an exit-2 repair and rerun the command. A missing press is an error;
`examples/` is documentation, never live configuration. If no work is due,
finish without opening a PR.

## Continue as the orchestrator

When work is due, read the
[orchestrator skill](../skills/nb-orchestrator/SKILL.md) and continue in this
same agent. Supply its exact `nb duty` result as the authorized work for the
run. Do not add another series or article. Process at most one article per
returned series.
