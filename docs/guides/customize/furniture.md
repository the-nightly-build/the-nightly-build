# Furniture

Furniture is reusable article markup with a defined communicative purpose: a
timeline, comparison, evidence card, pull quote, rubric, or other reading aid. A
component belongs in an article when it makes specific information easier to
understand than prose would. Start with `templates/FURNITURE.md`, the shipped
catalog. Its components work in every template, and most papers never need more.

Templates, themes, and furniture divide the visual work. The template fixes an
article's structure, the theme sets the paper-wide color tokens, and furniture
supplies the reusable components inside the structure. All three are yours to
define in `press/`.

When your paper does need its own component, decide the scope first. Shared
press furniture under `press/furniture/` serves several series. A component
whose meaning depends on one template belongs inside that template's package.

Design furniture with your assistant, starting from the information problem
rather than the markup: a request for "a card" may be better served by an
existing component. Expect a few genuinely different candidates rendered with
realistic content, an offer to open them in your browser, and iteration from
your reactions. A finished component gets a catalog entry, a stylesheet, and a
sample page, and holds up without JavaScript, on a phone, in both themes, and
for screen readers.

The [Furniture reference](../../reference/furniture.md) has the package layout,
the catalog contract, the gallery command, external libraries with Subresource
Integrity, and the class-inventory check.
