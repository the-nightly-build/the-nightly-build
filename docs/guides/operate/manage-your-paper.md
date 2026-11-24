# Manage your paper

Day-to-day changes live under `press/` on `main`. Ask your AI in plain language
("pause the docket series", "make the brief weekdays only", "commission a deep
dive on ASML", "less policy in the brief", "use a cheaper model for research")
and review the small validated diff it commits.

## Adjusting coverage and cadence

- **Topic focus:** edit the opening paragraph of a series's `prompt.md` (the
  same paragraph updated by the two-question flow in
  [Create your paper](../../getting-started/create-your-paper.md)).
- **Manual-only series:** set `cadence: manual` so `nb duty` never schedules it.
  In an open manual series, any slug is allowed and `items` acts only as topic
  suggestions.
- **Same-day runs:** you can request multiple articles in one series on the same
  day. On scheduled runs, `nb duty` treats a series as done once an article
  dated today (UTC) is published, so a requested article counts as that day's
  scheduled slot.

Configuration edits never change published articles on `library`. To edit a
published piece, see [Revise an article](../publish/revise-an-article.md).

## Retracting a published article

Open a PR against `library` that only deletes:

- `library/SERIES/SLUG.html`
- matching assets under `library/SERIES/SLUG/`
- production records under `agent-artifacts/SERIES/SLUG/`

CI allows this diff only when authored by the repository owner and never
auto-merges it. Once you merge the PR, the next build removes the article from
all indexes, feeds, and `catalog.json`. Git history preserves the deleted files.

See [Series reference](../../reference/series.md) for all configuration keys.
