# Set up a paper

Use `docs/getting-started/setup.md`, `docs/guides/operate/schedule.md`, and the
[capability audit](../references/capability-audit.md) as the current setup
contract. Inspect the repository before creating or replacing anything.

## Establish the boundaries

Distinguish the conversational assistant, scheduled runtime, and GitHub. The
same provider may use different identities, tools, network rules, and approval
modes in chat and on schedule. Verify only what the active environment can
demonstrate.

Preserve a valid fork, checkout, press, branch, or schedule. Resume from the
first incomplete requirement instead of restarting setup.

Offer the `main` protection choice once, plainly: unprotected keeps the owner's
quick direct edits; protected routes every change through a reviewed PR and
keeps the scheduled identity out of trusted configuration entirely. The tradeoff
lives in `docs/concepts/publishing-and-security.md`. Either answer is valid.
Record which the user chose.

## Minimize handoffs

Perform every safe action already authorized. Ask the user only for a sign-in,
provider authorization, billing-bearing choice, or setting that automation
cannot change. Give one manual action at a time, state its expected result, and
verify it before continuing. Never ask for a pasted token.

Run `nb setup` to create or repair the publishing boundary. It is idempotent and
safe to re-run over a healthy setup. Hand editorial definition to
[create paper](create-paper.md), then configure the scheduled runtime with the
repository's publication prompt.

## Offer scheduled verification

Offer a one-off smoke run in the exact scheduled environment. Use the capability
audit and `.agents/prompts/verify-scheduled-runtime.md`. Do not turn the smoke
into an article, cadence change, or production run. Present its evidence and
repair the narrow failed boundary when the user wants help.

The user may proceed with unverified capabilities. State them plainly rather
than manufacturing confidence or withholding unrelated setup work.
