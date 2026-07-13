# This paper's shared furniture

## Code block (`rs-code`)

A real code listing with a header (file · language) and an optional cited
caption. The article writes plain `<pre><code class="language-python">`. Prism
(declared in `site.yaml` `assets:`, loaded on every page) highlights it into
`.token` spans and `styles.css` colors them. No-JS readers still get clean
monospace. Used by Kernels and The Inference Stack.

```html
<figure class="rs-code">
  <div class="rs-code-head">
    <span class="rs-code-file">path/to/file.py</span><span>PYTHON</span>
  </div>
  <pre><code class="language-python">def attention(q, k, v):
    ...</code></pre>
  <figcaption class="rs-code-cap">
    Fig. 1 · What the listing shows.<sup class="nb-cite"
      ><a href="#s1">1</a></sup
    >
  </figcaption>
</figure>
```

## Case docket (`rs-docket`)

The standing facts of a legal matter as reference data, set apart so the prose
can argue instead of recite. Used by Docket. Open the article with it.

```html
<div class="rs-docket">
  <span class="rs-docket-case">Parties, short form</span>
  <span class="rs-docket-court">Court · docket no.</span>
  <dl class="rs-docket-grid">
    <dt>Stage</dt>
    <dd>where it is now</dd>
    <dt>Question</dt>
    <dd>the legal question in one line</dd>
    <dt>Stakes</dt>
    <dd>what turns on it for people who build AI</dd>
  </dl>
</div>
```
