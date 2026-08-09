# Verify the scheduled runtime

Run a non-publishing capability smoke test in this scheduled environment. Use
the repository and identity configured for the real schedule. Do not load the
production orchestrator, run `nb sync` or `nb duty`, generate an article, target
`library`, merge a pull request, or trigger Pages.

## Protect the repository and credentials

- Confirm the intended repository from its `origin` URL before changing
  anything.
- Preserve existing tracked and untracked work. Use an isolated worktree from
  `origin/main` when the checkout is not clean.
- Never print or commit a secret value in any form (e.g., tokens, cookies,
  authorization headers, environment dumps, etc.). Report only the authenticated
  account name and permission result when they are safe to expose.
- Name the run with its UTC timestamp plus a short random suffix. Use
  `nb/smoke/<run-id>` for the temporary branch and `.nb-smoke/<run-id>.md` for
  its report.

## Exercise the scheduled environment

1. Fetch `origin/main` and `origin/library`. Record both commit IDs. A missing
   branch or stale checkout is a failure, not permission to substitute another
   repository.
2. Check for `uv`. When it is absent, install it using Astral's current official
   installation instructions and verify the resulting version. If the runtime
   cannot install it, record the exact non-secret failure and required
   permission.
3. Run `./nb --help` from this checkout. If `press/` exists, also run
   `./nb validate --repo .`. Otherwise record press validation as not
   applicable.
4. Use the same search and browsing tools scheduled research will use. Search
   for a harmless current topic, then open two independent non-GitHub source
   pages. Do not treat snippets or cached knowledge as opened pages. Record each
   page's URL, title, and one short paraphrased fact.
5. From `origin/main`, create the temporary branch and commit the sanitized
   smoke report. Push it, then use the runtime's authenticated GitHub interface
   to open a draft pull request against `main`. Never open it against `library`.
6. Confirm that GitHub registers the ordinary `main` pull-request checks. A
   registered check may still be running. The purpose here is to prove the
   trigger and permissions, not to certify the engine through a smoke-only
   change.
7. Close the draft pull request without merging it, delete the remote branch,
   and remove any temporary local worktree or branch. Attempt cleanup after
   every partial failure as well as after success.

## Report evidence

Return exactly these rows, each marked `passed`, `failed`, or `not verified`
with concise non-secret evidence:

```text
repository identity:       passed | failed | not verified - <evidence>
fetch origin/main:         ...
fetch origin/library:      ...
uv available:              ...
checkout-owned nb:         ...
press validation:          ... (not applicable without press/)
web search:                ...
opened source page 1:      ...
opened source page 2:      ...
branch push:               ...
draft PR creation:         ...
CI registration:           ...
PR closed and branch deleted: ...
```

For every failure, give the single next action and the narrow step to rerun. Do
not claim the smoke passed while a temporary PR or branch remains. State
explicitly that article proof, automatic merge, and Pages publication were not
tested.
