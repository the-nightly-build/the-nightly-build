# Update a paper

Read `docs/guides/operate/manage-your-paper.md` and the relevant reference page. Read
[prompt authoring](../craft/prompt-authoring.md) whenever prose direction will
change.

## Diagnose the request

Translate the user's observation into its true owner before editing:

- a different beat, angle, or recurring structure usually belongs in a series
  prompt;
- paper-wide register and reader assumptions belong in `editorial.md`;
- timing and item admission belong in `series.yaml`;
- evidence composition belongs in source policy fields;
- an isolated article correction belongs in the revision workflow;
- a presentational need may belong in existing furniture before new design.

Inspect recent published examples only to test a concrete diagnosis. Do not
copy their structure forward or conduct an ambient archive tour.

## Propose the smallest durable change

Explain the observed failure, the owning layer, and how the proposed change
will alter future output. Test it against at least one intended case and one
case it should not affect. A prompt addition that merely describes the last
bad article is overfit; rederive the editorial principle.

Apply the change on `main`, run `nb validate`, and preview when appearance,
furniture, or templates change. Keep unrelated improvements out of the diff.
If confidence depends on article output, keep autopublish off and recommend a
targeted test article.
