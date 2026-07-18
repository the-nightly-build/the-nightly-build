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

The catalogue is small on purpose: a few primitives the writer adapts beat a
component per idea. Retired components (callout, epigraph, aside, cast,
objectives box, check box, bridge, plain abstract, verdict, grade row, the
paper template's anchored excerpt) stay styled so the published shelf keeps
rendering; new articles express those moves through the note below, and a
claim's judgment lives on the claim card itself.

In the samples below, ALL-CAPS runs are placeholders: replace every one in
the article's own words. The proof warns on a caps run that survives into
prose. Sentence-case labels a component renders ("What holds up", "What to
be careful about") are fixed chrome: keep them verbatim. Everything else is
sample data: replace it.

The families, and how to choose within them. Evidence: a couple of
heterogeneous headline numbers are a stat strip, rows of one shape three or
more deep are a table, and anything the reader must see is a figure, drawn
from data or captured from a source. Voice: a labeled passage of any kind is
the note, and the article's own best sentence, promoted, is a pull quote.
Structure: stages in order are steps, events in time a timeline, a stance
anyone holds a position card, strengths against caveats the holds-up grid.
Judgment: scored criteria are a rubric, and a prediction is a claim card,
carried from open to hit or miss when a later article judges it.

## Stat strip

The numbers that carry the thesis. Any count works, one included. Each must
be cited in nearby prose.

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

## Table

Compact worked rows: steps of a computation, a record, a mapping, a
comparison, a ranking. Numeric cells are mono and never wrap (space digit
groups so the table fits a phone); add class `txt` on a cell that should
read as prose. First-column tokens may wear `nb-table-token` chips. The
caption states what the rows show and carries the citation.

```html
<table class="nb-table">
  <caption>
    WHAT THE ROWS SHOW.<sup class="nb-cite"><a href="#s1">1</a></sup>
  </caption>
  <thead>
    <tr>
      <th>STEP</th>
      <th>VALUE</th>
      <th class="txt">MEANING</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="nb-table-token">ROW</span></td>
      <td>1 0 0 1</td>
      <td class="txt">WHAT THIS ROW SAYS, IN PROSE.</td>
    </tr>
  </tbody>
</table>
```

## Figure

An image the argument needs, in one component with two kinds, told apart by
filename. A **chart** is drawn from data at production time: render with
`uv run --group charts engine/render_chart.py` (docs/charts.md), commit the
`chart-N.py` script beside `chart-N.png` as its provenance (the `chart-`
name is reserved), label axes, note a non-linear scale, and cite the data
source in the caption. A **source asset** (`asset-N.png`/`.jpg`/`.webp`) is
an exact visual captured from a cited primary or public document: a figure,
photograph, or document detail. Crop away page furniture and printed
captions unless that text is itself evidence, and cite the document. Both
live beside the article in `library/<series>/<slug>/`, need useful
alternative text, and restate what matters in caption and prose.

```html
<figure class="nb-figure">
  <img src="ARTICLE-SLUG/chart-1.png" alt="WHAT THE CHART SHOWS" />
  <figcaption>
    Fig. 1 · CAPTION.<sup class="nb-cite"><a href="#s1">1</a></sup>
  </figcaption>
</figure>

<figure class="nb-figure">
  <img src="ARTICLE-SLUG/asset-1.png" alt="WHAT THE ASSET SHOWS" />
  <figcaption>
    Fig. 2 · A SHORT FACTUAL LABEL.<sup class="nb-cite"
      ><a
        href="#s1"
        data-nb-locator="Fig. 1 · p. 4"
        data-nb-url="https://example.org/source.pdf#page=4"
        data-nb-note="WHAT THIS ASSET SUPPORTS IN THIS ARTICLE."
        >1</a
      ></sup
    >
  </figcaption>
</figure>
```

## The note

The one labeled-passage component. You supply the label and the content:
prose, a list, or a quotation. The label is not an enum. Name the move this
passage makes. A definition wears its term. A plain-language rendering
of a work's claim wears "In plain language". The weight-of-evidence landing
wears "Verdict" and the `nb-note-strong` modifier (at most one per article).
A sequenced series' pointer onward wears "Next article"; a teaching piece's
goals wear "In this article". Reuse a label the paper's shelf already uses
before coining a new one, and never stack two notes where one carries both
thoughts.

```html
<div class="nb-note">
  <span class="nb-note-label">THE MOVE THIS PASSAGE MAKES</span>
  <p>
    THE PASSAGE.<sup class="nb-cite"><a href="#s1">1</a></sup>
  </p>
</div>

<div class="nb-note nb-note-strong">
  <span class="nb-note-label">Verdict</span>
  <p>
    THE WEIGHT THE READER SHOULD PUT ON IT, AND WHAT WOULD CHANGE THE
    ASSESSMENT.<sup class="nb-cite"><a href="#s3">3</a></sup>
  </p>
</div>

<div class="nb-note">
  <span class="nb-note-label">A LABEL FOR A QUOTATION</span>
  <blockquote>
    THE QUOTATION, VERBATIM.<sup class="nb-cite"><a href="#s2">2</a></sup>
    <span class="nb-note-who">WHO SAID IT, WHERE</span>
  </blockquote>
</div>
```

## Pull quote

One sentence from the article itself, promoted for emphasis. Use at most one.

```html
<div class="nb-pull"><p>THE SENTENCE THAT EARNS THE SPACE.</p></div>
```

## Numbered steps

A mechanism or process, one stage per step. The connecting rule implies
order. Do not use it for unordered lists; a ranking is a table.

```html
<ol class="nb-steps">
  <li>
    <h3>STAGE</h3>
    <p>
      WHAT HAPPENS AT THIS STAGE.<sup class="nb-cite"><a href="#s2">2</a></sup>
    </p>
  </li>
  <li>
    <h3>NEXT STAGE</h3>
    <p>...</p>
  </li>
</ol>
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
    <p>WHAT HAPPENED, IN ONE OR TWO SENTENCES.</p>
  </li>
  <li class="nb-tl-interlude"><p>WHAT THE ERA ADDED UP TO.</p></li>
</ol>
```

## Position card

One cleanly stated position: whose it is, the statement once, a summary of
its basis, the citation. Use it for a named holder the article calls on, or
for the paper's own position in an opinion piece (the opinion template pins
it). The "Position" pill is fixed chrome.

```html
<div class="nb-position">
  <div class="nb-position-top">
    <span class="nb-position-who">WHO HOLDS IT</span>
    <span class="nb-position-pill">Position</span>
  </div>
  <p class="nb-position-statement">THE POSITION, STATED ONCE.</p>
  <p class="nb-position-summary">
    THE BASIS IT RESTS ON.<sup class="nb-cite"><a href="#s3">3</a></sup>
  </p>
</div>
```

## Holds-up grid

Strengths against caveats, side by side. Its summary row is a "Verdict" note
(see the note), usually right after it.

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

## Rubric

Scored criteria for a review: each row a criterion, an integer score 0–5,
and one cited line the score stands on. A series may pin criteria every
review must score (`rubric:` in series.yaml, docs/series.md § Rubrics); add
rows the subject demands. The rendered score text must agree with
`data-score`, and the meter colors itself from the score.

```html
<div class="nb-rubric">
  <div class="nb-rubric-row" data-nb-criterion="CRITERION-SLUG" data-score="4">
    <div class="nb-rubric-head">
      <span class="nb-rubric-name">CRITERION</span>
      <span class="nb-rubric-gauge"
        ><span class="nb-rubric-meter"><i></i></span
        ><span class="nb-rubric-score">4/5</span></span
      >
    </div>
    <p class="nb-rubric-note">
      THE LINE THE SCORE STANDS ON.<sup class="nb-cite"
        ><a href="#s2">2</a></sup
      >
    </p>
  </div>
</div>
```

## Claim card

A falsifiable prediction that carries its own lifecycle. The night it is
made it is open: the claim, the reasoning, confidence, and when it can be
judged. When a later article judges it, that article renders the same card
with `data-nb-resolution="hit"` or `"miss"`, the matching state chip text,
and an outcome line saying what actually happened. If a section makes
claims, later articles must grade them.

```html
<div class="nb-claim" data-nb-resolution="open">
  <div class="nb-claim-top">
    <h3>
      THE CLAIM<sup class="nb-cite"><a href="#s4">4</a></sup>
    </h3>
    <span class="nb-claim-state">Open</span>
  </div>
  <p>THE REASONING BEHIND IT.</p>
  <div class="nb-claim-meta">
    <span>confidence 70%</span><span>resolves by 2026-12-31</span>
  </div>
</div>

<div class="nb-claim" data-nb-resolution="hit">
  <div class="nb-claim-top">
    <h3>
      THE ORIGINAL CLAIM<sup class="nb-cite"><a href="#s4">4</a></sup>
    </h3>
    <span class="nb-claim-state">Hit</span>
  </div>
  <p class="nb-claim-outcome">
    WHAT ACTUALLY HAPPENED.<sup class="nb-cite"><a href="#s5">5</a></sup>
  </p>
  <div class="nb-claim-meta">
    <span>claimed 2026-01-08 at 70%</span><span>judged 2026-12-19</span>
  </div>
</div>
```
