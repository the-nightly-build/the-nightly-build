# Manage your paper

Day-to-day changes belong on `main` under `press/`. Ask your AI in plain
language and expect the smallest configuration change that satisfies the
request, validated and committed for your review.

Common requests: "pause the docket series", "make the brief weekdays only",
"commission a deep dive on ASML", "less policy in the brief for a while", "use a
cheaper model for research", "give the paper a new look". Each lands as one
small diff under `press/`.

Use `cadence: manual` for a series that should publish only when someone asks.
It is never returned as due by `nb duty`. In a manual open series, every new
article's slug must be a configured item, and both article initialization and CI
enforce that.

Configuration changes do not edit the published archive. To correct an article
already on `library`, use [Revise an article](../publish/revise-an-article.md).

To retract an article, open a PR against `library` that only deletes
`library/SERIES/SLUG.html`, its matching `library/SERIES/SLUG/` assets, and the
article's `agent-artifacts/SERIES/SLUG/` production record. CI accepts that
shape only when the PR author is the repository owner, and a curation PR never
auto-merges. You review and merge it yourself. The next build removes the
article from every index, feed, and the catalog. Git history preserves
everything a retraction deletes.

The exact series fields live in [Series reference](../../reference/series.md).
