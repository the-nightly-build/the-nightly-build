# Capability audit

Setup crosses three execution surfaces. Audit each from direct evidence and
record `not tested`, `passed`, or `failed`; never promote an inference to a
pass.

| Surface              | Required evidence                                                                 |
| -------------------- | --------------------------------------------------------------------------------- |
| Current assistant    | Can inspect the intended repo and perform each setup mutation it claims to own    |
| Scheduled production | Can fetch both branches, run `nb`, browse real sources, push, and request a PR    |
| GitHub CI and Pages  | PR triggers trusted proof, browser render succeeds, merge publishes the candidate |

The same product name does not collapse surfaces. A desktop session and that
provider's hosted schedule can have different repositories, identities,
network policy, tools, billing, and approval modes.

## Audit the current assistant

Identify the GitHub account and target repository without exposing
credentials. Confirm whether this session can:

- create or inspect the canonical fork;
- clone and edit the fork;
- run `git`, authenticated GitHub operations, `uv`, and the checkout-owned
  `nb` command;
- push a `main` configuration branch or commit when authorized;
- inspect provider schedule configuration.

Use reversible, task-relevant checks. Do not ask the user to perform a command
merely because it is familiar. If the current assistant lacks a capability,
give one manual action through the provider's normal secure UI, state the
expected result, and wait.

## Audit the scheduled runtime

Inspect the actual scheduled environment's configuration. Confirm its checkout
ref, working directory, GitHub identity, secrets or subscription context,
outbound network policy, installed `uv`, non-interactive tool approvals, and
ability to push generated branches and open PRs against `library`.

Configuration is not proof. Run the test below. A local simulation, a run in
the setup chat, or a different provider environment cannot substitute.

## Run the immediate one-series test

Choose one approved series that can produce exactly one due article now. Keep
`autopublish: false`. If its intended cadence is `manual`, temporarily use an
ordinary due cadence for the test, then restore `manual` afterward; a
manual series is correctly invisible to `nb duty`.

Before triggering, run `nb duty` against the exact test configuration and
confirm it returns only that series. If other series are due, adjust their test
configuration rather than appending scope to the scheduler prompt. Use the
scheduler's on-demand trigger with its final unmodified prompt, repository,
permissions, and runtime.

The run must provide direct evidence that it:

1. checked out current `main` and current `library`;
2. completed `nb sync` and resolved the expected work through `nb duty`;
3. opened real web sources rather than relying on snippets or cached knowledge;
4. completed the recorded editorial roles;
5. pushed the generated article branch;
6. opened a real PR with base `library`;
7. received a publishable proof and successful browser render from CI; and
8. remained open for human review because autopublish was disabled.

Inspect the PR diff and CI result. The existence of a PR alone does not prove
research access or rendering. A green local proof alone does not prove GitHub
delivery. Do not merge merely to complete the audit; review the test article
as the first issue of the paper.

## Audit CI and publication

Confirm the test article used the `pull_request` validation workflow from the
base branch, the proof loaded engine and press state from `main`, and the
render probe targeted the candidate article. After the user approves and
merges the test article, confirm the Pages URL serves it and the catalog/feed
update. CI and Pages remain distinct checks even when GitHub hosts both.

## Handle failure without restarting

Record a failed requirement in this form:

```text
Surface: scheduled production
Requirement: push generated branch
Observed: authentication succeeded; push returned permission denied
Evidence: provider run URL or exact non-secret error
Owner: repository-app permission
Next action: enable Contents write for this repository
Resume at: rerun the one-series test from branch delivery
```

Give the user only the `Next action` when it requires them. After the external
state changes, repeat the narrowest reliable test, then resume the test run from
the named boundary when the runtime supports it. Preserve completed evidence;
do not repeat account creation, press interviews, or unrelated setup.

Setup status is `ready` only when every surface has passed and the exact
scheduled runtime produced the passing test Article PR. Otherwise report
`not ready`, the failed or untested requirement, and the single next action.
