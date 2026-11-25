# Site reference

`press/site.yaml` configures paper-wide presentation and delivery.

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

| Key                     | Type / values               | Default               | Notes                                                               |
| ----------------------- | --------------------------- | --------------------- | ------------------------------------------------------------------- |
| `title`                 | string                      | `"The Nightly Build"` | Masthead title                                                      |
| `theme`                 | local path                  | Shipped newspaper CSS | Custom CSS under `press/themes/`                                    |
| `appearance`            | `auto` \| `light` \| `dark` | `auto`                | Color scheme mode                                                   |
| `front`                 | `compact` \| `comfortable`  | `compact`             | Front-page density (`comfortable` includes deks)                    |
| `footer`                | string (≤ 80 chars)         | Product credit        | Footer imprint                                                      |
| `assets.scripts/styles` | list of objects             | `[]`                  | Each entry needs `url` (HTTPS), `integrity` (SRI), optional `defer` |
| `directory.description` | string (≤ 280 chars)        | none                  | Optional public card description                                    |
| `directory.publish`     | boolean                     | `true`                | Set `false` to opt out of the shared directory                      |

External assets are owner-authored only and do not relax the article sandbox
(articles still cannot include scripts, event handlers, frames, or forms). Pin
exact versions and preview both JS-enabled and no-JS rendering. Declared
stylesheets join the proof's class inventory so their classes are not flagged as
dead. See [Furniture reference](furniture.md).

See [Appearance and voice](../guides/customize/appearance-and-voice.md) and
[Delivery](delivery.md).
