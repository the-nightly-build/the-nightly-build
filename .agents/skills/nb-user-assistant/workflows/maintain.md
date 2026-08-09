# Maintain and curate a paper

Route maintenance to the canonical guide before acting:

- engine update: `docs/guides/operate/update-engine.md`
- schedule or capability failure: `docs/guides/operate/schedule.md` and
  `docs/troubleshooting/setup-and-scheduling.md`
- Article PR failure: `docs/troubleshooting/article-prs.md`
- feeds, catalog, directory, or Pages URLs: `docs/reference/delivery.md`

Inspect state and diagnose before mutating. Preserve user changes and keep
engine updates separate from press edits. Run `nb sync` through the documented
path, and never repair protected `library` workflow files by hand.

For curation, distinguish correction from removal. A correction uses the
revision workflow. A retraction is an owner-authored deletion-only PR removing
one article, its matching local assets, and its `agent-artifacts` production
record. Git history preserves what it removes. Never push the deletion directly
to `library`.

Real usage settles what the interview could only estimate, so review cost once
the paper has published for a week. Read the provider's usage report against the
plan the user is on, and count published articles against the observed per-role
work in `docs/reference/production.md`. Bring back a decision rather than a
statistic: a section not earning its nightly research can drop cadence,
downgrade a stage, or pin a voice guide. Confirm the change with the user before
editing `press/`.

When troubleshooting, report the failing boundary, direct evidence, and the next
test. Do not retry unchanged work indefinitely or paper over a permission
failure with a different environment. Resume at the failed requirement after the
user or provider changes it.
