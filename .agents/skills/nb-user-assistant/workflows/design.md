# Design the paper

Choose the smallest thing that can change:

- For masthead, tokens, typography, theme, or paper-wide voice, read
  `docs/guides/customize/appearance-and-voice.md`.
- For a reusable presentation component, read
  [furniture design](../craft/furniture-design.md) and the public furniture
  guide.
- For enforceable article structure, read
  [template design](../craft/template-design.md) and the template reference.

Start from the information problem, not the requested artifact. A user asking
for "a card" may need an existing note, table, or claim component. A user asking
for "a new template" may need a stronger series prompt. Show that diagnosis with
a representative content example.

Every visual proposal must survive realistic copy, long labels, narrow screens,
both themes, keyboard navigation, and a reader who cannot see color or run
JavaScript. Use the existing gallery and site preview as design tools, not just
build checks. Inspect results and iterate before presenting the work as done.

Design belongs to the user's taste. Iterate with them rather than presenting a
finished design for approval. Build a few genuinely different candidates with
realistic content, render each exactly as the site will show it, and offer to
open the rendered pages in the user's browser for reaction. Revise from what
they say and return with the next render. Never present a single take as the
finished design.

Keep all paper-specific design under `press/`. A requested change to generated
site navigation or page layout is an engine contribution, not customization.
State that maintenance cost before proceeding.
