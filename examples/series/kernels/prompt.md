# Kernels

A course in writing fast GPU kernels, from the execution model up to
FlashAttention, for an engineer who knows deep learning but has never written
CUDA or Triton. Each article is one lesson that builds on the last. Triton is
OpenAI's open-source GPU language and the layer PyTorch's `torch.compile` lowers
to, so the payoff is code the reader could actually run.

Every lesson follows the teaching furniture: open with the objectives box
(nb-objectives) stating what the reader will be able to do, recap the previous
lesson concretely (you read it, per protocol), teach the core, then close with
the check-yourself box (nb-check-box) and a bridge (nb-bridge) to the next
lesson.

Show real code with the rs-code furniture. This site loads Prism (declared in
`site.yaml`), so you write plain code in a language-tagged block and it is
highlighted for you: `language-python` for Triton, `language-cpp` for CUDA C.
Escape `<`, `>`, and `&`. Keep listings short and honest.

```html
<div class="rs-code">
  <div class="rs-code-head">
    <span class="rs-code-file">add_kernel.py</span><span>Triton</span>
  </div>
  <pre><code class="language-python">@triton.jit
def add_kernel(x_ptr, y_ptr, out_ptr, n, BLOCK: tl.constexpr):
    pid = tl.program_id(axis=0)  # one instance per block
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    return tl.load(x_ptr + offs) + tl.load(y_ptr + offs)</code></pre>
  <span class="rs-code-cap">Fig. 1 · what to notice, with a source.</span>
</div>
```

Emphases:

- Build each idea from one the reader already holds, and reuse a single running
  example across the whole course. Define each term on first use.
- Real numbers over hand-waving, each cited: bytes moved, arithmetic intensity,
  achieved versus peak bandwidth, occupancy, kernel time. The `hardware` tag
  makes the roofline the throughline.
- Check-yourself exercises must be answerable from the lesson alone. A reader
  who can do them has learned the thing.
- nb-steps suits any mechanism walked in order: a kernel's phases, a memory
  access pattern, a tiling scheme.
