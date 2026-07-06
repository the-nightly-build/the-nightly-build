# Phase 6 — end-to-end verification runbook

Phase 6 (handoff §13.6) has two halves.

## Local half — automated, done

`engine/tests/run_e2e_test.py` (part of `run_tests.py`) rehearses two nights
against a real git repo shaped exactly like production: orphan `library`
branch, one-file agent branches, the editor's exact PR-mode invocation
(engine + configs from a main checkout, diff from the PR checkout), the
autopublish gate, squash merges, and a site rebuild after each night. It
asserts the §13.6 outcomes: a multi-edition front page on night 1, rollover
and permanence on night 2, and feed updates both nights. It also rehearses a
same-slug race (losing PR is refused with `B-MODE`).

Phase 6 review caught and drove four production fixes:
1. PR mode loaded series configs from the PR checkout, which on a real orphan
   `library` branch has none — every production PR would have failed
   `B-SERIES`. `check.py` now takes `--main` (check.yml passes `_main`).
2. YAML reads unquoted `slug: 2026-07-05` in PR bodies as a date object —
   every rolling PR would have failed `B-META-MATCH`. `parse_pr_body` now
   normalizes dates to ISO strings.
3. GitHub fires `pull_request`/`push` triggers only from workflow files
   present on the base/pushed branch — an orphan `library` carries none, so
   neither the editor nor the press would ever have run. `setup.sh` now seeds
   trigger-only copies of both workflows onto `library` (all engine logic is
   still checked out from `main` at run time, so §1 invariant 1 holds;
   `B-DIFF-SHAPE` keeps agent PRs off the seeded files).
4. Pushes made with `GITHUB_TOKEN` fire no events (recursion guard), so the
   editor's auto-merge could never have started the press. The automerge job
   now dispatches `publish.yml` explicitly; human merges trigger it normally.

## Cloud half — human-run, two nights

What the automation cannot prove: a real harness schedule firing unattended,
GitHub Actions running the editor and the press, and Pages serving the result.

1. Fork (or use a test fork of) this repo; clone; run `./setup.sh`. Confirm
   the `library` branch now carries `.github/workflows/` (the seeded triggers).
2. On the upstream repo the shipped dogfood pair is the assignment
   (`semiconductors` = collection, `ai-briefs` = rolling). On a fork, setup
   clears them — configure your own collection + rolling pair instead.
3. Connect the fork at claude.ai/code, then create two Routines per
   `harnesses/claude.md` — one per series, nightly cadence, the filled
   schedule prompt.
4. **Night 1 checklist:** two PRs titled `nb: …` appear → `nightly-build-check`
   passes → auto-merge → `nightly-build-publish` deploys → the Pages front
   page shows a two-edition build → `feed.xml` has both entries.
5. **Night 2 checklist:** the rolling series publishes the new date; the
   collection series publishes its next item; night 1's build page is
   unchanged; feeds updated.
6. Delete one published edition file on `library` and confirm the next run
   rewrites it (the documented regeneration escape hatch).

Nothing needs to be undone afterwards — the test library is a real library.
