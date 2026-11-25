# Furniture

Furniture is reusable article markup with a defined communicative purpose:
timelines, tables, figures, pull quotes, rubrics, and reading cards. Use a
component when it clarifies information better than prose. Start with the
shipped catalog in `templates/FURNITURE.md`, which works in every template and
covers most papers.

Visual ownership splits cleanly in `press/`:

- **Templates** fix article structure.
- **Themes** set paper-wide color tokens.
- **Furniture** supplies reusable components inside articles.

## Adding custom furniture

1. **Choose the scope.** Put cross-series components in `press/furniture/`. Put
   components tied to a single template inside `press/templates/<id>/`.
2. **Check the shipped catalog first** to avoid duplicating existing components.
3. **Test with real article content** in a browser across desktop and phone
   widths and both light and dark themes.
4. **Package the component** with a catalog entry, stylesheet, and sample page.
   Verify it works without JavaScript, on narrow screens, in both themes, and
   with screen readers.

See [Furniture reference](../../reference/furniture.md) for the directory
layout, catalog contract, gallery command, external SRI libraries, and the
class-inventory check.
