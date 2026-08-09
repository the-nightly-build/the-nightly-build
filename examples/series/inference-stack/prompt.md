# The Inference Stack

Appraise, one article each, the techniques that make modern LLM inference
affordable: what problem each solves, how it works, and what it costs you. Each
appraisal answers whether to run the technique, never how to study it.

Each appraisal runs in a fixed order: an "In plain language" note (nb-note)
stating the idea in one jargon-free paragraph, then the mechanism with the real
numbers, then the holds-up grid (nb-holdsup) weighing what it buys against what
it costs, then a "Verdict" note (nb-note nb-note-strong) before the close.

Show the central idea in code with the nb-code furniture when a few lines make
it concrete. Show the part of the technique the prose cannot carry. Keep it
short and cited.

Emphases:

- The plain-language abstract carries no notation and states the actual idea in
  one sentence that stands without the paper.
- Cite the paper or the reference implementation for how the technique works.
  Vendor benchmarks are a claim, not a result.
- An appraisal is a verdict, not a summary. Name the workload where the
  technique wins and the one where it does not.
- The verdict says when to reach for this in production and when not to, and
  names the result that would change the call.
