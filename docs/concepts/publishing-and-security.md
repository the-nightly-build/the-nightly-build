# Publishing and security

Every publication crosses a pull request to `library`. That PR is both the
review record and the security boundary.

The scheduled runtime is trusted to browse arbitrary pages, invoke models, push
generated work branches, and request a merge. It should receive the narrowest
repository and network authority that still permits those jobs. Web content can
prompt-inject an agent, so prose instructions are not a sufficient containment
mechanism.

The validation workflow uses `pull_request`, never `pull_request_target`. It
checks untrusted article bytes with read-only contents and no scheduler secrets.
The proof restricts the diff shape, validates article metadata and source
contracts, rejects active article content, preserves artifact history, and
requires rendered-browser success.

Every valid new-article PR auto-merges, as does a workflow-synchronization PR
that exactly copies the protected workflows from `main`. Revisions and owner
curation never auto-merge. A revision may change one published article's HTML
and/or matching assets. It adds one numbered Markdown note explaining the change
and cannot rewrite earlier notes or the historical production record.

`main` starts unprotected on purpose: the owner can edit the press and push
directly, without the ceremony of approving their own pull request. The cost is
that the scheduled identity holds the same power, so a prompt-injected run could
change trusted engine or press configuration. Protect `main` when you will
accept the ceremony: every change, including yours, then goes through a reviewed
PR, and the scheduled identity cannot touch the trusted side at all. Review
`press/site.yaml` changes carefully either way, because owner-declared,
integrity-pinned page assets run for readers.
