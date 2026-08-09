# Furniture design

Read `docs/reference/furniture.md`, the current catalogs, styles, and gallery
tooling before proposing a new component.

## Design brief

Write the brief before markup:

- the information relationship or deliberate emphasis the component reveals
- when to use it and when prose, a table, a figure, or existing furniture is
  better
- the smallest semantic HTML that carries that meaning
- content constraints, edge cases, and citation behavior
- screen-reader and keyboard behavior
- narrow, wide, print-like, light, and dark presentation
- behavior without JavaScript or when an optional library fails

Use representative real content, including the longest plausible label and the
sparsest valid case.

## Implement and inspect

Use a user-owned prefix and existing design tokens. Keep DOM order meaningful
without CSS. Do not encode information in color alone, make a horizontally
compressed desktop block unreadable on a phone, or introduce motion without a
purpose and reduced-motion behavior.

Document the component in its catalog as a decision tool: purpose, selection
rule, exact markup, content constraints, and accessibility notes. Add a gallery
sample from the same owner. Build the gallery and an article using realistic
copy. Inspect both themes and multiple widths, then test the component beside
ordinary prose so it improves the page rather than dominating it.

Revise until the component remains legible, useful, and visually part of the
paper under all tested cases. A passing stylesheet or attractive screenshot is
not sufficient evidence.

The component belongs to the user's taste. Build the candidates as genuinely
different options, offer to open the rendered gallery and article pages in their
browser for reaction, and iterate from what they say before treating the design
as done.
