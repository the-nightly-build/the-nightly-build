# The divide template's furniture

## The split (`rs-divide` + `rs-side`)

Exactly two sides across an accent spine: left and right on wide screens, stacked
but still allegiant on phones. Each side is four slots, in order.

```html
<div class="rs-divide">
  <section
    class="rs-side rs-left"
    data-nb-section="the-case-for-X"
    id="the-case-for-X"
  >
    <h3 class="rs-side-camp">WHO HOLDS THIS SIDE</h3>
    <p class="rs-side-thesis">The position in one sentence.</p>
    <p>
      Its strongest form, in their actual cited words.<sup class="nb-cite"
        ><a href="#s2">2</a></sup
      >
    </p>
    <p class="rs-side-champion">
      <span class="rs-side-outlet">OUTLET</span>, standing here because
      REASON.<sup class="nb-cite"><a href="#s2">2</a></sup>
    </p>
  </section>
  <section
    class="rs-side rs-right"
    data-nb-section="the-case-for-Y"
    id="the-case-for-Y"
  >
    <!-- the same four slots, mirrored -->
  </section>
</div>
```

The slots: **camp** (`rs-side-camp`, who holds it), **thesis**
(`rs-side-thesis`, the position in one sentence), **argument**
(`rs-side-argument`, a wrapper holding the cited prose in the form its best
advocate would recognize), and **champion**
(`rs-side-champion`, the vetted holder and in one clause why it has standing on
this question, cited). One accent, mirrored, never two team colors.
