# Customization: look, voice, and your own templates

Everything here happens inside `press/` (see [press.md](press.md)). Engine
updates never touch it. Working examples live in `examples/`.

## Look: themes

The entire visual system reads about 14 CSS variables from one token file.
The theme contract: define the color tokens in all four blocks (light, dark,
and the two manual-override blocks); the font and radius tokens live in the
base block and are inherited. The test suite enforces parity across the
blocks.

The shipped theme pairs a pale day-sky paper with bronze accents in light
mode and a deep navy night with amber in dark mode. Keep day accents deep
if you customize: contrast is measured, and bronze #8A5C08 reads at 5.4:1
on the shipped paper while bright amber fails at 2:1.

1. Copy `engine/assets/themes/newspaper.css` to `press/themes/<name>.css`.
2. Edit the color variables in all four blocks (fonts and radius live only in
   the base block).
3. Point `press/site.yaml` at it: `theme: press/themes/<name>.css`.

The builder republishes the chosen theme as `assets/theme.css` on every
publish, so a theme change restyles the whole library, every past edition
included. Base tokens are light, the universal fallback; dark applies via
`prefers-color-scheme` or the reader's toggle. Keep it that way in custom
themes.

Fonts load from Google Fonts, the only allowed external origin besides the
engine's own assets. Swapping families changes the chrome and new editions
immediately; editions published earlier keep their frozen font links and
fall back to system faces for any family they did not load.

## Your own furniture

Editions compose pre-designed components from the shared catalog,
`templates/FURNITURE.md`: stat strips, timelines, pull quotes, position
blocks, claim cards, and more. Any component works in any template.

You can extend the catalog without touching the engine. The builder
republishes your theme CSS across the whole library on every publish, so a
class defined there restyles past editions too. Define a component below
the token blocks, on your own prefix (`nb-` is reserved):

```css
/* press/themes/mytheme.css, below the tokens */
.rs-margin-note {
  float: right;
  width: 200px;
  margin: 4px 0 12px 20px;
  font-size: 13px;
  color: var(--ink-soft);
  border-top: 2px solid var(--accent);
  padding-top: 6px;
}
```

Then instruct a desk in its `prompt.md`: "use `<div class=\"rs-margin-note\">`
for asides." Editions carry the markup, your theme carries the look, and
engine updates never touch either.

### Furniture that needs a JavaScript library

CSS covers most furniture. When a component needs a real library — a syntax
highlighter, a math typesetter, a diagram renderer — declare it in
`press/site.yaml` under `assets`, and the build injects it into every page:

```yaml
# press/site.yaml
assets:
  scripts:
    - url: https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js
      integrity: sha384-…
    - url: https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js
      integrity: sha384-…
  styles: [] # same shape, for a library that ships CSS
```

With Prism loaded, a code component is pure markup — the edition writes
`<pre><code class="language-python">…escaped code…</code></pre>` and Prism
highlights it; your theme colors the `.token` classes. The
`examples/` press does exactly this for its `rs-code` furniture.

This does not weaken the security model, because the trust boundary is
**authorship**, not the presence of JavaScript:

- Assets are declared in `site.yaml`, which lives on `main` and changes only
  through your normal review — never through an auto-merged edition PR. An
  untrusted night-shift run cannot add one.
- Every asset must be **https and Subresource-Integrity-pinned**
  (`validate_config` enforces the hash), so the browser refuses a tampered CDN
  response. Pin an exact version.
- Editions themselves stay script-free. The library the edition uses reads and
  displays markup; it never runs edition-authored code. The edition sandbox
  (no `<script>`, no event handlers) is unchanged, so auto-merge is as safe as
  ever.

Readers with JavaScript off still get the raw content (plain monospace code, an
unrendered figure), the same graceful fallback the built-in charts use.

## Voice: press/editorial.md

Your paper's voice, composed into every edition's instructions after the
house style (`spec/editorial.md`) and before any series prompt. Register,
language, assumed background, banned habits: anything that should hold
across every series. Series-specific emphasis belongs in that series'
`prompt.md`. Per-topic angles belong in tag fragments
(`press/series/_tags/`).

The layer order, first to last. Later layers specialize and never override:

```text
PROTOCOL.md > spec/editorial.md > press/editorial.md > template registry
entry > press/series/<id>/prompt.md > tag fragments > item prompt
```

## Your own templates

User templates are first class: the proof enforces whatever a registry
entry declares, so a template you define gets the same validation, CI, and
site treatment as the shipped two. Reach for one when a desk needs
structure enforced rather than described; for most genres, describing it in
the series prompt on `article` is enough (see [series.md](series.md)).

Registry entries come in two styles:

- Fixed outline: declare `sections` and each must appear exactly once.
- Flexible outline: declare anchor `sections` plus
  `flex_sections: [min, max]`, and the agent names that many additional
  sections per edition. Either way the cite rule applies to every labeled
  section except `sources` (always exempt) and any you list in the template's
  `cite_exempt` (for a non-cited section like an objectives box).

Worked example: the classic lesson template, six fixed sections for an
ordered course, rebuilt as a press template.

1. Declare it in `press/templates/registry.yaml`:

   ```yaml
   lesson:
     class: longread
     words: [1500, 4000]
     sections: [objectives, recap, teach, check, bridge, sources]
     cite_rule: per-section
     cite_exempt: [objectives] # the goals box carries no citations
     modes: [sequence]
   ```

   Rules: `sections` must include `sources`. Bands are `[low, high]`.
   `cite_rule` is `per-section` or `per-item` (needs `data-nb-item` markers).
   Two optional fields let a template declare requirements the engine would
   otherwise not know: `cite_exempt: [names]` (sections that need no citations,
   on top of the always-exempt `sources`) and `require_why: true` (each
   `data-nb-item` must carry a `data-nb-why` line, as `brief` does). The engine
   reads these from the entry, so any template can use them.
   Entries here overlay the shipped registry, so reusing a shipped id
   redefines it. The test suite exercises this exact lesson entry, so the
   walkthrough cannot drift from what the proof enforces.

2. Scaffold it as `press/templates/lesson.html`. Copy a shipped template's
   `<head>` and header chrome verbatim (asset links, nb-meta skeleton,
   eyebrow, title, dek, byline), then lay out one
   `<section data-nb-section="...">` per declared section. The objectives
   box, check box, and bridge components in `templates/FURNITURE.md` carry
   the lesson. Template files shadow shipped ones by filename. The sandbox
   applies unchanged: no scripts beyond the JSON blocks and the engine
   runtime, citations as `sup.nb-cite` anchors into numbered source entries.

3. Validate and rehearse: `python3 engine/validate_config.py`, then point a
   series at the template and run a press check before scheduling it.

## site.yaml reference

```yaml
title: "My Press" # masthead; the accent period is added
theme: press/themes/mytheme.css # default: the shipped newspaper theme
appearance: auto # auto | light | dark
front: compact # compact (default) | comfortable (deks on story cells)
email: # optional, see docs/delivery.md
  send_utc_hour: 12
```
