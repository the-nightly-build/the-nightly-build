# Publishing and security

Every publication crosses a pull request to `library`. That PR is both the audit
record and the security boundary.

## Threat model

The scheduled runtime browses untrusted web pages, runs models, pushes work
branches, and opens PRs. Grant it the narrowest repository and network
permissions needed for those tasks. Because web content can prompt-inject an
agent, prompt instructions alone cannot enforce safety.

## Validation boundary

The validation workflow triggers on `pull_request` (never `pull_request_target`)
and evaluates untrusted article bytes with read-only contents and no scheduler
secrets. The proof enforces:

- narrow diff shape for the PR type
- valid article metadata and source contracts
- no active content (scripts, handlers, frames, forms)
- intact artifact history
- passing headless browser render check

## Merge policy

- **Auto-merges:** valid new-article PRs and exact workflow-sync PRs copied from
  `main`.
- **Human review required:** revisions and owner retractions never auto-merge. A
  revision may change one article's HTML and matching assets, adds one numbered
  Markdown note, and cannot alter prior notes or role history.

## Branch protection on `main`

`main` starts unprotected so you can edit `press/` and push directly without
self-approving PRs. The trade-off is that a prompt-injected scheduled identity
with push access to `main` could modify engine or press files. Protect `main`
once you prefer every change, including yours, to pass a reviewed PR. Always
review `press/site.yaml` edits closely, since owner-declared SRI-pinned external
assets execute for readers.
