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
> `PROTOCOL.md` on main and follow it exactly. Fallback summary: for every
> series configured under `press/series/` on main, list `library/<series>/` on the
> `library` branch; if the series has an unpublished next item per its
> `series.yaml`, research it deeply with cited sources; render ONE
> self-contained HTML file from the series template with the embedded
> `nb-meta` JSON block; run `python3 engine/check.py <file> --series <id>` and
> revise until BLOCK=0; open ONE pull request per series targeting the
> `library` branch adding ONLY `library/<series>/<slug>.html`, title
> `nb: <series>/<slug> - <Title>`, body containing the nb-meta yaml block. If
> no series has work, exit without a PR. Never modify other files.

## 3. Model

Pick the model when creating the Routine (settings on the routine); the single
press-level Routine runs every series on that model. Deep research rewards the
strongest model you have access to: Fable/Opus-class for longread templates
(dossier, lesson, chronicle); Sonnet-class is serviceable for briefs. To vary
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
  (correct exit; check whether everything is already published); Pages not
  enabled (`./setup.sh`); Actions disabled (GitHub turns workflows
  off on forks until you enable them once in the fork's Actions tab).
