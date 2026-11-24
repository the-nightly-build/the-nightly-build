# Your first article

Here is what happens between asking for an article and reading it on GitHub
Pages.

## 1. Series selection

A fresh paper has three series. Requested articles go to **Dispatches** by
default. It is open, manual-only, and requires no `press/` edit. **News Brief**
and **Feature** run on a schedule, though the assistant routes a request there
if it fits and the series allows it, stating which series it chose.

## 2. Commission

The assistant turns your request into a commission: the central question, what
must be established rather than merely mentioned, starting material vs. open
research, prior coverage to avoid repeating, the template, and a slug. Links,
topics, questions, and pasted documents are starting points, not the full
evidence base. The assistant asks follow-ups only when the answer changes the
piece.

## 3. Production

Four roles produce the article, each from an exact brief and each saving its
record:

1. **Writing coach** sets how the piece should sound.
2. **Researcher** fetches, reads, and records sources. Nothing is cited unread.
3. **Writer** drafts the article and checks it against `nb check`.
4. **Editor** reads the draft three times and cuts unsupported claims.

## 4. Publication

`nb prepare-pr` opens one PR against `library`. CI validates it with the engine
from `main` and no secrets. A clean new-article PR auto-merges, rebuilds the
site, and publishes to `library/<series>/<slug>.html` with its production record
under `agent-artifacts/`.

Add "let me read it first" to open a draft PR instead. CI still validates it,
and nothing merges until you click **Ready for review**, which re-runs checks
and publishes.

## Cost and troubleshooting

One requested article took ~45 minutes of agent time and ~500k–1M tokens across
the four roles before any repair round. See
[Production cost and role models](../reference/production.md) for per-role
figures and cost levers, and
[Troubleshoot Article PRs](../troubleshooting/article-prs.md) if validation
fails.
