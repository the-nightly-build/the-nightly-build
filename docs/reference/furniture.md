# Furniture reference

Furniture is reusable article markup with a defined communicative purpose. The
shipped catalog lives in `templates/FURNITURE.md` and works in every template.

## Custom furniture layout

```text
press/furniture/          # shared across all series
├── catalog.md
├── styles.css
└── samples/<slug>.html

press/templates/<id>/     # scoped to one template
├── furniture.md
├── furniture.css
└── samples/<slug>.html
```

Writers use only documented catalog markup, never classes guessed from CSS. Each
catalog entry must state its purpose, exact markup, and constraints.

## Requirements

- Prefix custom CSS classes with your own namespace (`nb-` is reserved for the
  engine).
- Support no-JavaScript rendering, narrow mobile viewports, light and dark
  themes, and screen readers.
- The builder merges the active theme and all furniture stylesheets into
  `assets/theme.css`, so CSS edits restyle the back catalog on rebuild.

## Preview gallery

```sh
uv run python scripts/gallery/build.py
```

Renders every documented component and its samples into the gitignored
`press-check/` directory.

## Shipped catalog and retired components

- **Active components:** Stat strip, Table, Figure, Equation, Code listing, Note
  (give each an article-specific label), Pull quote, Numbered steps, Timeline,
  Rubric, Reading card, and Quote card.
- **Retired (blocked in new articles, styled for back catalog):** Position card,
  Holds-up grid, and Claim card.
- **Media and social posts:** link to media as ordinary links; when citing a
  social post as evidence, quote only the relevant words in a linked blockquote.

## External libraries

- The engine automatically loads KaTeX (for equations) and one version-pinned
  Shiki module (for code listings, keyed off `data-language`) only when those
  components appear. If the network or grammar is unavailable, raw source stays
  visible. Static components (including Reading and Quote cards) need no JS.
- Additional press libraries belong under `assets` in `press/site.yaml` with
  HTTPS URLs and exact Subresource Integrity hashes. Articles remain
  script-free.

## Class inventory check (`W-DEAD-CLASS`)

The proof builds an automatic class inventory from `nb.css`, composed
`theme.css`, and every stylesheet declared under `assets` (fetched and verified
against its SRI hash), plus Shiki runtime built-ins. Any article class absent
from the inventory raises `W-DEAD-CLASS`. If an external sheet cannot be fetched
or verified, the check suppresses itself for that run and reports why. There is
no manual allowlist.

See [Furniture guide](../guides/customize/furniture.md) and
[Site reference](site.md).
