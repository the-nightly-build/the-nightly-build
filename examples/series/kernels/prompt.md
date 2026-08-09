# Kernels

A course in writing fast GPU kernels, from the execution model up to
FlashAttention. The course assumes deep learning fluency and no prior CUDA or
Triton. Each article is one lesson that builds on the last. Triton is OpenAI's
open-source GPU language and the layer PyTorch's `torch.compile` lowers to, so
the payoff of every lesson is runnable code.

Every lesson follows the teaching moves, each a labeled note (nb-note): open
with an "In this article" note stating what the lesson makes doable, recap the
previous lesson concretely, teach the core, and close with a self-check note of
exercises and a "Next article" note bridging onward.

Show real code with the nb-code furniture: Triton in Python, CUDA in C++. Escape
the code as HTML: an unescaped `kernel<<<blocks, threads>>>` is read as a tag
and silently eaten. Keep listings short, honest, and runnable as printed.

Emphases:

- Build each idea from one an earlier lesson established, and reuse one running
  example across the course. Define each term on first use.
- Real numbers over hand-waving, each cited. Every lesson measures the kernel it
  teaches.
- Check-yourself exercises must be answerable from the lesson alone.
- nb-steps suits any mechanism walked in order: a kernel's phases, a memory
  access pattern, a tiling scheme.
