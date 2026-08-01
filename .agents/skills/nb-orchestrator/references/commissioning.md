# Commissioning

Plan the complete authorized work set before launching an editorial role. For
scheduled publication, this is where the orchestrator turns deterministic duty
into article-specific judgment. For manual publication, the configured article
is already the authorized work set.

## Read only the governing context

Read the layers that apply to the selected article in this order:

1. `spec/editorial.md` and `spec/headlines.md`;
2. `press/editorial.md`, when present;
3. the selected template's manifest, skeleton, identity, and furniture;
4. the series prompt, declared tag fragments in order, and selected item.

Later layers specialize earlier ones; they do not silently waive them. Use the
generated `editorial-direction.md` as the exact composed record supplied to
roles instead of paraphrasing these layers.

Start history work with targeted `nb history` queries. Use
`nb history --show <series>/<slug>` or a raw article only when a concrete
commissioning question requires it. Record relevant prior coverage and recent
openers, section shapes, furniture, and conclusions as habits not to inherit
automatically. Publication history informs context; it is never a template.

## Plan the articles together

Prevent both editorial repetition—a topic, claim, or angle already covered—and
structural repetition inherited from prior articles. Record neighboring
articles from this run so every piece adds distinct value and the articles read
as one paper.

Choose a subject, template, sources, tags, and production policy that fit the
series. Complete every commission before any role begins so concurrent articles
remain coherent and non-redundant.

## Initialize each article

Resolve the selected series with `nb source-policy` and
`nb production-policy`. Honor required model selections and record the actual
model and effort used for each role.

Initialize the chosen series, slug, template, and tags with:

```text
nb start-article <series> <slug> --template <template> \
  --workspace .nb-work/<series>/<slug> [--tag <tag> ...]
```

The command owns the initial article, generated editorial direction, effective
template contract, runtime assets, and applicable furniture catalogs. Do not
edit generated context or recreate it in a brief. Keep later role invocations
numbered `02`, `03`, and onward without overwriting earlier work.

## Write the record

Write `commission.md` with the assignment, angle, intended reader, mode,
template, source obligations, starting sources, relevant history, structures
not to repeat, neighboring articles, output paths, actual harness and model
choices, and the article's required contribution. Write directions, never
sample article sentences.

Create each numbered role brief only when its inputs exist. Name exact inputs,
outputs, permitted changes, useful `nb` commands, unresolved decisions, and the
owner of anything missing. Preserve fixed labels or markup where necessary,
but do not restate configuration or ask a role to rediscover it.
