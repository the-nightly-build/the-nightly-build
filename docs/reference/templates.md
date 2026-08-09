# Template reference

A template is an enforceable article package under shipped `templates/<id>/` or
user-owned `press/templates/<id>/`:

```text
<id>/
├── manifest.yaml
├── skeleton.html
├── identity.md
├── furniture.md
├── furniture.css
└── samples/<slug>.html
```

`manifest.yaml` and `skeleton.html` are required. The other files add editorial
identity, bespoke furniture, and gallery examples. Skeleton placeholders are
uppercase instructions, never sample prose a writer could preserve. A press
package replaces a shipped package with the same ID wholesale.

## Shipped templates

The engine ships six packages. Each manifest carries the exact enforced
geometry. Their one-line identities:

- `article`: enforced cited prose, two anchors plus flexible sections, every
  section cited.
- `brief`: enforced structure, several tagged items, every item cited.
- `lesson`: a teaching piece framed by two anchored bookends the proof requires.
- `opinion`: an argued position that discloses its stance up front and can never
  skip the strongest opposing case.
- `paper`: reporting on one research paper, with the source's abstract and link
  anchored first.
- `unbiased`: an enforced two-sided format where a one-sided article blocks.

## Manifest

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

| Key               | Contract                                                     |
| ----------------- | ------------------------------------------------------------ |
| `about`           | Optional human-readable description; ignored by the proof    |
| `class`           | `longread` or `shortread`                                    |
| `bands`           | Optional default `[low, high]` recommendations               |
| `sections`        | Required section IDs; must include `sources`                 |
| `cite_rule`       | `per-section` or `per-item`                                  |
| `cite_exempt`     | Declared sections exempt from citation requirements          |
| `chrome`          | Exact skeleton strings that a finished article must preserve |
| `flex_components` | CSS classes required once in every flexible section          |

`bands.flex_sections` turns the outline into a flexible one: declared sections
remain anchors and the article adds a number of subject-specific sections within
the band. Without it, `sections` is a fixed outline. A series may replace
template bands field by field.

`per-item` citation geometry requires `data-nb-item` markers. A series using
`per_item_sources` may select only templates with that cite rule. Source
composition policies also require skeleton source entries to declare
`data-nb-kind="primary"` or `"secondary"`.

## Skeleton contract

The skeleton supplies the complete article shell, one typed `#nb-meta` JSON
block, engine asset links, title and dek chrome, declared sections, source
markup, and instructional placeholders. Use uppercase placeholders so they
cannot be mistaken for finished copy. Surviving placeholder text produces a
warning.

Finished articles must remain inside the article sandbox: no authored scripts,
event handlers, frames, forms, or externally hosted images. Citations use
`sup.nb-cite` anchors whose targets are source entries carrying
`data-nb-source`.

Keep `class="nb-dekline"` on the rendered dek. The proof requires it to agree
with nb-meta because the home page and feed read the metadata value.

## Selection

Every series declares either `template: <id>` or `templates: [<id>, ...]`. They
are mutually exclusive. Any scheduling mode may use any template. When several
are allowed, the production workflow chooses one for the article and records it
in nb-meta.

See [Customize templates](../guides/customize/templates.md) for the design and
testing process, and [Furniture](../guides/customize/furniture.md) for the
component scopes.
