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

The original's own sentences, quoted verbatim where the argument turns, with
a locator into the source and a one-line gloss of what the passage does and
does not claim. When the paper has no numbered sections or pages (arXiv
HTML often has neither), the locator stays honest: "Abstract", "Introduction · closing
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
