# Update a paper

Read `docs/guides/operate/manage-your-paper.md` and the relevant reference
page. Read [prompt authoring](../craft/prompt-authoring.md) whenever prose
direction will change.

## Diagnose the request

Translate the user's observation into its true owner before editing:

- a different beat, angle, or recurring structure usually belongs in a series
  prompt
- paper-wide register and reader assumptions belong in `editorial.md`
- how articles should sound belongs in `editorial.md` for the whole paper, or
  in a register line in the series prompt for one section
- a repeated word or verbal tic belongs in `press/banned-terms.yaml`
- timing and item admission belong in `series.yaml`
- evidence composition belongs in source policy fields
- recurring production usage may belong in cadence, series boundaries,
  commissioned items, or production policy
- an isolated article correction belongs in the revision workflow
- a presentational need may belong in existing furniture before new design

Route feedback across the full customization surface before concluding
something cannot be prevented. The feature catalog
(`docs/reference/README.md`) maps every mechanism. When the fix is genuinely
infeasible in the current system but plausibly simple in the engine, offer to
open a feature request on the upstream repository, only with the user's
permission.

Inspect recent published examples only to test a concrete diagnosis. Do not
copy their structure forward or tour the archive for background.

## Propose the smallest durable change

Explain the observed failure, the owning layer, and how the proposed change
will alter future output. Test it against at least one intended case and one
case it should not affect. A prompt addition that merely describes the last
bad article is overfit. Rederive the editorial principle.

Apply the change on `main`, run `nb validate`, and preview when appearance,
furniture, or templates change. Keep unrelated improvements out of the diff.
If confidence depends on article output, recommend a local preview before the
change lands.

For a production-usage request, read `docs/reference/production.md` before
proposing a change and use the next normal run to evaluate its effect.
