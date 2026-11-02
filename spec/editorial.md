# Editorial standard

Every article meets this standard, whatever its template and whatever the press.

The first section is about writing, and it applies to everything. The second is
about what this paper does, and an owner may move any of it in
`press/editorial.md` except correctness. Register, formality, and how hard to
press a judgment are an owner's to set in `press/editorial.md` and in the
article's voice guide. Nothing here sets them.

`spec/slop.md` lists the prose failures, and they apply at every register. An
owner may allow one of them in a template or a press, and has to say which one
and where.

Nothing here covers trivia. There is no paper-wide position on the Oxford comma.
Be consistent within a piece.

## The principles of great writing

**It is clear.** Clear writing is easy to understand, and that has little to do
with how hard the words are. Use the exact word. An approximate one leaves a
reader guessing which of several things you meant, and a precise one settles it.
The subject can be difficult without the sentence being difficult. Use one word
for each idea and keep using it. Reach for a synonym and whoever reads it looks
for a second idea.

**It teaches.** Someone who finishes the piece can reason about the subject and
not only recall it. Order it so each part can be used where it appears. Define a
technical term where it first appears and assume the rest. Carry an abstract
claim down to an instance before moving on. Order the piece so each section uses
what you set up earlier.

**It stands on its own.** Someone arriving from a link has read nothing else.
Introduce every term and event inside the article. A lesson in a running course
is the exception, because it may rely on the earlier lessons it links.

**It does original work.** Do something with the sources that the sources did
not do. Say in one sentence what that was. If you cannot write that sentence,
the article is not finished.

## The paper's principles

Correctness is the one nothing loosens. An owner who wants a different bar on
the others says so in `press/editorial.md`.

**It is correct.** Cite what could be doubted and the claims without which the
piece does not work. Common ground needs no citation. Open the source and find
the passage before citing it, and record the section, page or paragraph, so a
reader lands on the words and not on a homepage. Cite the document that made a
claim ahead of any article about it, and where a figure is disputed cite the
document that owns it. If you cannot source a claim, cut it or state the
uncertainty plainly. Never fabricate, pad or decorate a citation.

**It says what the reporting supports.** Say it without hedging. Withholding a
conclusion you can show is its own distortion. Where the reporting does not
reach one, say that, and separate what is established from what is judged. Show
the reasoning from the evidence to the conclusion. Never write that someone
hinted, implied or signalled, which attributes your guess to them.

**It is fair to a view it disagrees with.** State a view in the words of someone
who holds it before taking it apart. Beating a weak version of the opposition
tests nothing.

**It is written for more than one person.** Use the profile in
`press/editorial.md` to decide what to cover and what background to assume, then
write each piece for the audience around that profile. Where the profile is a
new parent, write articles any parent could be handed. Narrow a series to one
person only where `press/editorial.md` or the series prompt says to.

## Numbers

Give the figure and not the magnitude. Give the range a source gives and no more
precision than that. Where nobody could scale a figure alone, put it beside one
they already hold. Say plainly what nobody knows.

## Punctuation

Use the plainest mark that works. Where two marks would both work, use the
plainer one, and where you are unsure use the period.

- **Period.** Two thoughts are two sentences. In most drafts, a period belongs
  where the em-dash, the semicolon or the colon is.
- **Comma.** Joins inside one thought, and sets off a short aside. Two
  independent clauses joined by a comma alone are two sentences.
- **Colon.** Introduces a list, a definition, or the payoff. The clause in front
  of it stands on its own.
- **Semicolon.** Rare. Two independent clauses close enough that a period would
  be too much between them. Do not chain them and do not patch a comma splice
  with one.
- **Em-dash.** A real interruption or a sharp aside. When you delete one, a
  period is usually what belongs there. `spec/banned-terms.yaml` sets the count.
- **Parentheses.** A true aside. Take them out and the sentence still says what
  it said. If you need what is inside them, fold it back in.

An owner may extend this section and may not loosen it.

## Form

Each template's identity specifies its own form: paragraph length, how the dek
reads, how the piece closes. End on the conclusion you built. Skip the generic
moral.

Read the published library for what a series has covered and what not to repeat.
Do not read it for the form. An older piece was written to the format of its
time, and if you copy that structure forward you bring back a section somebody
retired.

### Literal strings

Use inline `<code>` only where somebody must preserve a string's exact spelling:
something they could type, paste, execute or match character for character.
Ordinary terms, product names and model names do not take it, and neither does a
literal you have already established. Where several tokens need comparison, give
them a table or a code listing.

## Charts

Use a chart where a trend or a comparison is the point. Charts are PNGs rendered
from the committed `chart-N.py` script beside the article (`spec/charts.md`).
Label the axes, note a non-linear scale, and cite the data source in the
caption.

## One exception

If following a rule in this file would give you a sentence you would not say
aloud, break the rule. Correctness, teaching and sourcing stay.
