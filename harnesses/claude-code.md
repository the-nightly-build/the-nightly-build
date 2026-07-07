# Harness adapter: Claude Code (Routines)

## 0. Runtime

The engine scripts need Python 3.9+ and PyYAML in the run environment. If
`python3 engine/check.py` reports PyYAML missing, install it first
(`pip install pyyaml`) and retry; environments with uv can use
`uv run engine/check.py` instead.

## 1. Connect

One-time: connect your fork at [claude.ai/code](https://claude.ai/code) →
add the GitHub repo. Grant access to the fork (contents + pull requests).
Claude Code Routines run in Anthropic's cloud, so your laptop can be off.

## 2. Schedule

Create **one Routine for the whole press**: in the Claude Code CLI type
`/schedule`, or use [claude.ai/code/routines](https://claude.ai/code/routines).
Set the cadence (nightly, e.g. `0 6 * * *` UTC for a 6:00 build) and paste the
prompt below with `<repo>` filled in. That's the only scheduling you will ever
do: the run derives tonight's work list from the repo, so adding, retiring, or
completing series never touches the Routine. When a course completes, its
series simply stops appearing in the night's work.

Routines push work branches with default `claude/`-prefixed names; that's
fine; all protocol semantics live in the PR, not the branch name.

**Advanced: one Routine per series** (parallel nights, or a different model
per series): create extra Routines and append one line to the prompt:
`Work ONLY series <series-id>.`

> You are the night shift for The Nightly Build repo `<repo>`. Read
> `PROTOCOL.md` on main and follow it exactly. Runtime: needs Python 3.9+ and
> PyYAML; if a script reports it missing, `pip install pyyaml` (or use
> `uv run`). Work from the `main` checkout (it carries the engine and
> `press/`) with the `library` branch checked out separately at `<checkout>`,
> then run `python3 engine/duty.py --repo . --library <checkout>` for tonight's
> due series. For each: research deeply with cited primary sources; render ONE
> self-contained HTML file from the series' template (whichever it declares),
> setting the nb-meta `form` label and using `templates/FURNITURE.md`; run
> `python3 engine/check.py library/<series>/<slug>.html --series <id> --repo .
> --library <checkout>` and revise until `BLOCK: 0`; then write the PR body to
> a file and re-run check with `--pr-body <file>` so it passes too. Open ONE
> PR per series targeting `library`, adding ONLY
> `library/<series>/<slug>.html`, title `nb: <series>/<slug> - <Title>`, body
> containing the nb-meta yaml block. Nothing due: exit without a PR. Never
> merge, push to `library`, or modify other files.

**First build now (don't wait for tonight).** Once the Routine exists and the
repo is connected, trigger it once immediately (the routine's Run now) so
today's edition researches, publishes, and deploys within roughly half an
hour. It then runs on its own every night. Setting up in the morning means a
paper by lunch and a fresh one every day after.

## 3. Model

Pick the model when creating the Routine (settings on the routine); the single
press-level Routine runs every series on that model. Deep research rewards the
strongest model you have access to: Fable/Opus-class for articles;
Sonnet-class is serviceable for briefs. To vary
the model by series, use the advanced per-series Routines above. The edition
records whatever ran in `nb-meta.model`, so your library doubles as a model
comparison corpus.

## 4. Verify

- Within the scheduled window, expect a PR titled `nb: <series>/<slug> - ...`
  targeting `library`.
- The **Actions** tab shows the editor's verdict (`nightly-build-check`);
  clean PRs auto-merge, then `nightly-build-publish` rebuilds the site.
- First-run troubleshooting: repo not connected at claude.ai/code; the Routine
  lacks network access (enable web tools); the Routine ran but found no work
  (correct exit; check whether everything is already published); the site
  404s (GitHub Pages needs a public repo on the free plan, or Pro; make the
  repo public, then `./setup.sh` to enable it); Actions disabled (GitHub turns
  workflows off on forks until you enable them once in the fork's Actions tab).
