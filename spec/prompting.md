# Prompting

Every layer an article-making agent reads is a prompt: the orchestrator package,
spec files, editorial-role skills, template identities, furniture catalog, and
prompts a press writes for its series. Their prose trains the writer's prose. A
rambling layer produces rambling articles. A layer written as a list produces
articles that treat the list as the complete allowed set. Keep slogans out of
every prompt surface.

This file is the standard every prompt surface is written against, and
`spec/slop.md` binds prompt prose exactly as it binds an article. A prompt is
reread on every run, so slop written into one reaches every article it governs.
The user assistant applies both to every prompt it writes or edits, and engine
contributors apply them to the shipped layers.

## What a prompt carries

A prompt carries only what the engine cannot know. Config is not prose:
`series.yaml`, the template manifest, and the furniture catalogs are read
directly, so a rule restated in prose drifts from the rule it copies and carries
no force. Say each thing once in its owning file and reference the file. The
editorial judgment no schema holds is what belongs in prose: the beat, the
angle, the genre, the standard a source must clear, what a series refuses to do.

## Sentences

Open concrete. The first sentence states the prompt's job or the rule's
consequence, never a framing abstraction. "A lesson teaches one subject to a
reader who is new to it" names the job in its first six words, and is the
opening to write. "The conceptual equipment for reading AI" names nothing and
asks the reader to supply it.

Write flat declaratives that carry consequences. Vary the rhythm. A prompt whose
sentences all land the same beat teaches the writer that beat. Name a rule or a
test after what it does ("the delete test"), never after a virtue ("the
earns-its-place test"), because a name that sounds good invites argument about
the name. No fragment openers.

Prefer the period. An em-dash used as a connective, a semicolon chain, and a
stacked-colon sentence are all run-ons held together by punctuation. Write the
period, or write the list.

Name the actual thing. Container nouns (machinery, landscape, space, equipment,
dynamics) gesture at a subject instead of stating it. A sentence that presumes a
frame the reader does not hold compresses nothing. Anchor every claim in the
subject itself.

## Lists

A list of examples reads as a closed menu: the writer treats it as the complete
allowed set. For territory (beats, angles, subjects), state the principle and
frame any examples as open ground: "anything that", "wherever", "whoever holds
the lever: a regulator, a court, a standards body". For requirements (a fixed
analysis contract, anchor sections), a bounded list is correct. If a list could
be read either way, reword it or delete it.

## References and labels

Link a file when the reader should open it. Name it in backticks when the
sentence is about the file itself: something to edit, create, or paste. A
backtick path is repo-rooted. A layer that gets composed into
`editorial-direction.md` never carries a relative link, because the composed
file resolves links from a different directory. Give every link target a
directory component (`./setup.md`, never `setup.md`) so same-named files stay
unambiguous.

Never name the reader in a series prompt. The audience lives in
`press/editorial.md`. Prompt rules are stated about the article, the series, or
the subject.

Keep planning labels in working files. Published prose should say what happened,
what the evidence shows, or what is disputed, not repeat the label used to
organize the work.

Write prompts as directions, not sample article sentences. Topic-selection rules
and checks on the finished draft are directions too. Remove any line a writer
could paste into an article.

## Process

Before polishing a paragraph, say what it is for. A paragraph with no answer
gets deleted, not improved. A paragraph with a real job that reads badly gets
rederived from its goals, not edited sentence by sentence. Reread the finished
prompt as the writer will: anything it could copy verbatim into an article is a
defect the editor will have to catch later.
