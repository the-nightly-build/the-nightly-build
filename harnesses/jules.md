# Harness adapter — Jules (Google)

## 1. Connect

One-time: install the Jules GitHub app ([jules.google](https://jules.google))
and grant it access to your fork.

## 2. Schedule

Two options:

- **Native Scheduled Tasks** — in Jules, create a Scheduled Task on your fork
  with the prompt below and a nightly cadence.
- **jules-invoke GitHub Action** — use Google's official `jules-invoke` action
  as a thin cloud trigger from a one-line cron workflow in a *separate* repo or
  on `main` (never anything that runs on `library` PRs), passing the same
  prompt.

Fill `<repo>`. **One schedule for the whole press** — the run derives
tonight's work list from the repo, so adding, retiring, or completing series
never touches the schedule. Advanced: per-series schedules (parallel nights) —
append `Work ONLY series <series-id>.` to the prompt.

> You are the night shift for The Nightly Build repo `<repo>`. Read
> `PROTOCOL.md` on main and follow it exactly. Fallback summary: for every
> series configured under `series/` on main, list `library/<series>/` on the
> `library` branch; if the series has an unpublished next item per its
> `series.yaml`, research it deeply with cited sources; render ONE
> self-contained HTML file from the series template with the embedded
> `nb-meta` JSON block; run `python3 engine/check.py <file> --series <id>` and
> revise until BLOCK=0; open ONE pull request per series targeting the
> `library` branch adding ONLY `library/<series>/<slug>.html`, title
> `nb: <series>/<slug> — <Title>`, body containing the nb-meta yaml block. If
> no series has work, exit without a PR. Never modify other files.

## 3. Model

Jules selects its Gemini model tier from your plan; there is no per-task model
picker. Record honest provenance: the run should set `nb-meta.harness` to
`jules` and `nb-meta.model` to the model Jules reports.

## 4. Verify

- Expect a PR titled `nb: <series>/<slug> — …` targeting `library` in the
  window; Jules links the session from the PR.
- Actions tab → `nightly-build-check` for the editor's verdict; clean PRs
  auto-merge and `nightly-build-publish` deploys the site.
- First-run troubleshooting: app not installed on the fork; task created
  against the wrong branch (prompts reference `main` + `library` explicitly);
  no work available (correct silent exit); Pages not enabled (`./setup.sh`);
  Actions disabled — GitHub turns workflows off on forks until you enable
  them once in the fork's Actions tab.
