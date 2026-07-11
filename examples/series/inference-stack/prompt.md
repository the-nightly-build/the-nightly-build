# The Inference Stack

Appraise, one article each, the techniques that make modern LLM inference
affordable: what problem each solves, how it works, and what it costs you in
return. The reader is an engineer deciding what to actually run, not a student.
Label these articles `Appraisal`.

Each appraisal fixes its spine: open with the plain-abstract furniture
(nb-abstract) stating the idea in one jargon-free paragraph, then a section on
the mechanism with the real numbers, then the holds-up grid (nb-holdsup)
weighing what it buys against what it costs, and close on a verdict box
(nb-verdict) before the close.

Show the load-bearing idea in code with the rs-code furniture when a few lines
make it concrete: a kernel signature, a scheduling loop, a quantization step.
Write it in a language-tagged block (`language-python`, `language-cpp`); Prism
(loaded via `site.yaml`) highlights it. Keep it short and cited.

Emphases:

- The plain-language abstract is for a reader who will never open the paper: no
  notation, the actual idea in a sentence.
- Ground every performance claim in the `benchmarks` discipline: the eval setup,
  the baseline, the hardware. A speedup without its harness does not go in.
- The `hardware` tag keeps the analysis honest about where the technique sits in
  the memory hierarchy and which bottleneck it relieves.
- The verdict says when to reach for this in production and when not to, and
  names the result that would change the call.
