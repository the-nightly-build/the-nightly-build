# Production cost and role models

The scheduled orchestrator uses the model selected in your automation. Article
roles can use cheaper models without changing the schedule by adding the
optional `press/production.yaml` file:

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
`profile: inherit` explicitly to preserve the harness's existing model and
effort for every role.

Profiles use portable model tiers:

- `efficient`: the lowest-cost available model competent for tool work.
- `capable`: a strong general model below the harness's premium tier.
- `premium`: the strongest available model.
- `inherit`: the model already selected by the runtime.

The orchestrator maps these tiers to models the current harness actually offers.
To pin one provider instead, write its exact model ID. Effort is also a plain
string because providers expose different levels.

## Billing model comes first

Production policy controls model selection. It cannot predict how a provider
bills or limits the resulting work.

A subscription converts model work into plan usage according to rules owned by
the provider. Token observations do not reliably predict the share of a weekly
or monthly allowance that one run will consume. Use the provider's usage report
after the first normal production run as the baseline for that paper. The
scheduled-runtime smoke test verifies access and permissions without producing
articles, so it is not a usage baseline.

A metered API charges for the exact models and token classes used. Estimate
dollars only after those models are selected and their current input, output,
and cached-token prices are known. Include repeated role invocations and leave
room for orchestration. The orchestrator selects topics, commissions articles,
supervises roles, routes repairs, prepares PRs, and follows publication. That
work sits outside the four configured role stages.

## Observed workload

One working configuration produced five to seven articles in 45 to 90 minutes
because independent articles ran in parallel. Its role invocations consumed:

| Work                       | Observed time | Observed tokens |
| -------------------------- | ------------- | --------------- |
| Initial orchestration      | 10–15 minutes | About 100k      |
| Researcher, per article    | 10–15 minutes | 100k–200k       |
| Writing coach, per article | 5–10 minutes  | 50k–100k        |
| Writer, per article        | 15–25 minutes | 150k–350k       |
| Editor, per article        | 5–15 minutes  | 150k–250k       |

These are observations, not limits or promises. A role may run again after an
editorial request or failed check. The table also excludes continuing
orchestrator work because it has not been measured reliably. It describes
workload, not a guaranteed subscription allowance or API bill.

## Stage directives

The orchestrator launches every article role directly. Each role receives an
exact brief and only the article context it needs. When isolated children are
unavailable, the same artifact sequence runs in one context. The policy controls
those four launches. It does not select the orchestrator itself and does not
require nested agents or a provider-specific team feature.

```yaml
stages:
  researcher:
    model: provider/exact-model-id
    effort: medium
    required: true
```

`required` controls who may change a directive, and it never stops an article.
With `required: false`, the setting is guidance: the orchestrator may deviate
when its judgment calls for it, recording the choice in the commission. With
`required: true`, the directive is not the orchestrator's to change: no judgment
call, no cost-driven downgrade. When the runtime genuinely cannot honor or
verify a required directive, the orchestrator uses the closest available option,
records the deviation prominently in the commission, and production continues. A
stage-level value overrides the paper-wide value.

The configurable stages are `writing-coach`, `researcher`, `writer`, and
`editor`. The orchestrator is deliberately absent: choose its model in the
automation itself, where the run begins.

A series that pins a voice guide never launches the writing coach, so its
`writing-coach` directives do not apply. Nothing else changes: the article still
carries a `writing-coach/01` record holding the pinned guide.

## Reduce usage without weakening the paper

Start with the commission. A broad or ambiguous series spends more work
discovering candidate subjects and deciding what belongs. Current-events
coverage often adds verification because claims change quickly and sources
disagree. Narrower series boundaries and precise queued commissions settle more
of those decisions before research begins.

Pin a voice guide on any series whose sound is settled. This is the only
reduction that removes a role invocation rather than making one cheaper: the
writing coach does not run, and the observed 5 to 10 minutes and 50k to 100k
tokens above go with it, every article, every night. See
[Series](series.md#pinning-a-voice-guide).

Then match models to the role each series needs. Research quality may dominate a
news-heavy series, while another series depends more on voice or drafting. Use
paper-wide defaults for the common case and per-series overrides for the
exceptions. Lowering cadence or running fewer series reduces total article work.
Parallel execution reduces elapsed time, but every article still consumes its
own role invocations.

## Per-series overrides

A costly or unusually demanding section can specialize the press defaults in its
`series.yaml`:

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
nb production-policy --repo . --series <id>
```

Production policy never skips an editorial stage and does not estimate token or
dollar usage. Only the harness can report authoritative usage.
