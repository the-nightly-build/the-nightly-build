# Schedule publication

The setup assistant and the scheduled runtime may be different products. Audit
the scheduled environment independently: it is the one that must check out the
paper, browse sources, push a branch, and open a PR while nobody is present.

## Runtime requirements

The scheduled runtime needs:

1. A schedule or on-demand trigger.
2. Current `main` plus access to `origin/main` and `origin/library`.
3. Outbound web access for research.
4. Permission to push generated branches and open PRs against `library`.
5. `uv` on `PATH`, or permission to install it.
6. Non-interactive permission to use every required tool.

Every run begins with `nb sync`, then asks `nb duty` for the deterministic work
list. One schedule can run the whole paper because series own their cadence.
`cadence: manual` series never appear as due.

Choose a scheduler only after its actual unattended environment meets all six
requirements. Verified runtimes and remaining candidates are listed in
[Integrations](../../integrations/README.md).

A self-hosted GitHub Actions cron path is planned but not yet verified: a PR
opened with the workflow's own `GITHUB_TOKEN` cannot trigger the required
`validate` check, so that recipe needs a separately scoped token and an
end-to-end test before this documentation can recommend it. Progress is tracked
in
[issue #148](https://github.com/the-nightly-build/the-nightly-build/issues/148).

## Canonical prompt

Keep the external schedule prompt deliberately small:

> Work in The Nightly Build repository `<repo>`. Update the checkout to the
> current remote `main` before reading anything; a stale clone may predate the
> entrypoint. Read `.agents/prompts/run-scheduled-publication.md` and follow it
> in this agent. This paragraph is the entire assignment. If that file is
> missing from up-to-date remote `main`, stop and report the missing repository
> entrypoint.

The repository owns the workflow. The scheduler owns only location and
authority. The scheduled agent loads the orchestrator skill in the same context.
It does not launch an orchestrator subagent. Replace prompts that restate
commands, role sequences, validation rules, or branch mechanics because those
copies drift.

## Verification prompt

To test the exact scheduled environment without publishing, trigger an on-demand
task with this assignment:

> Work in The Nightly Build repository `<repo>`. Update the checkout to the
> current remote `main` before reading anything; a stale clone may predate the
> entrypoint. Read `.agents/prompts/verify-scheduled-runtime.md` and follow it
> in this agent. This paragraph is the entire assignment. If that file is
> missing from up-to-date remote `main`, stop and report the missing repository
> entrypoint.

The smoke prompt opens and cleans up a draft PR against `main`. It never loads
the orchestrator or touches `library`.

Keep scheduler credentials out of the `library` PR workflow. Article validation
intentionally runs on `pull_request` with no scheduler secrets. See
[Publishing and security](../../concepts/publishing-and-security.md).

## Prove it before relying on it

Use [Verify the scheduled runtime](../../getting-started/first-run.md) for the
complete smoke-test boundary and result interpretation.
