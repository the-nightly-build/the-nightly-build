# Create a paper

Read [interview craft](../craft/interview.md) and
[prompt authoring](../craft/prompt-authoring.md). Load
[furniture design](../craft/furniture-design.md) or
[template design](../craft/template-design.md) only when the concept calls for
custom presentation or an enforceable new structure.

## Discover before configuring

Inspect `examples/`, the current `press/` if one exists, and the public docs.
Conduct a contextual interview, not a field-by-field questionnaire. Establish
these outcomes:

- the paper's purpose and the change it should make in the reader;
- a concrete reader model and reading situation;
- series with distinct territory, exclusions, evidence standards, and cadence;
- an editorial voice grounded in examples and anti-examples;
- the first week's range, coherence, and likely failure modes;
- the user's review appetite, budget posture, and autopublish comfort.

Ask from hypotheses. If the user wants a daily paper on AI, propose two or
three meaningfully different editorial shapes and test them with candidate
headlines. Use their reactions to learn the underlying standard.

## Synthesize and pressure-test

Present a compact press proposal in the user's language. For each series, give
its job, boundary, representative article, counterexample, mode, cadence, and
template choice. Simulate a first week. Look for topic collisions, repetitive
article geometry, impossible evidence requirements, and a reading load the
user will not sustain.

Do not turn approval into a vague "looks good?" Ask the user to decide the few
open choices that materially change the paper. Revise the concept until its
parts cohere.

## Implement the approved press

Write the smallest `press/` that expresses the approved concept. Keep schema in
YAML and editorial judgment in prose. Apply `spec/prompting.md` to
`editorial.md`, every `prompt.md`, item prompt, template identity, and custom
catalog entry. Do not duplicate cadence, source bands, template sections, or
other config inside prompts.

Run `nb validate`, build a preview where presentation changed, and show the
user the material consequences. Commit the press configuration separately from
any Article PR. Then return to [setup](setup.md) for the scheduled test article.
