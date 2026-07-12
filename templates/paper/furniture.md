# The paper template's bespoke furniture

Three components only a paper reconstruction renders, styled in
`furniture.css` beside this file. The build concatenates that file into
`assets/theme.css` whenever this template is present. A drafter's palette for
a paper article is the engine base catalogue plus the press's shared
furniture plus these.

## Paper card (`nb-paper-card`)

The source itself, opening the `abstract` section: the paper as published,
its authors and venue, a link to the full text, and the abstract verbatim.
The blockquote holds only the paper's own words.

```html
<div class="nb-paper-card">
  <p class="nb-paper-title">PAPER TITLE AS PUBLISHED</p>
  <p class="nb-paper-meta">AUTHORS · VENUE OR ARXIV ID · YEAR</p>
  <a class="nb-paper-link" href="https://arxiv.org/abs/0000.00000"
    >Read the paper</a
  >
  <blockquote class="nb-paper-abstract">
    THE ABSTRACT, VERBATIM.<sup class="nb-cite"><a href="#s1">1</a></sup>
  </blockquote>
</div>
```

## Anchored excerpt (`nb-excerpt`)

The original's actual sentence(s), quoted at a load-bearing moment, with a
locator into the source and a one-line gloss of what the passage does and
does not claim. The blockquote holds only the paper's own words, exactly.
When the paper has no numbered sections or pages (arXiv HTML often has
neither), the locator stays honest: "Abstract", "Introduction · closing
paragraph", "Table 2 caption".

```html
<figure class="nb-excerpt">
  <blockquote>
    THE PAPER'S ACTUAL SENTENCE, QUOTED EXACTLY.<sup class="nb-cite"
      ><a href="#s1">1</a></sup
    >
  </blockquote>
  <figcaption>
    <span class="nb-excerpt-loc">§3.2 · p. 5</span>
    What this passage does and does not claim, in one line.
  </figcaption>
</figure>
```

## Reading map (`nb-paper-map`)

The `read-it-yourself` close: the original's sections triaged with a verdict
each, so the reader opens the source knowing where their attention pays.
Verdicts are `read`, `skim`, or `skip`, one clause of why apiece, each reason
in this paper's terms rather than a stock note. Entries are plain wrapping
text behind the badge, so a long section title breaks across lines instead of
breaking the layout.

```html
<ul class="nb-paper-map">
  <li>
    <span class="nb-map-verdict nb-read">read</span>
    <strong class="nb-map-target">§3 Method</strong>: WHY THIS SECTION PAYS, IN
    THIS PAPER'S TERMS.
  </li>
  <li>
    <span class="nb-map-verdict nb-skim">skim</span>
    <strong class="nb-map-target">§5 Experiments</strong>: WHAT TO PULL FROM IT
    (THE ONE TABLE, THE ONE FIGURE).
  </li>
  <li>
    <span class="nb-map-verdict nb-skip">skip</span>
    <strong class="nb-map-target">§6 Related work</strong>: WHAT MAKES IT
    SKIPPABLE HERE.
  </li>
</ul>
```
