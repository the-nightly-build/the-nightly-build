# Template reference

A template is an enforceable article package under shipped `templates/<id>/` or
press-owned `press/templates/<id>/`:

```text
<id>/
├── manifest.yaml       # required
├── skeleton.html       # required
├── identity.md         # optional editorial identity
├── furniture.md        # optional template-scoped furniture catalog
├── furniture.css       # optional template-scoped furniture styles
└── samples/<slug>.html # optional gallery samples
```

A press package in `press/templates/<id>/` replaces a shipped package with the
same ID wholesale.

## Shipped and example packages

| Package    | Location               | Purpose                                                                      |
| ---------- | ---------------------- | ---------------------------------------------------------------------------- |
| `article`  | `templates/` (shipped) | Cited prose: two anchor sections plus flexible sections, every section cited |
| `brief`    | `templates/` (shipped) | Tagged items, every item cited                                               |
| `paper`    | `templates/` (shipped) | Single research paper report with source abstract and link anchored first    |
| `lesson`   | `examples/templates/`  | Teaching piece framed by two required bookend sections                       |
| `opinion`  | `examples/templates/`  | Argued position disclosing stance upfront and addressing the counter-case    |
| `unbiased` | `examples/templates/`  | Enforced two-sided format that blocks one-sided articles                     |

Example packages are not in the shipped registry. Copy one whole into
`press/templates/<id>/` before referencing it (otherwise `nb validate` fails and
names the copy to make). Once copied, edit it freely.

## Manifest (`manifest.yaml`)

```yaml
about: "A short human description."
class: longread
bands:
  words: [1200, 3000]
  items: [3, 8]
  flex_sections: [1, 4]
sections: [orientation, sources]
cite_rule: per-section
cite_exempt: [orientation]
chrome:
  - '<body class="nb-article">'
flex_components: [my-required-component]
```

| Key               | Contract                                                          |
| ----------------- | ----------------------------------------------------------------- |
| `about`           | Optional human description (ignored by the proof)                 |
| `class`           | `longread` or `shortread`                                         |
| `bands`           | Optional default `[low, high]` ranges; overridable field by field |
| `sections`        | Required section IDs (must include `sources`)                     |
| `cite_rule`       | `per-section` or `per-item`                                       |
| `cite_exempt`     | Declared sections exempt from citation rules                      |
| `chrome`          | Exact skeleton strings a finished article must preserve           |
| `flex_components` | CSS classes required once in every flexible section               |

- Setting `bands.flex_sections` turns `sections` into anchors with flexible
  sections between them; omitting it makes `sections` a fixed outline.
- `per-item` citation geometry requires `data-nb-item` markers. Series using
  `per_item_sources` may only select `per-item` templates.
- Series using `sources_by_kind` or `per_item_sources` require skeleton source
  entries to carry `data-nb-kind="primary"` or `"secondary"`.

## Skeleton contract (`skeleton.html`)

- Provide the full article shell, one typed `#nb-meta` JSON block, engine asset
  links, title/dek chrome, declared sections, source markup, and **uppercase**
  instructional placeholders (surviving placeholder text triggers a warning).
- Keep `class="nb-dekline"` on the rendered dek; the proof enforces agreement
  with `nb-meta` for the home page and feeds.
- Citations use `sup.nb-cite` links pointing to source entries marked with
  `data-nb-source`.
- Articles must obey the sandbox: no authored scripts, event handlers, frames,
  forms, or externally hosted images.

## Series selection

Each series declares `template: <id>` or `templates: [<id>, ...]` (mutually
exclusive). Any scheduling mode works with any template. When multiple templates
are listed, production picks one per article and stores it in `nb-meta`.

See [Customize templates](../guides/customize/templates.md) and
[Furniture](../guides/customize/furniture.md).
