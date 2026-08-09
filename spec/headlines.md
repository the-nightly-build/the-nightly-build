# Headlines, deks, and section headings

This file defines the standard for the three lines a reader meets first. The
prose rules of `spec/editorial.md` and `spec/slop.md` apply here word for word.
One test governs all three: the line commits to something the piece establishes.
Every tell named below fails that test.

## The headline

Subject, verb, and the surprise in the first words. Put the concrete news in the
opening words, ahead of every qualifier, because a scanning reader may not reach
the rest.

- **State the finding, with its actors named.** "Steve Ballmer was an underrated
  CEO" (Dan Luu) and "Ghostty Is Now Non-Profit" (Mitchell Hashimoto) are claims
  their pieces defend. A specific record beats a scope: "A decade of major cache
  incidents at Twitter" (Luu again) promises exactly what it delivers.
- **Let a fresh verb carry it, in the present tense for events.** The classic
  headline pair: "Students applaud later start times" reports the event from the
  side that felt it. "Officials approve schedule change" reports the same event
  as paperwork.
- **Numbers earn their spot when they are the story.** "Building a World Map
  with only 500 bytes" (Simon Willison): the figure is the surprise, so it sits
  in the headline.
- **Ask a question only when the piece answers it.** "Why is DNS still hard to
  learn?" (Julia Evans) is honest because the post commits to an answer.
  Betteridge's law names the other kind: a headline ending in a question mark so
  the writer never has to stand behind a claim.
- **The colon subtitle is a machine tell.** "X: How Y Changed Z" and "Company:
  The Adjective Noun and the Adjective Noun" are templates any topic drops into.
  A colon survives only when both halves inform, as in "git branches: intuition
  & reality" (Evans). When the right half is atmosphere, cut the colon and write
  the claim.
- **A triad of paired adjectives ("Faster Models, Firmer Rules, Tighter Supply")
  only sounds comprehensive.** Pick the one development that matters most and
  say what happened to it. The other two get their own sentences in the dek or
  the body.
- **Anchor wit in the story's own nouns, with a plain dek beside it.** The
  Economist headlined a meat-producer merger "A steak in the market" and could
  afford to, because the dek under it stated the argument plainly. Wordplay only
  works on the story's own nouns, and no pun substitutes for the dek.

All of the above, at once: a piece that found two chip CEOs reading the same
market data and reaching opposite conclusions could headline itself "The Chip
Curtain: Slowdown or Surrender?" and hedge twice, once with the borrowed
metaphor and once with the question. It found something better. Say it: "Two
CEOs read the same chip data and reach opposite conclusions."

## The dek

The dek adds what the headline left out and never restates it. The headline
commits to the surprise. The dek supplies the who, the what, and the one detail
that makes the piece unmistakable for any other. "The very modern corporate tale
of what happens when a top executive at a $6 billion public company can't stop
tweeting" works because the dollar figure and the verb do the identifying. "The
fascinating tale of a San Francisco-based executive" decorates without
informing. One lean sentence, a stance and not a topic, and no detail that pulls
attention from the thesis.

`spec/slop.md` bans the negative-parallelism reflex in body prose, and the dek
gets no exemption. Three dek molds carry it: the semicolon reversal ("X did A; Y
refuses B"), the suspended question ("...and the real question is whether"), and
the comma triad, three clauses joined by commas and closed with "and" ("The
trial cut the rate from 14 in 100 to 2, the general-population evidence is
thinner, and the benefit depends on sustained feeding"). Cut them on sight. Even
a good mold looks stamped once it recurs, so check the recent library's deks
before settling on one.

## Section headings

Each heading is a step of the argument, written in the piece's own nouns. A
reader skimming only the headings should be able to reconstruct what the piece
argues and in what order. When a heading would fit any article on any subject,
it is scaffolding, and scaffolding slots ("Background", "Implications", "The
Road Ahead", "Key Takeaways") are the machine tell. The `data-nb-section` label
mirrors its heading, short and concrete. Fixed headings a template mandates
("Sources") are furniture and exempt. Every heading the writer names is held to
this standard.

Headings repeat the same way deks do. A paper whose headings keep joining two
clauses with a comma and "and" ("The scale, and what it is compounding against")
looks stamped however sharp each line is. Vary how they are built, and check the
recent library's headings as you checked its deks.
