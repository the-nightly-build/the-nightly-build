# Manage your paper

Day-to-day changes belong on `main` under `press/`. Ask your AI in plain
language; it should translate the request into the smallest configuration
change, run `nb validate`, show the effect, and commit it for review.

Common requests include:

- pause or resume a series with `paused`;
- change its schedule with `cadence`;
- commission or reorder configured items;
- refine a beat in `prompt.md`;
- change paper-wide voice in `editorial.md`;
- adjust role model guidance in `production.yaml`;
- change appearance or add carefully designed furniture.

Use `cadence: manual` for a series that should publish only when someone asks.
It is never returned as due by `nb duty`. A manual open series also requires
each article to have a configured item before article initialization or CI
will accept it.

Configuration changes do not edit the published archive. To correct an article
already on `library`, use [Revise an article](../publish/revise-an-article.md). To remove
one, use an owner-authored deletion-only curation PR.

The exact series fields live in [Series reference](../../reference/series.md).
