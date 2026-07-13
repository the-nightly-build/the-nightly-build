# Furniture

Furniture is the set of pre-designed components an article may use. The
engine's shared CSS styles every class in both color schemes, so composing
pieces cannot break the paper's look. Use a piece when it carries information
better than prose would. Skip it when it would decorate. Two or three pieces
per article is typical. Zero is fine.

Section tags, citation markup, source entries, and the nb-meta block are
protocol, not furniture. PROTOCOL.md defines them. This base catalogue is the
engine's, always available to every template. A paper can add its own
furniture (paper-wide in `press/furniture/`, or bespoke inside one template's
folder) and instruct sections to use it in prompt.md (see
docs/customization.md).

In the samples below, ALL-CAPS runs are placeholders: replace every one in
the article's own words. The proof warns on a caps run that survives into
prose. Sentence-case labels the component renders ("In plain language",
"What holds up", "What to be careful about", "Verdict", "Next article",
"In this article") are fixed chrome: keep them verbatim. Everything else is
sample data: replace it.

## Stat strip

Three or four numbers that carry the thesis. Each must be cited in nearby prose.

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
Restate the data in caption and prose. The noscript line is fixed chrome.

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

A term or concept the reader must carry forward.

```html
<div class="nb-callout">
  <span class="nb-callout-term">KEY TERM</span>
  A CRISP DEFINITION.
</div>
```

## Pull quote

One sentence from the article itself, promoted for emphasis. Use at most one.

```html
<div class="nb-pull"><p>THE SENTENCE THAT EARNS THE SPACE.</p></div>
```

## Epigraph

An opening quotation, before the first section. Cite it like any claim.

```html
<div class="nb-epigraph">
  <p>
    THE QUOTATION, VERBATIM.<sup class="nb-cite"><a href="#s1">1</a></sup>
  </p>
  <span class="nb-epigraph-who">WHO SAID IT, WHERE</span>
</div>
```

## Aside

A short tangent worth keeping out of the main flow. Floats right on wide
screens, sits inline on phones. Sans-set, so it reads as apparatus.

```html
<div class="nb-aside">THE TANGENT, ONE TO THREE SENTENCES.</div>
```

## Numbered steps

A mechanism or process, one stage per step. The connecting rule implies
order. Do not use it for unordered lists.

```html
<ol class="nb-steps">
  <li>
    <h3>STAGE</h3>
    <p>
      WHAT HAPPENS AND WHY IT MATTERS.<sup class="nb-cite"
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
grounded in their cited statements. Use two or more. Never one.

```html
<div class="nb-position">
  <span class="nb-position-who">WHO</span>
  <span class="nb-position-stance">THEIR POSITION IN ONE SENTENCE.</span>
  <p>
    WHAT THEY HAVE ACTUALLY SAID AND WHERE.<sup class="nb-cite"
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
    <p>WHAT HAPPENED AND WHY IT MATTERED.</p>
  </li>
  <li class="nb-tl-interlude"><p>WHAT THE ERA ADDED UP TO.</p></li>
</ol>
```

## Objectives box

What the reader will be able to do afterwards. For teaching pieces.

```html
<div class="nb-objectives">
  <div class="nb-objectives-label">In this article</div>
  <ul>
    <li>OBJECTIVE, CONCRETE AND CHECKABLE.</li>
  </ul>
</div>
```

## Check box

Self-test exercises answerable from the article.

```html
<div class="nb-check-box">
  <ol>
    <li>EXERCISE, ANSWERABLE FROM THE ARTICLE.</li>
  </ol>
</div>
```

## Bridge

What comes next and why today's ideas are its prerequisites. For sequenced series.

```html
<div class="nb-bridge">
  <span class="nb-bridge-label">Next article</span>
  ONE OR TWO SENTENCES.
</div>
```

## Plain abstract

A jargon-free statement of what a work claims and shows. For appraisals.

```html
<div class="nb-abstract">
  <div class="nb-abstract-label">In plain language</div>
  <p>
    THE CLAIM, THE TEST, THE FINDING.<sup class="nb-cite"
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
  TWO OR THREE SENTENCES.<sup class="nb-cite"><a href="#s3">3</a></sup>
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
  <p>THE REASONING BEHIND IT.</p>
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
    THE CLAIM, AND WHAT ACTUALLY HAPPENED.<sup class="nb-cite"
      ><a href="#s5">5</a></sup
    >
  </p>
</div>
```
