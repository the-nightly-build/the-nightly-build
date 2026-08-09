# Editorial standard

This is the editorial standard every article meets, whatever its template.

The standard is prescriptive on purpose. Its job is to make the default
professional: research-grade writing. It has two parts.

- **Standards a paper cannot loosen.** Sourced claims, teach don't summarize,
  earned analysis, and the prose failures `spec/slop.md` rules out. A template
  or a press may allow one of those prose failures where its own work needs it.
  `spec/slop.md` bans self-reference, for instance, and the lesson template
  allows its two bookend cards to address the reader. Say which failure is
  allowed and where. Nothing loosens sourced claims, teaching, or earned
  analysis.
- **Defaults a paper may override.** Everything that is taste rather than
  quality: register, formality, the assumed reader and that reader's background,
  how far to press a judgment, and any other choice of that kind. These belong
  to `press/editorial.md` and the series prompts. This standard sets the quality
  of those choices, never the choices themselves.

This file bans failures of writing. How a paper sounds is its own to set in
`press/editorial.md`.

The standard does not legislate trivia: no paper-wide rule on the Oxford comma.
Be consistent within a piece.

## Teach, don't summarize

The reader finishes knowing how to think about the topic. Each section builds on
what the last one taught. A section that spends nothing an earlier one taught is
in the wrong place. Cut any sentence that adds nothing new. Define each term of
art the declared reader does not hold in the sentence where it first appears.
Assume the rest. Ground abstract claims in a worked example.

The declared reader centers the paper: the profile chooses what to cover and
when, and what background to assume. Write each piece for the natural audience
around that center. A paper declaring a new parent gets articles any parent
could be handed. A declared practitioner gets pieces worth forwarding to a
colleague. Narrowing a series to the reader personally takes an explicit ask in
`press/editorial.md` or the series prompt.

## Report and analyze

Report what is true and analyze what it means. Hold the analysis to the same bar
as the reporting. Analysis must be earned: grounded in the cited evidence, its
reasoning shown. Keep three things distinct: reported fact, estimate, and
synthesis. Never write that someone hinted, implied, or signalled. That is the
writer's guess presented as attribution. Synthesis with a point of view is
welcome. Cut unsupported opinion. How hard to press a view is the paper's call,
and a press that wants opinion may have a column or an opinion series. A verdict
is welcome once it is earned, and it meets the same bar as any analysis: cited,
reasoned, shown.

## Citations

- Every claim the argument rests on carries an inline citation linking to a
  source entry.
- Prefer primary sources: the document that owns the claim, whatever form the
  document takes. Secondary reporting is acceptable for context. Contested
  figures need a primary source.
- Never fabricate, pad, or decorate citations. If you cannot source a claim, cut
  it or state the uncertainty plainly.
- Cite only what you have read. Open the source, find the passage that supports
  the specific claim, and cite that. Its URL must resolve.
- On contested questions, steelman the opposing views before you weigh them.

## Numbers

Give the figure, not the magnitude, and a sourced range rather than a precision
the source does not support. Anchor a figure the reader cannot scale on their
own to a comparison they already hold. Say plainly what is unknown.

## Clarity

An article is understood on the first read or it has failed. Abstraction is the
usual reason it fails: an abstract noun the article has not built up asks the
reader to carry something unstated, and a weak argument is easy to hide inside
one. Prefer the concrete. Reach for an abstraction only when the abstraction
itself is the subject, and build it up like any other term.

Name a thing one way and keep that name. Once a term is set, reuse it exactly. A
synonym reached for variety reads as a new thing.

Default to short, single-purpose sentences, and vary their length. A long
sentence under control is good writing, and a page of same-length declaratives
is monotonous. If a sentence can be misread, rewrite it rather than trust the
next one to rescue it. Shorten by cutting, never by packing ideas denser. If a
paragraph holds more ideas than it has sentences, it is no longer explaining
them.

## Prose

The house register is a serious paper, not a feed. It is a default, and a press
may move it. `spec/slop.md` is the standard for prose that reads as
machine-written. It binds every article at every register.

Register and formality belong to `press/editorial.md`, which a paper writes for
itself, and to the article's voice guide, which sets how one piece should sound.
A paper that wants to be funny, loose, or direct with its reader says so there,
and every article inherits it. No form is forbidden for being expressive. What
gets cut is writing that fails `spec/slop.md`, at whatever register the paper
has chosen.

If a rule in this Prose section would produce a sentence you would not say
aloud, break that rule. Sourcing, teaching, and earned analysis are not subject
to this.

## Punctuation

Reach for the plainest mark that does the job. When two marks would both work,
the plainer one is right, and when in doubt the period is the default.

- **Period.** The default. Two thoughts are two sentences. Most em-dashes,
  semicolons, and colons in a draft belong where a period would do.
- **Comma.** Joins within a single thought, and sets off a short aside. It is
  not a splice: two independent clauses joined by a comma alone are two
  sentences.
- **Colon.** Introduces what the clause before it promises, a list or a
  definition or the payoff. The clause before it stands on its own. It is not a
  general connector between two thoughts.
- **Semicolon.** Rare. Two independent clauses so tightly bound that a period
  would over-separate them. Do not chain them, do not use one to patch a comma
  splice, and do not use one to extend a run-on.
- **Em-dash.** A real interruption or a sharp aside, and never a general
  connective or a stand-in for a semicolon. When you delete one, the fix is
  usually the period the thought wanted rather than another mark in its place.
  `spec/banned-terms.yaml` sets the count.
- **Parentheses.** A true aside the sentence survives without. If the sentence
  needs what is inside them, it is not an aside, so fold it back in.

A press extends this section for its own paper. It does not loosen it.

## Form

Each template's identity sets its own form: paragraph length, how the dek reads,
how the piece closes. A press may shadow them. This file holds those choices to
a standard. Keep the writing easy to follow. End on the conclusion the argument
built. Skip the generic moral. Let the teaching and the citations equip the
reader to go further.

### Literal strings

Use inline `<code>` only when the reader must preserve a string's exact
spelling: something they could type, paste, execute, match, or distinguish
character-for-character. It is not technical emphasis. Ordinary terms, product
names, model names, and prose do not take it. Neither does every repeat of a
literal once the sentence has established it. When several tokens need
comparison, give them a table or a code listing instead of turning a paragraph
into labels.

An article's form comes only from its template and its own content. Reading the
published library informs content and context: what a series has covered, what
not to repeat. It never informs form. A structure in an older piece records what
the format was at the time. It does not say what the format should be now. A
template that has moved on leaves its old structure in the back-catalog, and
copying that structure forward is how a retired section reappears where it no
longer belongs.

## Charts

Use a chart when a trend or comparison is the point. Charts are PNGs rendered
from the committed `chart-N.py` script beside the article (spec/charts.md),
never hand-drawn images or script blocks. Keep them honest: label axes, note a
non-linear scale, and cite the data source in the caption.
