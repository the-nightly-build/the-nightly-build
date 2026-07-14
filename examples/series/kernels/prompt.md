# Kernels

A course in writing fast GPU kernels, from the execution model up to
FlashAttention, for an engineer who knows deep learning but has never written
CUDA or Triton. Each article is one lesson that builds on the last. Triton is
OpenAI's open-source GPU language and the layer PyTorch's `torch.compile` lowers
to, so the payoff is code the reader can run.

Every lesson follows the teaching furniture: open with the objectives box
(nb-objectives) stating what the reader will be able to do, recap the previous
lesson concretely, teach the core, and close with the check-yourself box
(nb-check-box) and a bridge (nb-bridge) to the next lesson.

Show real code with the rs-code furniture: Triton in Python, CUDA in C++. Keep
listings short and honest. The reader should be able to run what you print.

Emphases:

- Build each idea from one the reader already holds, and reuse one running
  example across the course. Define each term on first use.
- Real numbers over hand-waving, each cited. A lesson that cannot measure its
  kernel has not taught it.
- Check-yourself exercises must be answerable from the lesson alone. A reader
  who can do them has learned the thing.
- nb-steps suits any mechanism walked in order: a kernel's phases, a memory
  access pattern, a tiling scheme.
