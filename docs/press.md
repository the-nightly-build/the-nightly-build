# Your paper: ownership, forks, updates

## The layout rule

`press/` is yours. All configuration lives there: series, voice, title,
themes, templates. The directory does not exist on the upstream repository,
so upstream can never ship a change that collides with it.

Everything else is the engine. You have no reason to touch it, but it is
your fork and you can (see below).

`examples/` is a complete working paper configuration kept as
documentation. The engine never reads it. Copy from it into `press/`.

The upstream repository is engine-only. It runs no paper and publishes no
library. The maintainer dogfoods by copying it like any other user.

```text
press/
  site.yaml          masthead title, theme, appearance, front density
  editorial.md       your voice, composed into every article's instructions
  series/<id>/       series.yaml + prompt.md + sources/ per series
  series/_tags/      reusable prompt fragments shared across series
  themes/            custom design token files
  furniture/         shared furniture: catalog.md + styles.css (see customization.md)
  templates/<id>/    your own template packages: manifest, skeleton, brief, furniture
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
4. Publish forever. The night shift adds articles to `library` via one-file
   PRs. `main` only changes when you change configuration or pull an engine
   update.

## Updating the engine

```sh
git remote add upstream https://github.com/the-nightly-build/the-nightly-build.git   # once
git fetch upstream
git merge upstream/main
./setup.sh    # re-syncs the trigger workflows onto library
```

This is an ordinary fork merge. It is clean by construction for anyone who
only writes inside `press/`: your commits and upstream's commits touch
disjoint paths, and upstream has no `press/` at all.

Editing the engine is allowed. It is your fork. If you patch engine files,
future merges may conflict exactly where you deviated, and resolving them is
yours, the same as any fork on GitHub.

Three follow-ups after an engine update:

- `./setup.sh` re-syncs the two trigger workflows that the `library` branch
  carries. They are the only engine-adjacent files outside `main`.
- Check your schedule prompt against the canonical one in
  [scheduling.md](scheduling.md). The prompt lives outside the repo (a hosted
  routine, an Actions step), so a merge cannot update it, and a prompt that
  restates the pipeline rots as the engine improves. If yours says more than
  the canonical prompt, replace it.
- Optionally dispatch the publish workflow (Actions, nightly-build-publish,
  Run workflow) to re-render your whole back catalog with the new engine
  immediately instead of waiting for tonight's build. Nothing on `library`
  ever merges with upstream. Forks copy `main` only, and your library is
  yours alone.
