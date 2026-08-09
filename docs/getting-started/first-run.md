# Verify the scheduled runtime

The conversational assistant and scheduled agent may run with different
repositories, identities, tools, network rules, and approvals. An optional smoke
test can verify the actual scheduled environment without publishing an article.

## Trigger the smoke test

Create a one-off or on-demand task in the same automation environment used by
the publication schedule. Give it this assignment:

> Work in The Nightly Build repository `<repo>`. Update the checkout to the
> current remote `main` before reading anything; a stale clone may predate the
> entrypoint. Read `.agents/prompts/verify-scheduled-runtime.md` and follow it
> in this agent. This paragraph is the entire assignment. If that file is
> missing from up-to-date remote `main`, stop and report the missing repository
> entrypoint.

Keep the repository identity, credentials, network access, and approval mode
identical to normal scheduled publication. A local run or a different cloud
environment proves only itself.

## What it verifies

The scheduled agent will install or verify `uv`, fetch both repository branches,
run the checkout-owned command, search the web, open real source pages, push a
temporary branch, and open a draft PR against `main`. It confirms that ordinary
PR checks register, then closes the PR and deletes the branch.

The smoke test never loads the publication orchestrator, resolves due work,
creates an article, targets `library`, merges a PR, or deploys Pages.

## Read the result

Treat each capability independently as passed, failed, or not verified. Fix a
failure at its named boundary and rerun only the relevant smoke step. Local
success is not evidence about a hosted scheduler, and the test is not finished
while its diagnostic PR or branch remains open.

Article proof, automatic merge, and Pages deployment are exercised by the first
real article as ordinary product behavior. They are intentionally not part of
setup verification.
