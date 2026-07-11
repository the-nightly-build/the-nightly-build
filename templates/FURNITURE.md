# Furniture

Furniture is the set of pre-designed components an article may use. Every
class here is styled by the engine's shared CSS in both color schemes, so
composing them cannot break the paper's look. Any template may use any
component in this catalogue. Use a piece when it carries information better than prose would;
skip it when it would decorate. Two or three pieces per article is typical,
zero is fine.

The section tags, citation markup, source entries, and nb-meta block are
protocol, not furniture; they are defined in PROTOCOL.md. This is the engine's
base catalogue, always available. A paper can add its own furniture too (shared
across the paper in `press/furniture/`, or bespoke to one template in that
template's folder) and instruct sections to use it in prompt.md (see
docs/customization.md).

## Stat strip

Three or four load-bearing numbers. Each must be cited in nearby prose.

```html
<div class="nb-stat-strip">
  <div class="nb-stat">
    <span class="nb-stat-n">$193B</span
    ><span class="nb-stat-l">DATA-CENTER REVENUE</span>
  </div>
  <div class="nb-stat">
    <span class="nb-stat-n">92%</span><span class="nb-stat-l">SHARE</span>
  </div>
</div>
```

## Chart

Declarative data, rendered by the engine runtime. Types: line, bar, scatter.

```html
<figure class="nb-chart">
  <figcaption>Fig. 1 · CAPTION</figcaption>
  <canvas></canvas>
  <noscript>chart requires JS; data in caption and prose</noscript>
  <script type="application/json" data-nb-chart>
    {
      "type": "line",
      "labels": ["2022", "2023"],
      "series": [{ "name": "NAME", "values": [1, 2] }],
      "y": { "scale": "linear", "label": "UNITS" }
    }
  </script>
</figure>
```

## Callout

A key term or concept the reader should carry forward.

```html
<div class="nb-callout">
  <span class="nb-callout-term">KEY TERM</span>
  A crisp definition.
</div>
```

## Pull quote

One sentence from the article itself, promoted for emphasis. Use at most one.

```html
<div class="nb-pull"><p>The sentence that earns the space.</p></div>
```

## Epigraph

An opening quotation, before the first section. Cite it like any claim.

```html
<div class="nb-epigraph">
  <p>
    The quotation.<sup class="nb-cite"><a href="#s1">1</a></sup>
  </p>
  <span class="nb-epigraph-who">WHO SAID IT, WHERE</span>
</div>
```

## Aside

A short tangent worth keeping out of the main flow. Floats right on wide
screens, sits inline on phones. Sans-set, so it reads as apparatus.

```html
<div class="nb-aside">The tangent, one to three sentences.</div>
```

## Numbered steps

A mechanism or process, one stage per step. The connecting rule implies
order; do not use it for unordered lists.

```html
<ol class="nb-steps">
  <li>
    <h3>STAGE</h3>
    <p>
      What happens and why it matters.<sup class="nb-cite"
        ><a href="#s2">2</a></sup
      >
    </p>
  </li>
  <li>
    <h3>NEXT STAGE</h3>
    <p>...</p>
  </li>
</ol>
```

## Cast

The people and institutions in a story, one line each.

```html
<div class="nb-cast">
  <div>
    <span class="nb-cast-name">NAME</span
    ><span class="nb-cast-role">ROLE IN THIS STORY</span>
  </div>
</div>
```

## Position block

One participant's stance in a disagreement, stated at its strongest and
grounded in their actual cited statements. Use two or more; never one.

```html
<div class="nb-position">
  <span class="nb-position-who">WHO</span>
  <span class="nb-position-stance">Their position in one sentence.</span>
  <p>
    What they have actually said and where.<sup class="nb-cite"
      ><a href="#s3">3</a></sup
    >
  </p>
</div>
```

## Timeline

Events along a dated spine, with optional prose interludes between eras.
Add class `major` for filled dots.

```html
<ol class="nb-timeline">
  <li class="nb-tl-event major">
    <span class="nb-tl-date">1997</span>
    <h3>
      EVENT<sup class="nb-cite"><a href="#s2">2</a></sup>
    </h3>
    <p>What happened and why it mattered.</p>
  </li>
  <li class="nb-tl-interlude"><p>What the era added up to.</p></li>
</ol>
```

## Objectives box

What the reader will be able to do afterwards. Openers for teaching pieces.

```html
<div class="nb-objectives">
  <div class="nb-objectives-label">In this article</div>
  <ul>
    <li>OBJECTIVE, concrete and checkable.</li>
  </ul>
</div>
```

## Check box

Self-test exercises answerable from the article.

```html
<div class="nb-check-box">
  <ol>
    <li>EXERCISE.</li>
  </ol>
</div>
```

## Bridge

What comes next and why today's ideas are its prerequisites. Closers for
sequenced series.

```html
<div class="nb-bridge">
  <span class="nb-bridge-label">Next article</span>
  One or two sentences.
</div>
```

## Plain abstract

A jargon-free statement of what a work claims and shows. Openers for
appraisals.

```html
<div class="nb-abstract">
  <div class="nb-abstract-label">In plain language</div>
  <p>
    The claim, the test, the finding.<sup class="nb-cite"
      ><a href="#s1">1</a></sup
    >
  </p>
</div>
```

## Holds-up grid

Strengths against caveats, side by side.

```html
<div class="nb-holdsup">
  <div class="good">
    <span class="nb-holdsup-label">What holds up</span>
    <ul>
      <li>STRENGTH.</li>
    </ul>
  </div>
  <div class="careful">
    <span class="nb-holdsup-label">What to be careful about</span>
    <ul>
      <li>LIMITATION.</li>
    </ul>
  </div>
</div>
```

## Verdict

How much weight the reader should put on something, and what would change
the assessment.

```html
<div class="nb-verdict">
  <span class="nb-verdict-label">Verdict</span>
  Two or three sentences.<sup class="nb-cite"><a href="#s3">3</a></sup>
</div>
```

## Claim card

A falsifiable prediction: what, how confident, and when it can be judged.
If a section makes claims, later articles should grade them (see grade row).

```html
<div class="nb-claim">
  <h3>
    THE CLAIM<sup class="nb-cite"><a href="#s4">4</a></sup>
  </h3>
  <p>The reasoning behind it.</p>
  <div class="nb-claim-meta">
    <span>confidence 70%</span><span>resolves by 2026-12-31</span>
  </div>
</div>
```

## Grade row

A past claim judged against what happened. Verdict class: `hit`, `miss`,
or `open`.

```html
<div class="nb-grade hit">
  <span class="nb-grade-verdict">Hit</span>
  <p>
    The claim, and what actually happened.<sup class="nb-cite"
      ><a href="#s5">5</a></sup
    >
  </p>
</div>
```
