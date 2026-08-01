# Prompting

Every layer an article-making agent reads is a prompt: the orchestrator
package, spec files, editorial-role skills, template identities, furniture
catalog, and prompts a press writes for its series. Their prose trains the
writer's prose. A layer that rambles produces articles that ramble, and a
layer that lists produces articles that treat the list as the whole world.
This file is the standard every prompt surface is written against. The user
assistant applies it to every prompt it writes or edits, and engine
contributors apply it to the shipped layers.

## What a prompt carries

A prompt carries only what the engine cannot know. Config is not prose:
`series.yaml`, the template manifest, and the furniture catalogs are read
directly, so a rule restated in prose drifts from the rule it copies and
carries no force. Say each thing once in its owning file and reference the
file. The editorial judgment no schema holds is what belongs in prose: the
beat, the angle, the genre, the standard a source must clear, what a series
refuses to do.

## Sentences

Open concrete. The first sentence states the prompt's job or the rule's
consequence, never a framing abstraction. "A performance number arrives with
its baseline" instructs; "the conceptual equipment for reading AI" decorates.

Write flat declaratives that carry consequences. Vary the rhythm; a prompt
whose every sentence lands the same aphoristic beat reads as performance,
and the writer learns to perform. No fragment openers.

Prefer the period. An em-dash used as a connective, a semicolon chain, or a
stacked-colon sentence is a run-on wearing punctuation. Write the period, or
write the list.

Name the actual thing. Container nouns (machinery, landscape, space,
equipment, dynamics) gesture at a subject instead of stating it. A sentence
that presumes an unstated frame confuses instead of compressing; anchor
every claim in the subject itself.

## Lists

A list of examples reads as a closed menu: the writer treats it as the
complete allowed set. For territory (beats, angles, subjects), state the
principle and frame any examples as open ground: "anything that", "wherever",
"whoever holds the lever: a regulator, a court, a standards body". For
requirements (a fixed analysis contract, anchor sections), a bounded list is
correct. If a list could be read either way, reword it or delete it.

## References and labels

Never name the reader in a series prompt. The audience lives in
`press/editorial.md`; prompt rules are stated about the article, the series,
or the subject.

Keep planning labels in working files. Published prose should say what happened,
what the evidence shows, or what is disputed, not repeat the label used to
organize the work.

Write prompts as directions, not sample article sentences. Topic-selection
rules and checks on the finished draft are directions too. Remove any line a
writer could paste into an article.

## Process

Before polishing a paragraph, say what it is for. A paragraph with no
answer gets deleted, not improved. A paragraph with a real job that reads
badly gets rederived from its goals, not edited sentence by sentence.
Reread the finished prompt as the writer will: anything it could copy
verbatim into an article is a defect the editor will have to catch later.
