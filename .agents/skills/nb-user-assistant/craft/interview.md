# Dynamic editorial interview

An interview discovers a coherent paper. It does not collect fields. Maintain a
live model of what is known, uncertain, and contradictory. Ask one compact
question or one related cluster at a time, using the user's previous answer to
choose the next move.

## Required outcomes

Reach confidence on purpose, reader, territory, evidence standard, voice,
recurring series, reading rhythm, how visual the paper should be, how much
production usage the user can sustain, and first-week coherence. These are
goals, not a prescribed order. Skip what the user already made concrete and
revisit an apparent answer when later evidence contradicts it.

When the desired evidence standard depends on sources behind a login or paywall,
surface the constraint immediately: scheduled research reads the public web, and
a source the user is entitled to read but must authenticate for currently
requires significant harness-specific setup, tracked as upstream issue #127.
Settle a source standard the runtime can actually meet, and treat authenticated
access as a separate project the user opts into.

## Settle sustainable production usage

Read `docs/reference/production.md` before a budget conversation. Learn how the
scheduled runtime is billed and what usage the user can sustain, then translate
that tolerance into cadence, series scope, and production policy. When an answer
depends on measurement, use the provider report from a normal run.

Ask what the user pays for and what ceiling they would notice hitting: the
subscription tier or metered account behind the automation, and whether a run
that consumed most of a week's allowance would be a problem. A twenty dollar
monthly plan does not run a quality profile across six nightly sections. Ask
now, rather than finding out in week two after the bill.

Three levers act on different things, so settle them separately. Cadence and
section count decide how many articles exist. A production profile and its
per-stage tiers decide what each role costs. A pinned voice guide removes the
writing coach for a section whose sound has settled, the only lever that drops a
role invocation instead of making one cheaper. Write a pinned guide against the
standard in `.agents/skills/nb-writing-coach/SKILL.md`.

## Interview loop

1. **Discover.** Ask for the desired reader experience and the frustration or
   curiosity behind the paper. Ask for reading habits, not demographic labels.
2. **Form hypotheses.** Offer a small number of distinct interpretations. Name
   the tradeoff in each so the user can react to something real.
3. **Test examples.** Generate representative subjects, headlines, evidence
   situations, and article shapes. Ask which feel inevitable, surprising, or
   wrong and why.
4. **Test counterexamples.** Present plausible work the paper should reject.
   Boundaries sharpen a beat and expose whether two proposed series overlap.
5. **Synthesize.** Reflect the editorial principle in the user's language,
   separating settled choices from open ones. Invite correction of the model,
   not approval of your eloquence.
6. **Simulate.** Lay out a credible first week. Check variety, cumulative
   reading load, repeated structures, source feasibility, and whether the paper
   fulfills its stated purpose.
7. **Approve.** Ask decisions only on remaining consequential alternatives.
   Approval covers the editorial specification, not hidden publication or
   account mutations.

## Question quality

A good question makes two plausible futures distinguishable. "Who is the
audience?" invites a label. "Should an engineer already building retrieval
systems learn more from this paper than a product leader deciding whether to
fund one? What would each consider wasted space?" exposes the knowledge and
decision boundary.

Do not stack ten unrelated questions, force multiple-choice answers when the
space is not understood, or ask the user to restate repository facts. When their
answer is abstract, test it with an example before requesting a better
adjective.

The interview is complete when you can predict how the user will judge a new
article idea and explain why each proposed series belongs in the same paper.
