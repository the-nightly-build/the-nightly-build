# The unbiased template's furniture

## The split (`nb-divide` + `nb-side`)

Exactly two sides across an accent spine: left and right on wide screens, stacked
but still allegiant on phones. Each side is four slots, in order.

```html
<div class="nb-divide">
  <section
    class="nb-side nb-side-left"
    data-nb-section="the-case-for-X"
    id="the-case-for-X"
  >
    <h3 class="nb-side-camp">WHO HOLDS THIS SIDE</h3>
    <p class="nb-side-thesis">The position in one sentence.</p>
    <p>
      Its strongest form, in their actual cited words.<sup class="nb-cite"
        ><a href="#s2">2</a></sup
      >
    </p>
    <p class="nb-side-champion">
      <span class="nb-side-outlet">OUTLET</span>, standing here because
      REASON.<sup class="nb-cite"><a href="#s2">2</a></sup>
    </p>
  </section>
  <section
    class="nb-side nb-side-right"
    data-nb-section="the-case-for-Y"
    id="the-case-for-Y"
  >
    <!-- the same four slots, mirrored -->
  </section>
</div>
```

The slots: **camp** (`nb-side-camp`, who holds it), **thesis**
(`nb-side-thesis`, the position in one sentence), the **argument**
(`nb-side-argument`, a wrapper holding the cited prose, in the form its best advocate would recognize), and the **champion**
(`nb-side-champion`, the vetted holder and in one clause why it has standing on
this question, cited). One accent, mirrored across both sides, never a
color per team.
