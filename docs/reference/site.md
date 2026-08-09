# Site reference

`press/site.yaml` owns paper-wide presentation and delivery settings.

```yaml
title: "My Paper"
theme: press/themes/my-paper.css
appearance: auto
front: compact
footer: "Filed while you slept."
assets:
  scripts:
    - url: https://cdn.example.com/katex.min.js
      integrity: sha384-EXACT-HASH-OF-THE-PINNED-FILE
      defer: true
  styles: []
directory:
  description: "One line describing the paper."
  publish: true
```

| Key                     | Contract                                                                     |
| ----------------------- | ---------------------------------------------------------------------------- |
| `title`                 | Masthead title; defaults to "The Nightly Build"                              |
| `theme`                 | Local CSS path; defaults to the shipped newspaper theme                      |
| `appearance`            | `auto`, `light`, or `dark`                                                   |
| `front`                 | `compact` or `comfortable`                                                   |
| `footer`                | Imprint, at most 80 characters; defaults to a product credit                 |
| `assets.scripts/styles` | Entries of `url` (HTTPS), `integrity` (exact SRI hash), and optional `defer` |
| `directory.description` | Optional public description, at most 280 characters                          |
| `directory.publish`     | Boolean; set `false` to opt out of the shared directory                      |

External assets are owner-authored configuration. Scripts do not relax the
article sandbox: articles still cannot add scripts, handlers, frames, forms, or
other active content. Pin exact versions and preview both success and
no-JavaScript behavior. Declared stylesheets also join the proof's class
inventory, so a dependency's classes are never reported dead. See
[Furniture reference](furniture.md).

See [Appearance and voice](../guides/customize/appearance-and-voice.md) for
design practice and [Delivery](delivery.md) for published URLs.
