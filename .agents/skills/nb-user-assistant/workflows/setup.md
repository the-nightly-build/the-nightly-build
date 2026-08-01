# Set up a paper

Read `docs/getting-started/ask-your-ai.md`, `docs/getting-started/setup.md`,
`docs/getting-started/first-run.md`, and the chosen page under
`docs/integrations/`. Read and apply
[the capability audit](../references/capability-audit.md) before declaring any
environment ready.

## Establish the actual boundary

Audit separately:

1. what this conversational assistant can do now;
2. where scheduled production will execute and what that runtime can do; and
3. what GitHub CI and Pages will do after a PR opens.

Do not infer one from another. Record direct evidence for each requirement. A
chat that can browse says nothing about a
hosted schedule, and a local authenticated `gh` says nothing about the
schedule's repository app.

Inspect existing repository state before creating anything. Preserve a valid
fork, press, branch, or schedule; resume the first incomplete requirement.

## Minimize handoffs

Aim for the user to do only the actions a permission boundary makes impossible:
sign in, authorize a provider, choose a billing-bearing runtime, or enable a
setting unavailable to automation. Ask for one action, wait for its result,
then verify it. Never ask the user to paste a token or perform a Git operation
you can perform safely.

Run `nb setup` only when setup is actually needed. Use the current docs for its
prerequisites and effects. Once the fork and publishing boundary exist, hand
off to [create paper](create-paper.md) for editorial definition and return here
for schedule verification.

## Acceptance

Setup is not complete after a local validation or a successful provider form.
Run the audit's immediate one-series test in the exact scheduled environment
with `autopublish: false`. It must use the web, push its generated branch, open
a real Article PR, and pass proof plus browser rendering. Keep the PR for human
review. Report `ready` only after every audit surface passes; otherwise name
the failed boundary, its evidence, and the single next action.
