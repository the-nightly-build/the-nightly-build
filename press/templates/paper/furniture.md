# The paper template's bespoke furniture

Two components only a paper reconstruction renders, styled in `furniture.css`
beside this file on the `rs-` prefix (`nb-` is the engine's). The engine
concatenates that file into `assets/theme.css` whenever this template is
present. A drafter's palette for a paper article is the engine base catalogue
plus the press's shared furniture plus these.

## Anchored excerpt (`rs-excerpt`)

The original paper's actual sentence(s), quoted at a load-bearing moment,
with a locator into the source and a one-line gloss of what the passage does
and does not claim. Two to five per article. The blockquote holds only the
paper's own words, exactly.

```html
<figure class="rs-excerpt">
  <blockquote>
    THE PAPER'S ACTUAL SENTENCE, QUOTED EXACTLY.<sup class="nb-cite"
      ><a href="#s1">1</a></sup
    >
  </blockquote>
  <figcaption>
    <span class="rs-excerpt-loc">§3.2 · p. 5</span>
    What this passage does and does not claim, in one line.
  </figcaption>
</figure>
```

## Reading map (`rs-paper-map`)

The `read-it-yourself` close: the original's sections triaged with a verdict
each, so the reader opens the PDF knowing where his attention pays. Verdicts
are `read`, `skim`, or `skip`, one clause of why apiece.

```html
<ul class="rs-paper-map">
  <li>
    <span class="rs-map-verdict rs-read">read</span>
    <span class="rs-map-target">§3 Method</span>
    where the contribution actually lives.
  </li>
  <li>
    <span class="rs-map-verdict rs-skim">skim</span>
    <span class="rs-map-target">§5 Experiments</span>
    Table 2 is the one to stare at; the rest confirms it.
  </li>
  <li>
    <span class="rs-map-verdict rs-skip">skip</span>
    <span class="rs-map-target">§6 Related work</span>
    defensive reviewer coverage; this article already placed the paper.
  </li>
</ul>
```
