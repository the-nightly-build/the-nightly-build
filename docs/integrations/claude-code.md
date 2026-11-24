# Use Claude Code

Use Claude Code in a local clone for interactive setup and articles, and
[Claude Code Routines](https://code.claude.com/docs/en/routines) for unattended
scheduled runs.

## Publish an article now

**Prerequisites:** Claude Code, `git`, `gh` (authenticated as the fork owner),
`uv`, and Python 3.10+.

Fork this repository, clone your fork, open it in Claude Code, and ask:

> Help me set up my Nightly Build paper and publish my first article about
> `<topic>`. Follow the repository's instructions. Let me review the article
> before it publishes.

Claude Code runs `./nb setup` if needed and opens an Article PR. Omit the last
sentence to auto-merge after checks pass instead of opening a draft PR.

## Schedule publication

Create a cloud Routine with access to your fork, web search, GitHub, and
required tools. Set the schedule and use this prompt:

> Work in The Nightly Build repository `<owner>/<repo>`. Update the checkout to
> the current remote `main` before reading anything. Read
> `.agents/prompts/run-scheduled-publication.md` and follow it in this agent.
> This paragraph is the entire assignment. If that file is missing from
> up-to-date remote `main`, stop and report the missing repository entrypoint.

Choose automatic publication or draft-only PRs. See
[Claude Code's Routines guide](https://code.claude.com/docs/en/routines) for
current setup steps and limits.

## After publication

Your paper publishes to `https://<owner>.github.io/<repo>/`. If `validate` never
starts on an Article PR, enable Actions in the fork's **Actions** tab, then
close and reopen the PR. See
[Troubleshoot setup and scheduling](../troubleshooting/setup-and-scheduling.md).
