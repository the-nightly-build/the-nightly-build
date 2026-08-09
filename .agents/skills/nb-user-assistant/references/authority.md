# Authority and source of truth

The user's request establishes the outcome. The current repository establishes
how this version of The Nightly Build works. Inspect before advising or editing.

## Canonical owners

- `docs/` is the human documentation. Link the relevant page when the user will
  benefit from a durable explanation.
- `press/` is the user's specification. Keep paper-specific configuration,
  prompts, themes, furniture, and templates there.
- `spec/` and the orchestrator and editorial-role skill packages govern article
  creation. Do not paraphrase them into user prompts.
- The checkout-owned `nb` command is the operational boundary. Use its help and
  current behavior rather than reconstructing commands.
- `library` is publication state. New articles use `nb prepare-pr`. Revisions
  use an ordinary branch from `origin/library`. Never push directly to the
  `library` branch.

One fact gets one owner. Skills provide judgment and procedure. Docs and config
own product facts. Link rather than copy field lists, provider instructions, or
engine contracts into a workflow.

## Working agreement

Distinguish discovery, proposal, approval, execution, and verification. A user
can approve an editorial direction without approving publication or an external
write. State the impending mutation before making it when the user has not
already requested that change.

Never request secrets in chat. When a provider or GitHub needs a credential,
direct the user to that product's secure settings and ask only for confirmation
or a non-secret status result.

Prefer one manual handoff at a time. Explain why it is necessary, give the
shortest exact action, say what success looks like, and resume from the result.
Do not burden the user with actions the current assistant can safely perform.

Validate every config change with `nb validate`. Before any Article PR, run the
proof through this checkout's `nb`. New articles publish automatically.
Revisions never auto-merge.
