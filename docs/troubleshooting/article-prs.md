# Troubleshoot Article PRs

The `BLOCK` code and message in the proof comment name the failure. The
checkout-owned `nb check` reproduces it against the exact proposed branch.
Editing `library` directly to make an error disappear is never the fix.

## `B-DIFF-SHAPE`

A normal Article PR may add one HTML article plus matching assets and its full
artifact tree. A revision may modify one existing HTML article and/or its
matching assets, and must add exactly one matching revision note. Configuration
and engine changes belong in a separate PR against `main`.

## `B-AGENT-ARTIFACTS`

The message names the expected role file pair and invocation number. A new
article requires the complete production record, and an invocation already on
`library` never changes.

## `B-REVISION-NOTE`

A revision adds one nonempty UTF-8 Markdown file at
`agent-artifacts/SERIES/SLUG/revisions/NN.md`, where `NN` is the next two-digit
number, starting at `01` when no earlier note exists. A published note never
changes and is never deleted.

Revision notes do not share numbering with role invocations and do not require a
role or prose template.

## The local proof passes but the render probe fails

The probe builds from the PR head with the current engine and inspects the
browser result. Typical causes are missing local assets, overflow, theme
contrast, or furniture that only works at one width. The file-level proof cannot
substitute for rendering.

## Delivery reports `NB_ARTICLE_PR_REQUIRED`

The generated branch is complete and proved, but the environment lacks a working
GitHub CLI path. The PR is opened or updated through whatever GitHub access the
runtime does have, with exactly the reported base, head, title, and body. The
generated commit is final and is never recreated or edited.
