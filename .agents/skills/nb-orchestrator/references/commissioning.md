# Commissioning

Plan the complete authorized work set before launching an editorial role. For
scheduled publication, this is where the orchestrator turns deterministic duty
into article-specific judgment. For manual publication, the configured article
is already the authorized work set.

## Read only the governing context

Read the layers that apply to the selected article in this order:

1. `spec/editorial.md`, `spec/slop.md`, and `spec/headlines.md`
2. `press/editorial.md`, when present
3. the selected template's manifest, skeleton, identity, and furniture
4. the series prompt, declared tag fragments in order, and selected item

Later layers specialize earlier ones. They do not silently waive them. Never
paraphrase these layers: supply the generated `editorial-direction.md` itself,
to exactly the roles production and delivery names as its recipients.

Start history work with targeted `nb history` queries. Use
`nb history --structure <series>/<slug>` for a recent article's outline and
furniture, and `--show` or a raw article only when a concrete commissioning
question requires the prose itself. Record relevant prior coverage and recent
openers, conclusions, and outline shapes as habits not to inherit automatically.
Read the prose of the last few pieces too, not only their structure, and record
any phrasing that has started recurring. A catchphrase is a phrase, so structure
notes cannot show one, and the editor cannot catch what the notes do not carry.
Never record template-required furniture or fixed labels as habits to avoid: the
proof requires them, and only optional choices repeat. Publication history
informs context. It is never a template.

## Plan the articles together

Prevent editorial repetition, meaning a topic, claim, or angle already covered.
Prevent structural repetition inherited from prior articles. Record neighboring
articles from this run so every piece adds distinct value and the articles read
as one paper.

Choose a subject, template, sources, tags, and production policy that fit the
series. Complete every commission before any role begins so concurrent articles
remain coherent and non-redundant.

## Initialize each article

Resolve the selected series with `nb source-policy` and `nb production-policy`.
A `required` model or effort directive is never yours to trade down by judgment.
If the runtime cannot honor or verify it, use the closest available option and
record the deviation in the commission. Record the actual model and effort used
for each role.

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

Write `commission.md` as the record of every decision production needs. A reader
should reconstruct the assignment, its boundaries, and its required contribution
without the chat. Record the actual harness and model choices. Write directions,
never sample article sentences. A commission and a brief meet `spec/slop.md`
like every other file a role writes.

Create each numbered role brief only when its inputs exist. The coach and
researcher briefs have no upstream outputs, so write them with the commissions
and launch every article's opening roles in one burst.

A brief that names its exact inputs and its output path is complete. Write every
brief in this shape:

```text
# <role> brief: <series>/<slug> (<NN>)

Inputs: the named files, one line each, with a clarifying phrase only where
        a file's job is not obvious from its name
Output: <path>
Proof:  the exact nb check command        (writer and editor briefs only)

Nothing else, unless a decision the inputs do not carry needs stating
(e.g., a run-environment caveat, recent shapes to break, this round's focus).
```

Never restate what a named input carries: the role reads its inputs itself, and
a digest drifts from the file it copies. The role's own risk surface, method,
and standards are the role's to derive from its skill and inputs.
