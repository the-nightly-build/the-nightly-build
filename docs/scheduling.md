# Scheduling the night shift

The night shift is an agent that runs on a clock. Any agent that can check out
your repo, browse the web, and open a pull request can run it. This page helps
you choose the scheduler and give it the access it needs.

Two choices are involved, and they are independent:

1. **The setup agent** is whatever you are talking to right now (any coding
   agent). It configures `press/` and wires up the schedule. It does not have to
   be the same product that runs the night shift.
2. **The night-shift runtime and its scheduler** is what actually fires nightly.
   You can do setup in one agent and schedule the night shift on another.

The scheduler comes in two shapes. Some providers host their own; when yours
does, that is the shortcut, and it may be included in a plan you already pay
for. Otherwise, the universal path below runs the same night shift on a GitHub
Actions cron. Which agents are supported, how to invoke them, and how usage is
billed are in [harnesses.md](harnesses.md).

## What the night shift needs

Four requirements. Everything past them lives in `PROTOCOL.md`.

1. A scheduler that fires on a nightly cron.
2. A checkout of `main` (the engine and `press/`) with access to the fork's
   `origin/main` and `origin/library` refs.
3. Web access for research. Many cloud run environments sandbox outbound
   network by default, so this usually has to be enabled on the environment
   explicitly. Without it the night shift reaches nothing and correctly
   publishes nothing, rather than citing pages it never opened.
4. Permission to push work branches and open pull requests to `library`.

Every run starts with `scripts/sync.sh`. It follows the fork's `main`, waits
for any protected workflow repair to merge, and stops before article work if
the publishing boundary is not current. With an authenticated GitHub CLI it
performs the repair itself. Otherwise it prepares and proves the exact branch,
then hands the PR operations to the same connected GitHub tools the agent uses
for article PRs.

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
    env:
      GH_TOKEN: ${{ github.token }}
    steps:
      - uses: actions/checkout@v4 # main: engine + press/
      - uses: actions/checkout@v4 # library; the agent refreshes it after sync
        with:
          ref: library
          path: library-checkout
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"
      # Invoke your agent here with the prompt below. It needs web access, your
      # agent's API key as a repo secret, and the two permissions declared above.
      # Per-agent one-liners are in docs/harnesses.md.
```

The trigger lives on `main` (or in a separate repo). Never put it on the
`library` PR path: the editor validates untrusted article PRs with read-only
permissions and no secrets, and that boundary is the security model. A scheduled
workflow on `main` holding your API key is the trusted side of that line.

### Security: contain the night shift

The night shift reads arbitrary web pages. Treat it as untrusted: a page can
prompt-inject the agent, and instructions alone cannot prevent that.

- Article PRs are checked without scheduler secrets. The proof rejects active
  content, including extra scripts, iframes, forms, and meta-refresh.
  `scripts/setup.sh` protects `library`, and its required `validate` check
  gates every merge.
- The scheduled agent is more powerful. The Actions example grants repository
  contents write access so it can create work branches. Unless you also protect
  `main`, a compromised run can change the engine or trusted configuration in
  your fork. It cannot change another user's paper or the canonical repository.

For stronger containment, protect `main` as well as `library` and run the
schedule under the narrowest identity your provider supports. That stricter
setup needs feature branches and pull requests, not direct writes to either
protected branch. Because `press/site.yaml` can add JavaScript to every reader's
page, review changes to it as engine changes.

### The schedule prompt

Paste it verbatim wherever your scheduler takes a prompt (a hosted routine, a
scheduled task, or the invoke step above), with `<repo>` and `<checkout>`
filled in. It defers everything to the repository on purpose: a prompt that
owns nothing the repo owns cannot rot as the engine improves, and its last
sentence makes a stale prompt announce itself on the next run.

> You are the night shift for The Nightly Build repo `<repo>`. Check out
> `main` and read `PROTOCOL.md`: it is the complete contract, and the
> correspondent skill carries the procedure. Check out the `library` branch
> beside it at `<checkout>`. The engine scripts need uv and Python 3.10+;
> run them through `uv run`. Research needs web
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
