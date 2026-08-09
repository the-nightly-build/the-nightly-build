# Furniture reference

Furniture is reusable article markup with a defined communicative purpose. The
shipped catalog is `templates/FURNITURE.md`, and its components work in every
template. Custom furniture has two scopes:

```text
press/furniture/          # shared, available to every series
├── catalog.md
├── styles.css
└── samples/<slug>.html

press/templates/<id>/     # bespoke to one template
├── furniture.md
├── furniture.css
└── samples/<slug>.html
```

A component's catalog entry is its contract: the purpose, the exact markup, and
the constraints. Production writers use only documented markup, never classes
inferred from a stylesheet, so an undocumented component goes unused.

## Requirements

- Use your own CSS prefix. `nb-` is reserved for the engine.
- Components must work without JavaScript, on narrow screens, in both themes,
  and for screen readers.
- The builder concatenates the selected theme and every furniture stylesheet
  into the published `assets/theme.css`, so a style change restyles the back
  catalog on the next build.

## The gallery

`uv run python scripts/gallery/build.py` renders every documented component with
its samples for inspection. Output lands under the gitignored `press-check/`.

## External libraries

Owner-declared JavaScript or CSS libraries belong under `assets` in `site.yaml`.
They must use HTTPS and Subresource Integrity. Articles themselves remain
script-free, and CSS with semantic HTML is preferred whenever it is sufficient.

The two components that need a real library ship with the engine: `nb.js` loads
KaTeX for equations and Prism for code listings, version-pinned, SRI-hashed, and
only on pages that carry the furniture, so most papers declare nothing. Declare
a library under `assets` for anything beyond them, such as more Prism languages
or a different typesetter. A press-declared copy of a library the engine also
ships wins: `nb.js` sees it in the page and loads nothing. Readers with
JavaScript off still get readable content: the TeX source of an equation, plain
monospace code, and charts as ordinary PNG images.

## The class inventory

The proof guards class names against likely typos. It builds an inventory from
`nb.css`, the composed `theme.css`, and every stylesheet declared under
`assets`, fetching each external sheet and verifying it against its pinned
integrity hash before counting its classes. Article markup that names a class no
inventoried stylesheet defines is reported as `W-DEAD-CLASS`. Classes the
engine's code highlighting injects at runtime are known built-ins. When an
external sheet cannot be fetched or verified, the check suppresses itself for
that run and notes why instead of guessing. The inventory is automatic, and
there is no user-maintained allowlist.

See [Furniture](../guides/customize/furniture.md) for when and how to design
components, and [Site reference](site.md) for the `assets` key.
