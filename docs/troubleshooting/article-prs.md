# Troubleshoot Article PRs

Read the `BLOCK` code in the proof comment and reproduce it locally against the
branch with `./nb check`. Never edit `library` directly to work around a check
failure.

## `B-DIFF-SHAPE`

Each PR type must match a strict diff shape:

- **New article:** one HTML article, its matching assets under
  `library/SERIES/SLUG/`, and its complete `agent-artifacts/SERIES/SLUG/` tree.
- **Revision:** one existing HTML article and/or its matching assets, plus
  exactly one next revision note.

Put configuration and engine edits in a separate PR against `main`.

## `B-AGENT-ARTIFACTS`

The error names the missing or altered role file pair and invocation number. New
articles require the complete role record, and invocations already on `library`
are immutable.

## `B-REVISION-NOTE`

A revision must add one nonempty UTF-8 Markdown file at
`agent-artifacts/SERIES/SLUG/revisions/NN.md`, using the next two-digit number
(starting at `01`, independent of role invocation numbers). Never edit or delete
an existing note. No heading or prose template is required.

## Local proof passes, render probe fails

The render probe builds the site from the PR head using the engine on `main` and
checks it in a headless browser. Common causes: missing local assets, horizontal
overflow, theme contrast failures, or furniture that breaks at narrow widths.

## `NB_ARTICLE_PR_REQUIRED`

The generated branch is proved and ready, but the runtime has no working `gh`
CLI path. Open or update the PR through the runtime's GitHub integration using
the exact reported base, head, title, and body without recreating or editing the
commit.

## `NB_GIT_REQUIRED`

Git is missing or a fetch, push, or branch query failed (exit code `3`). The
output prints the checkout and arguments. Fix Git access, refresh local refs,
and rerun. After a failed push, rerun preparation because its temporary worktree
is removed. Do not assume a failed query means a branch is absent.
