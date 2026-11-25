# Verify the scheduled runtime

Interactive assistants and hosted schedulers often differ in credentials, tools,
network rules, and approvals. Run this optional smoke test in your scheduled
environment to verify permissions without publishing an article.

## 1. Run the smoke-test task

Create a one-off task in the same automation environment, repository identity,
network settings, and approval mode as your publication schedule. Give it this
exact prompt:

> Work in The Nightly Build repository `<repo>`. Update the checkout to the
> current remote `main` before reading anything. A stale clone may predate the
> entrypoint. Read `.agents/prompts/verify-scheduled-runtime.md` and follow it
> in this agent. This paragraph is the entire assignment. If that file is
> missing from up-to-date remote `main`, stop and report the missing repository
> entrypoint.

## 2. What it checks

The agent verifies or installs `uv`, fetches `main` and `library`, runs `./nb`,
searches the web and fetches live pages, pushes a temporary branch, opens a
draft PR against `main`, confirms PR checks register, and then closes the PR and
deletes the branch.

It never loads the publication orchestrator, runs `nb duty`, writes an article,
targets `library`, merges a PR, or deploys Pages.

## 3. Read the result

Evaluate each capability independently (`passed`, `failed`, or `not verified`).
Fix any failure at its named boundary and rerun only that step. A local run
never proves a hosted scheduler, and the test is incomplete until the diagnostic
PR is closed and its branch is deleted.

Article proof, auto-merge, and Pages deployment are tested by your first real
article.
