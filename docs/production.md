# Production cost and role models

The scheduled correspondent uses the model selected in your automation. Article
roles can use cheaper models without changing the schedule by adding the optional
`press/production.yaml` file:

```yaml
profile: balanced
required: false
stages:
  writer:
    model: capable
    effort: high
```

The four profiles are `inherit`, `economy`, `balanced`, and `quality`. A press
with no production file uses `balanced`, the cost-aware default. Set
`profile: inherit` explicitly to preserve the harness's existing model and effort
for every role.

Profiles use portable model tiers:

- `efficient`: the lowest-cost available model competent for tool work.
- `capable`: a strong general model below the harness's premium tier.
- `premium`: the strongest available model.
- `inherit`: the model already selected by the runtime.

The correspondent maps these tiers to models the current harness actually
offers. To pin one provider instead, write its exact model ID. Effort is also a
plain string because providers expose different levels.

```yaml
stages:
  researcher:
    model: provider/exact-model-id
    effort: medium
    required: true
```

`required: false` is guidance: if the harness cannot select the requested model
or effort, it chooses the closest available option and records that choice in
the commission. With `required: true`, the article stops before that role when
the runtime cannot honor or verify the directive. A stage-level value overrides
the paper-wide value.

The configurable stages are `writing-coach`, `researcher`, `writer`, `editor`,
and `publisher`. The correspondent is deliberately absent: choose its model in
the automation itself, where the run begins.

## Per-series overrides

A costly or unusually demanding section can specialize the press defaults in
its `series.yaml`:

```yaml
production:
  profile: quality
  stages:
    researcher:
      model: efficient
      effort: high
```

Resolution starts from the series profile when one is present, otherwise the
press profile. Press stage fields apply next, then series stage fields. For
`required`, the order is press-wide, press stage, series-wide, series stage.
Inspect the exact result with:

```sh
uv run engine/production_policy.py --repo . --series <id>
```

Production policy never skips an editorial stage and does not estimate token or
dollar usage. Only the harness can report authoritative usage.
