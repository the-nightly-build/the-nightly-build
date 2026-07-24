# Your paper: ownership, forks, updates

## The layout rule

`press/` is yours. All configuration lives there: series, voice, title,
themes, templates. The directory does not exist on the upstream repository,
so upstream can never ship a change that collides with it.

Everything outside `press/` is engine-owned. Keep paper-specific work inside
`press/`; you can edit the engine in your fork, but future engine updates may
then conflict with those changes.

`examples/` is a complete working paper configuration kept as
documentation. The engine never reads it. Copy from it into `press/`.

The upstream repository is engine-only. It runs no paper and publishes no
library. The maintainer dogfoods by copying it like any other user.

```text
press/
  site.yaml          masthead title, theme, appearance, front density
  editorial.md       your voice, composed into every article's instructions
  production.yaml    optional paper-wide role model and effort guidance
  series/<id>/       series.yaml + prompt.md + sources/ per series
  series/_tags/      reusable prompt fragments shared across series
  themes/            custom design token files
  furniture/         shared furniture: catalog.md + styles.css (see customization.md)
  templates/<id>/    your own packages: manifest, skeleton, identity, furniture
```

## The fork lifecycle

1. Fork with GitHub's "Copy the main branch only" box checked. Keep the fork
   **public** if you want the published site: GitHub Pages needs a public repo
   on the free plan (a private repo needs Pro).
2. Set up: say "set me up" to your agent, or run `./setup.sh` by hand. It
   scaffolds your empty `press/`, creates the empty `library` branch, seeds
   its trigger workflows, clears the library branch to deploy, and enables
   Pages and auto-merge. Enable workflows once in your fork's Actions tab.
3. Connect and schedule (cloud harnesses): authorize the night shift to reach
   your repo and schedule one nightly run per the path you pick in
   [scheduling.md](scheduling.md) (a native scheduler, often included in your
   plan, or the universal GitHub Actions cron). Optionally trigger it once now
   so today's first article publishes instead of waiting for tonight.
4. Publish forever. The night shift adds article bundles to `library` via isolated
   PRs. `main` only changes when you change configuration or pull an engine
   update.

## Updating the engine

### From GitHub

Click **Sync fork**. This updates your fork's `main`; it never touches
`library`. The next night shift runs `scripts/sync.sh`, updates the protected
publishing workflows through CI if needed, and only then starts article work.

To finish the workflow sync immediately from a local checkout:

```sh
git switch main
git pull --ff-only origin main
scripts/sync.sh
```

This is also how an older fork adopts `scripts/sync.sh` for the first time.
Do not rerun setup or update `library` yourself.

### From the command line

Once your fork contains `scripts/sync.sh`, one command performs the complete
engine update:

```sh
scripts/sync.sh --update-main-from-upstream
```

This deliberate command merges upstream into your clean, current `main`,
pushes it, and brings the protected `library` workflows forward through an
exact, CI-gated PR. A merge conflict stops before `library` changes and names
the paths to resolve.

The default command follows your fork's `origin/main`; it never imports
upstream changes. Only the explicit flag above fetches upstream.

Upstream merges are clean by construction for anyone who only writes inside
`press/`: your commits and upstream's commits touch disjoint paths, and
upstream has no `press/` at all.

Editing the engine is allowed. It is your fork. If you patch engine files,
future merges may conflict exactly where you deviated, and resolving them is
yours, the same as any fork on GitHub.

Two follow-ups after an engine update:

- Check your schedule prompt against the canonical one in
  [scheduling.md](scheduling.md). The prompt lives outside the repo (a hosted
  routine, an Actions step), so a merge cannot update it, and a prompt that
  restates the pipeline rots as the engine improves. If yours says more than
  the canonical prompt, replace it.
- Optionally dispatch the publish workflow (Actions, nightly-build-publish,
  Run workflow) to re-render your whole back catalog with the new engine
  immediately instead of waiting for tonight's build.

`library` is downstream publication state. Never merge it into `main` or
upstream. Forks copy `main` only; your library is yours alone.
