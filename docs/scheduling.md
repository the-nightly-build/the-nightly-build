# Scheduling the night shift

The night shift is just an agent that runs on a clock. Any agent that can check
out your repo, browse the web, and open a pull request can be it. This page is
how you put one on a nightly schedule.

Two choices are involved, and they are independent:

1. **The setup agent** is whatever you are talking to right now (any coding
   agent). It configures `press/` and wires up the schedule. It does not have to
   be the same product that runs the night shift.
2. **The night-shift runtime and its scheduler** is what actually fires nightly.
   You can do setup in one agent and schedule the night shift on another.

The scheduler comes in two shapes. Some providers host their own; when yours
does, that is the shortcut, and it is often included in a plan you already pay
for. When it does not, the universal path below runs the same night shift on a
GitHub Actions cron. That path always works. Which specific agents can be the
night shift, how to invoke each, and what a run costs are in
[harnesses.md](harnesses.md).

## What the night shift needs

Four requirements. Everything past them lives in `PROTOCOL.md`.

1. A scheduler that fires on a nightly cron.
2. A checkout of `main` (the engine and `press/`) with the `library` branch
   available separately.
3. Web access for research. Many cloud run environments sandbox outbound
   network by default, so this usually has to be enabled on the environment
   explicitly. Without it the night shift reaches nothing and correctly
   publishes nothing, rather than citing pages it never opened.
4. Permission to open a pull request to `library`.

## The universal path: GitHub Actions

This runs the night shift on GitHub's runners with your machine off, using any
agent that has a headless command. No vendor scheduler required. Copy this into
your fork as `.github/workflows/nightly.yml` and fill in the one marked step:

```yaml
name: nightly-build
on:
  schedule:
    - cron: "0 6 * * *" # 06:00 UTC nightly; pick your hour
  workflow_dispatch: {} # run tonight's first article on demand
permissions:
  contents: write # push the work branch
  pull-requests: write # open the PR to library
jobs:
  night-shift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4 # main: engine + press/
      - uses: actions/checkout@v4 # library, checked out separately
        with:
          ref: library
          path: library-checkout
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pyyaml
      # Invoke your agent here with the prompt below. It needs web access, your
      # agent's API key as a repo secret, and the two permissions declared above.
      # Per-agent one-liners are in docs/harnesses.md.
```

The trigger lives on `main` (or in a separate repo). Never put it on the
`library` PR path: the editor validates untrusted article PRs with read-only
permissions and no secrets, and that boundary is the security model. A scheduled
workflow on `main` holding your API key is the trusted side of the same line the
morning mailer already sits on.

### Security: the night shift is untrusted by design

The night shift researches by reading arbitrary web pages, so it can be
prompt-injected by a page it visits, and no instruction reliably prevents that.
The system is built to contain a compromised run, not to trust it:

- Every article is validated by the proof (`engine/check.py`) and sandboxed: no
  scripts beyond the engine runtime, no iframes or forms, no meta-refresh, and
  external references only to the engine assets and Google Fonts. `setup.sh`
  protects the `library` branch with `enforce_admins: true`, so the `validate`
  check gates every merge, including runs that use your own token. A hijacked
  run can do no more than open a PR the proof rejects.
- The blast radius is your own fork only. A successful injection can alter your
  `main` (the engine, or the `assets:` list in `press/site.yaml`, which loads
  owner-authored JavaScript into every page), but never another user's paper or
  the canonical repo, and it lands in your own commit history where you can see
  it.

For a stricter boundary, run the schedule under a least-privilege identity: a
fine-grained token or a bot collaborator that can push feature branches and open
PRs but cannot push to `main` or `library`. That contains the autonomous night
shift without touching your own ability to edit `press/` directly. And because
`press/site.yaml`'s `assets:` block runs JavaScript on every reader's page,
never let an untrusted agent edit it.

### The schedule prompt

Paste it verbatim wherever your scheduler takes a prompt (a hosted routine, a
scheduled task, or the invoke step above), with `<repo>` and `<checkout>`
filled in. It defers everything to the repository on purpose: a prompt that
owns nothing the repo owns cannot rot as the engine improves, and its last
sentence makes a stale prompt announce itself on the next run.

> You are the night shift for The Nightly Build repo `<repo>`. Check out
> `main` and read `PROTOCOL.md`: it is the complete contract, and the
> correspondent skill carries the procedure. Check out the `library` branch
> beside it at `<checkout>`. The engine scripts need Python 3.10+ and PyYAML
> (`pip install pyyaml` if one reports it missing), and research needs web
> access. This paragraph is the entire assignment. If your schedule prompt
> says more than this, it predates the engine you are running: flag that in
> your PR bodies and ask the owner to paste the current paragraph from
> `docs/scheduling.md`.

One schedule runs the whole paper. Each night the run derives its work list from
the repo, so adding, retiring, or completing a series never touches the
schedule. To run series on different models or in parallel, add a second
schedule and append one line: `Work ONLY series <series-id>.`

## Which agent, and the cost

For the specific agents verified to run the night shift, how to invoke each
headless, whether a run is subscription-included or metered, and the native
provider shortcuts (hosted routines and scheduled tasks), see
[harnesses.md](harnesses.md). The universal Actions path above works with any of
them.
