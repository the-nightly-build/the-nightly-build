# The lesson template's bespoke furniture

The components only a lesson renders, styled in `furniture.css` beside this
file. The build concatenates that file into `assets/theme.css` whenever this
template is present. A drafter's palette for a lesson is the engine base
catalogue plus the press's shared furniture plus these.

## Lesson bookends (`nb-bookend`)

Two cards frame every lesson: Why this matters opens it, The takeaway closes
it. Both are written after the body; the template's `identity.md` carries the
writing rules. The name lines, the band labels (Background, Go deeper), and the
words "optional reading" are fixed chrome. Reading rows are editorial: each row
is a link and one line on what it covers. Background rows may point into this
library or beyond; Go deeper rows always point beyond this paper. Bookends are
apparatus, not claims, so they carry no citations.

```html
<section class="nb-bookend" data-nb-section="why" id="why">
  <p class="nb-bookend-name">Why this matters</p>
  <div class="nb-bookend-rule"></div>
  <p>THE OPENER, TO THE READER, THIS LESSON'S PARTICULARS ONLY.</p>
  <div class="nb-bookend-band">
    <span class="nb-bookend-label">Background</span>
    <span class="nb-bookend-note">optional reading</span>
  </div>
  <dl class="nb-bookend-reading">
    <dt>01</dt>
    <dd><a href="../SERIES-ID/SLUG.html">TITLE</a>: WHAT IT COVERS.</dd>
  </dl>
</section>
```

The takeaway card is the same markup with `data-nb-section="takeaway"`,
`id="takeaway"`, the name line "The takeaway", and the band label "Go deeper".
