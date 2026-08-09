# The unbiased template's furniture

## The split (`nb-divide` + `nb-side`)

Exactly two positions across an accent spine: left and right on wide screens,
stacked with mirrored rails on phones. Each position contains exactly one of the
four components below. They orient the reader without prescribing the argument
inside them.

```html
<div class="nb-divide">
  <section
    class="nb-side nb-side-left"
    data-nb-section="POSITION-A-SLUG"
    id="POSITION-A-SLUG"
  >
    <h3 class="nb-side-camp">RECOGNIZABLE NAME FOR THIS POSITION</h3>
    <p class="nb-side-thesis">THE POSITION STATED CONCISELY.</p>
    <div class="nb-side-argument">
      <p>
        EVIDENCE AND REASONING IN THE FORM THIS QUESTION REQUIRES.<sup
          class="nb-cite"
          ><a href="#s2">2</a></sup
        >
      </p>
    </div>
    <p class="nb-side-champion">
      <span class="nb-side-outlet">NAMED PERSON OR INSTITUTION</span>. WHY THIS
      HOLDER HAS STANDING ON THE QUESTION.<sup class="nb-cite"
        ><a href="#s2">2</a></sup
      >
    </p>
  </section>
  <section
    class="nb-side nb-side-right"
    data-nb-section="POSITION-B-SLUG"
    id="POSITION-B-SLUG"
  >
    <!-- the same four slots, mirrored -->
  </section>
</div>
```

The slots are the position's recognizable **name** (`nb-side-camp`), its concise
**thesis** (`nb-side-thesis`), the open **argument** (`nb-side-argument`), and a
credible named **holder** with a cited statement and a brief indication of
standing (`nb-side-champion`). The manifest makes all four mandatory in both
positions. One accent is mirrored across the split. It is never a color assigned
to either position.
