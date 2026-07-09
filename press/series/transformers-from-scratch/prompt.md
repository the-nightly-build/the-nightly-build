# Transformers from Scratch

A course that builds a decoder-only transformer (a tiny GPT) from first
principles, for an engineer who knows Python and basic neural nets but has never
implemented attention. Each article is one lesson that builds on the last, and
by the final lesson the reader could train a small model that generates text.
The throughline is a single running example: a character-level GPT trained on a
small text corpus, extended one mechanism at a time.

Every lesson follows the teaching furniture: open with the objectives box
(nb-objectives) stating what the reader will be able to do, recap the previous
lesson concretely (you read it, per protocol), teach the core mechanism, then
close with the check-yourself box (nb-check-box) and a bridge (nb-bridge) to the
next lesson.

Show real code with the rs-code furniture. This paper loads Prism (declared in
`site.yaml`), so you write plain code in a `language-python` block and it is
highlighted for you. Escape `<`, `>`, and `&`. Keep listings short, runnable,
and honest — prefer PyTorch, and show the shapes.

```html
<div class="rs-code">
  <div class="rs-code-head">
    <span class="rs-code-file">attention.py</span><span>PyTorch</span>
  </div>
  <pre><code class="language-python">scores = q @ k.transpose(-2, -1) / math.sqrt(head_dim)  # (B, T, T)
weights = scores.masked_fill(causal_mask, float("-inf")).softmax(dim=-1)
out = weights @ v  # (B, T, head_dim)</code></pre>
  <span class="rs-code-cap">Fig. 1 · scaled dot-product attention, with a source.</span>
</div>
```

Emphases:

- Build each idea from one the reader already holds. Define every term (query,
  key, value, logit, residual stream) on first use, and never introduce a symbol
  without saying what it is and its shape.
- Derive, don't assert. Show why attention is a weighted average, why the
  `1/sqrt(d_k)` scaling exists, why masking makes it causal. Cite the primary
  sources (Attention Is All You Need, the GPT papers, and reputable
  implementations) for each load-bearing claim.
- Check-yourself exercises must be answerable from the lesson alone. A reader who
  can do them has implemented the thing.
- nb-steps suits any mechanism walked in order: the forward pass of a block, the
  shapes through multi-head attention, the training loop.
