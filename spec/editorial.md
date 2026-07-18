# The house floor

The editorial standard every article meets, whatever its template. It composes under
`PROTOCOL.md` and over the series, tag, and item prompts. A paper's own voice in
`press/editorial.md` composes immediately after this file and specializes it.

The floor is prescriptive on purpose. Its job is to make the default professional:
research-grade writing. It reads in two registers.

- **Standards a paper cannot loosen.** The quality bar below: sourced claims, teach don't
  summarize, earned analysis, and prose free of fluff, slop, and run-ons.
- **Defaults a paper may override.** Everything that is taste rather than quality:
  register, formality, the assumed reader and that reader's background, how far to
  press a judgment, and any other choice of that kind. These belong to
  `press/editorial.md` and the series prompts. The floor sets the quality of those
  choices, never the choices themselves.

The floor does not legislate trivia: no house-wide rule on the Oxford comma. Be
consistent within a piece.

## Teach, don't summarize

The reader finishes knowing how to think about the topic. Each
section spends what the last one taught. A section the reader could have read first is in
the wrong place. Cut any sentence that adds nothing new. Prefer concrete detail over
abstraction. Define each term of art the declared reader does not hold
in the sentence where it first appears. Assume the rest. Ground abstract claims in a
worked example.

The declared reader centers the paper: the profile chooses what to cover and when, and
what background to assume. Write each piece for the natural audience around that center.
A paper declaring a new parent gets articles any parent could be handed. A declared
practitioner gets pieces worth forwarding to a colleague. Narrowing a desk to
the reader personally takes an explicit ask in `press/editorial.md` or the series prompt.

## Report and analyze

Report what is true and analyze what it means. Hold the analysis to the same bar as the
reporting. Analysis must be earned: grounded in the cited evidence, its reasoning shown.
Keep three things distinct: reported fact, estimate, and synthesis. Never write that
someone hinted, implied, or signalled. That is the writer's guess wearing attribution.
Synthesis with a point of view is welcome. Cut unsupported opinion. How hard to
press a view is the paper's call, and a press that wants opinion may have a
column or an editorial desk. The floor bans the unearned verdict, never the
verdict: an opinion meets the same bar as any analysis, cited, reasoned, shown.

## Citations

- Every claim the argument rests on carries an inline citation linking to a source entry.
- Prefer primary sources: the document that owns the claim, whatever form the document
  takes. Secondary reporting is acceptable for context. Contested figures need a
  primary source.
- Never fabricate, pad, or decorate citations. If you cannot source a claim, cut it or
  state the uncertainty plainly.
- Cite only what you have read. Open the source, find the passage that supports the
  specific claim, and cite that. Its URL must resolve.
- On contested questions, steelman the opposing views before you weigh them.

## Numbers

Concrete figures beat vague magnitudes. Ranges with sources beat false precision. Give
every number a comparison the reader already knows. Say plainly what is unknown.

## Prose

The register is a serious paper, not a feed. Some habits are always cut. They are the
tells of slop.

- **Fluff.** Filler openings ("In today's fast-paced world"), empty connectives,
  throat-clearing ("As you might know"), and openers that lecture: Note, Consider,
  Imagine. If a sentence carries no information, it goes.
- **Slop.** The median AI read: smooth, hedged, reaching for the generic phrasing. Write
  the specific word: the drug's name, not "a treatment"; 40 nanometers, not "tiny".
  Commit where the evidence lets you. Anchor the prose to how the best writers on the
  subject write, not to the average of everything written about it.
- **Run-ons.** A sentence that piles clause on clause until the reader loses the thread
  gets broken. A semicolon chain is the same failure wearing punctuation, and often an
  em-dash swap: write the period, or write the list. Let the verbs carry the weight.
  Vary length for rhythm; a long sentence in control is craft.
- **Manufactured punchlines.** Cut any sentence engineered to sound quotable while
  carrying little ("that's the whole point", "here's the kicker", "the catch is"). The
  "X is the whole Y" family belongs here too ("that identity is the whole guarantee",
  "where it is sent is the whole argument"): a sentence that announces its own stakes has
  stopped making the argument and started grading it. A closer or section opener reused
  as a formula across articles is the same failure. So is a house catchphrase.
- **Hedged contrast.** The "X is not Y; it is Z" mold and its softer cousins ("not X but
  Y", "rather than") stay only when the misconception they correct is real and named, and
  fall wherever the "not" clause is a strawman the sentence invented. One or two earned
  contrasts per piece is the ceiling.
- **Self-reference.** The piece never narrates itself or its newsroom ("this dossier",
  "what follows"), never addresses its audience, and never mentions a reader at all
  ("a reader will notice", "where a reader's scrutiny belongs"). Report the subject;
  what deserves notice is shown by making it noticeable.
- **Banned terms.** `spec/banned-terms.yaml` lists the words and marks the corpus has
  ruled out and how many uses each may keep. A press extends or adjusts the list in
  `press/banned-terms.yaml`, and the proof counts every article against the merged list.
  When a count runs over, rewrite rather than substitute: a synonym carries the same
  vagueness, and repunctuating an em-dash keeps the fluff the dash was carrying. Delete
  first, then rewrite what remains. An em-dash still earns its place for a real aside or
  a sharp break. The ceiling exists for the reflex.

Break any rule here sooner than write a sentence no honest voice would say aloud.

## Form

Each template's identity sets its own form: paragraph length, how the dek reads, how the
piece closes. A press may shadow them. The floor holds those choices to a standard. Keep
the writing easy to follow. End on the conclusion the argument built. Skip the generic
moral. Let the teaching and the citations equip the reader to go further.

## Charts

Use a chart when a trend or comparison is the point. Charts are PNGs
rendered from the committed `chart-N.py` script beside the article
(docs/charts.md), never hand-drawn images or script blocks. Keep them honest:
label axes, note a non-linear scale, and cite the data source in the caption.
