# Revise a published article

A revision updates one published article without erasing its production record.
Whether fixing a typo or rewriting a section, the PR contract is the same.
Revisions always require human review and never auto-merge.

## 1. Branch from `origin/library`

Fetch `origin/library` and create a working branch or worktree from that exact
ref. Never commit or push directly to `library`.

Match your editorial process to the change:

- Fix spelling or markup directly when no editorial judgment is needed.
- Reopen sources whenever a claim, citation, number, or interpretation changes.
- Invoke roles (researcher, writer, editor, writing coach) when their judgment
  improves the change. Keep their scratch output local, outside the PR.
- Add, replace, or remove files under `library/SERIES/SLUG/` when visuals need
  fixing.

## 2. Add a revision note

Create one new Markdown file using the next two-digit sequence number (starting
at `01.md`, independent of role invocation numbers):

```text
agent-artifacts/SERIES/SLUG/revisions/NN.md
```

No fixed heading or schema is required. State why the revision was needed, what
materially changed, and how it was verified. Write for a reader auditing the
article's history, not about AI tool mechanics. Never edit or delete prior
revision notes or historical role artifacts.

## 3. Stamp, check, and open the PR

After editing article text, refresh counts and reading time while preserving the
original publication date:

```sh
nb stamp FILE --revision
```

Preflight the edited file locally (skipping already-published and paused-series
blocks):

```sh
nb check FILE --series ID --library DIR --revision
```

Commit the revision branch and run the full PR proof from a `main` checkout:

```sh
PATH-TO-MAIN/nb check --pr \
  --repo . \
  --main PATH-TO-MAIN \
  --base origin/library \
  --head HEAD \
  --library .
```

Preview the rendered page if markup, layout, furniture, or assets changed, then
push the branch and open a PR against `library`.

## PR contract

A revision PR must:

- modify `library/SERIES/SLUG.html`, matching files under
  `library/SERIES/SLUG/`, or both
- add exactly the next `agent-artifacts/SERIES/SLUG/revisions/NN.md`
- leave all other articles and historical artifacts untouched
- keep the article's `series` and `slug` metadata matching its file path
  (renaming or moving an article is not an in-place revision)

CI runs the full proof and browser render check. Revisions are permitted on
paused or already-published series and on retired configured items, provided the
series still exists and the revised article satisfies its template contract.
