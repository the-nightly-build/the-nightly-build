# Harness adapter: Codex (OpenAI)

## 0. Runtime

The engine scripts need Python 3.9+ and PyYAML in the run environment. If
`python3 engine/check.py` reports PyYAML missing, install it first
(`pip install pyyaml`) and retry; environments with uv can use
`uv run engine/check.py` instead.

## 1. Connect

One-time: connect GitHub in Codex settings
([chatgpt.com/codex](https://chatgpt.com/codex) → Settings → GitHub) and grant
access to your fork. Codex cloud tasks run with the repo checked out.

## 2. Schedule

Codex's native automations currently run on your local machine, so for a
laptop-off nightly use a thin cloud trigger: a one-line cron workflow (in a
separate repo, or on `main`) that fires a Codex cloud task via the Codex API;
or an issue-label trigger if you prefer click-to-run. The trigger passes the
prompt below verbatim; all real behavior lives in `PROTOCOL.md`.

Fill `<repo>`. **One schedule for the whole press**: the run derives
tonight's work list from the repo, so adding, retiring, or completing series
never touches the trigger. Advanced: per-series triggers (parallel nights, or
different models): append `Work ONLY series <series-id>.` to the prompt.

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

Choose the model/reasoning effort in Codex settings (or per task via the API
call). Deep research rewards the strongest tier; the edition records what ran
in `nb-meta.model` (`nb-meta.harness: codex`).

## 4. Verify

- Expect a PR titled `nb: <series>/<slug> - ...` targeting `library` in the
  window.
- Actions tab → `nightly-build-check` for the editor's verdict; clean PRs
  auto-merge and `nightly-build-publish` deploys the site.
- First-run troubleshooting: GitHub not connected in Codex settings; the cloud
  environment lacks internet access (enable it in the Codex environment
  settings; research requires web); no work available (correct silent exit);
  Pages not enabled (`./setup.sh`); Actions disabled (GitHub turns workflows
  off on forks until you enable them once in the fork's Actions tab).
