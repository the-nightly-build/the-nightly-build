# Production cost and role models

Configure article-role models and reasoning effort in optional
`press/production.yaml` (paper-wide) and under `production:` in `series.yaml`
(per-series). The orchestrator always uses its harness or scheduler model.

```yaml
profile: balanced
required: false
stages:
  writer:
    model: capable
    effort: high
```

## Profiles and portable tiers

If `press/production.yaml` is absent, the press defaults to `balanced`.

| Profile    | Purpose                                                     |
| ---------- | ----------------------------------------------------------- |
| `balanced` | Cost-aware default across roles                             |
| `economy`  | Lower-cost role mapping                                     |
| `quality`  | Higher-capability role mapping                              |
| `inherit`  | Keep the harness's current model and effort for every stage |

| Portable tier | Meaning                                               |
| ------------- | ----------------------------------------------------- |
| `efficient`   | Lowest-cost model competent for tool work             |
| `capable`     | Strong general model below the harness's premium tier |
| `premium`     | Strongest available model                             |
| `inherit`     | Model already selected by the runtime                 |

The orchestrator maps tiers to models available in the active harness. To pin a
specific model instead, set `model` to the provider's exact model ID. `effort`
takes a provider-supported string (e.g., `low`, `medium`, `high`).

## Stage directives

Configurable stages: `writing-coach`, `researcher`, `writer`, and `editor`. The
orchestrator is configured in your scheduler, not here.

```yaml
stages:
  researcher:
    model: provider/exact-model-id
    effort: medium
    required: true
```

| `required` | Behavior                                                                                                                                                      |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `false`    | Guidance: the orchestrator may adjust when warranted and logs the choice in the commission.                                                                   |
| `true`     | Binding: no judgment-based downgrade. If the runtime cannot honor or verify it, the orchestrator uses the closest option, logs it prominently, and continues. |

- When isolated child contexts are unavailable, the same four stages run
  sequentially with identical records.
- If a series pins a `voice_guide`, `writing-coach` does not run (its stage
  directives are ignored, while `writing-coach/01` still records the pinned
  guide).

## Precedence and inspection

Per-series overrides live under `production:` in `series.yaml`:

```yaml
production:
  profile: quality
  stages:
    researcher:
      model: efficient
      effort: high
```

Resolution order:

1. **Base profile:** series `profile` if set, otherwise press `profile` (default
   `balanced`).
2. **Stage fields:** press stage fields, then series stage fields.
3. **`required`:** press-wide -> press stage -> series-wide -> series stage.

Inspect resolved directives for any series:

```sh
nb production-policy --repo . --series <id>
```

## Billing and observed workload

Production policy selects models; it never estimates cost or subscription share.
Check your provider's usage report after a baseline run for subscriptions, or
calculate metered API spend from actual model rates (including repair rounds and
orchestrator overhead).

**Single requested article** (`economy` profile, `writer` and `editor` on
`capable`, coach and researcher in parallel, before repairs): ~45 minutes total
agent time (coach ~6m / 94k tokens, researcher ~9m / 135k, writer ~13m / 167k,
editor ~11m / 157k).

**Scheduled run of 5–7 parallel articles** (45–90 minutes wall-clock):

| Work                       | Observed time | Observed tokens |
| -------------------------- | ------------- | --------------- |
| Initial orchestration      | 10–15 minutes | ~100k           |
| Researcher, per article    | 10–15 minutes | 100k–200k       |
| Writing coach, per article | 5–10 minutes  | 50k–100k        |
| Writer, per article        | 15–25 minutes | 150k–350k       |
| Editor, per article        | 5–15 minutes  | 150k–250k       |

These figures are observations, not guarantees; repair rounds and ongoing
orchestration add work.

## Reducing usage

1. **Pin a voice guide** on settled series to skip `writing-coach` completely
   (saving ~5–10 min and 50k–100k tokens per article). See
   [Series reference](series.md#pinning-a-voice-guide).
2. **Tighten commissions and series scope** so discovery and verification spend
   fewer turns (current-events beats require heavier verification).
3. **Match models to bottlenecks** using paper-wide defaults and per-series
   overrides (e.g., stronger researcher on news, stronger writer on essays).
4. **Lower cadence or series count.** Parallelism reduces wall-clock time, not
   total token consumption.
