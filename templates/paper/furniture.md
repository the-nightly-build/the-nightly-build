# The paper template's bespoke furniture

The component only a paper reconstruction renders, styled in
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

The anchored excerpt is retired: a citation's own `data-nb-locator`,
`data-nb-url`, and `data-nb-note` carry the anchor, and a verbatim passage
that earns display space is a note holding a quotation (see
templates/FURNITURE.md). Published articles keep rendering `nb-excerpt`.
