# Ownership and branches

A Nightly Build repository separates three kinds of state:

| State               | Location                  | Owner    | How it changes                                      |
| ------------------- | ------------------------- | -------- | --------------------------------------------------- |
| **Your press**      | `press/` on `main`        | You      | Direct commits or PRs to `main`                     |
| **The engine**      | Everything else on `main` | Upstream | Synced from upstream (local edits own conflicts)    |
| **Published paper** | `library` branch          | CI gate  | Validated PRs only (new articles, revisions, syncs) |

## Your press vs. the engine

Upstream never includes `press/`, so keeping customizations inside `press/`
(title, appearance, editorial direction, production policy, series, prompt
fragments, themes, furniture, and custom templates) gives you conflict-free
engine updates. `examples/` is documentation only and is never read by the
engine.

Scheduled runs always start from current `main`, where both the engine and your
press live.

## The `library` branch and working state

`library` stores published article HTML, article assets, role artifacts, and
protected publishing workflows. Never push directly to `library`, edit its files
in place, merge it into `main`, or include it when forking. Every PR type (new
article, revision, retraction, workflow sync) must match a narrow diff shape.

The GitHub Pages workflow runs on `main` when `library` changes, builds the
static site from `library`, and deploys it as a Pages artifact. Generated site
files, including `catalog.json`, are never committed to `library`.

Generated article branches are disposable: `nb prepare-pr` branches from
`origin/library`, proves its single commit, and prepares the PR. Workspaces
under `.nb-work/` are local scratch state and are never published.

See [Update the engine](../guides/operate/update-engine.md) and
[Publishing and security](publishing-and-security.md).
