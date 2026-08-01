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
5. `uv` on `PATH`.
6. Non-interactive permission to use every required tool.

Every run begins with `nb sync`, then asks `nb duty` for the deterministic work
list. One schedule can run the whole paper because series own their cadence.
`cadence: manual` series never appear as due.

Choose a provider-hosted scheduler when it meets all six requirements. The
portable alternative is a GitHub Actions cron around a headless agent. Current
provider entrypoints are listed in [Integrations](../../integrations/README.md).

## Canonical prompt

Keep the external schedule prompt deliberately small:

> Work in The Nightly Build repository `<repo>` on current `main`. Read
> `.agents/prompts/run-scheduled-publication.md` and follow it in this agent.
> This paragraph is the entire assignment. If that file is unavailable, stop
> and report the missing repository entrypoint.

The repository owns the workflow; the scheduler only owns location and
authority. The scheduled agent itself becomes the orchestrator; it never
launches an orchestrator subagent. Replace prompts that restate commands, role
sequences, validation rules, or branch mechanics because those copies drift.

## GitHub Actions boundary

A universal workflow runs on `main`, grants its job `contents: write` and
`pull-requests: write`, installs `uv`, checks out both branches, and invokes the
chosen headless agent with the canonical prompt. Keep model credentials in
repository secrets.

Do not put the trusted scheduler or its credentials in the `library` PR
workflow. Article validation intentionally runs on `pull_request` with no
scheduler secrets. See
[Publishing and security](../../concepts/publishing-and-security.md).

## Prove it before relying on it

Trigger an immediate canary in the exact scheduled environment with
`autopublish: false`. Setup is not complete until that runtime browses real
sources, creates a real Article PR, and passes both proof and render CI. Use
[First run](../../getting-started/first-run.md) as the acceptance test.
