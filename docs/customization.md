# Customization: look, voice, and your own templates

Everything here happens inside `press/` (see [press.md](press.md)). Engine
updates never touch it. Working examples live in `examples/`.

Most papers only need three files: `site.yaml` for the title and appearance,
`editorial.md` for the paper-wide voice, and each series' `prompt.md` for its
beat. Use the rest of this page when you want to change the visual system or
add reusable furniture and templates.

## Look: themes

The entire visual system reads about two dozen CSS variables from one token
file. The theme contract: define the color tokens in all four blocks (light,
dark, and the two manual-override blocks); the font and radius tokens live in
the base block and are inherited. The test suite enforces parity across the
blocks.

Beyond the page tokens, a theme carries two data-color groups. `--chart-1`
through `--chart-6` are the categorical series colors for charts, in a
fixed, colorblind-validated order: assign them in sequence, never
re-sorted.
`--ok`, `--warn`, and `--bad` are semantic status inks (grade verdicts,
holds-up labels, score meters). The suite checks their contrast in every
block: chart tokens hold at least 3:1 against `--bg` and `--panel`, status
tokens at least 4.5:1, so a custom theme cannot ship unreadable legends or
status text.

The shipped theme pairs a pale day-sky paper with bronze accents in light
mode and a deep navy night with amber in dark mode. Keep day accents deep
if you customize: contrast is measured, and bronze #8A5C08 reads at 5.4:1
on the shipped paper while bright amber fails at 2:1.

1. Copy `engine/assets/themes/newspaper.css` to `press/themes/<name>.css`.
2. Edit the color variables in all four blocks (fonts and radius live only in
   the base block).
3. Point `press/site.yaml` at it: `theme: press/themes/<name>.css`.

The builder republishes the chosen theme as `assets/theme.css` on every
publish, so a theme change restyles the whole library, every past article
included. Base tokens are light, the universal fallback; dark applies via
`prefers-color-scheme` or the reader's toggle. Keep it that way in custom
themes.

The shipped templates and generated site chrome load the default families from
Google Fonts. Theme tokens choose the font stack, but they do not add a new
font import: a custom web font needs a matching `<link>` in the template and,
for generated pages, an engine change. Existing articles keep the font links
from the templates they were written with and fall back to system faces when a
requested family is unavailable. Google Fonts is the only external origin the
article sandbox allows besides the engine's own assets path; page-injected
`assets:` libraries below are a separate, owner-authored path with their own
rules.

## Your own furniture

Articles compose pre-designed components from the engine's base catalog,
`templates/FURNITURE.md`: stat strips, timelines, pull quotes, position
blocks, claim cards, and more. Any component in it works in any template.

A drafter's furniture palette composes three scopes, so you extend the catalog
without touching the engine:

- **Engine base**: `templates/FURNITURE.md`, always available.
- **Shared press furniture**: `press/furniture/`, a `catalog.md` (one read is
  the whole palette) beside a `styles.css`. Anything every section might reach
  for lives here.
- **Template-bespoke**: a `furniture.md` + `furniture.css` inside a template's
  own folder (`press/templates/<id>/`), for a component only that template
  renders.

The builder concatenates every CSS owner (your theme plus all furniture files)
into the single `assets/theme.css` on each publish, so a class defined in any of
them restyles past articles too. Define a component on your own prefix (`nb-` is
reserved):

```css
/* press/furniture/styles.css */
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

Catalogue it in `press/furniture/catalog.md` (a heading and a markup sample),
then instruct a section in its `prompt.md`: "use `<div class=\"rs-margin-note\">`
for asides." Articles carry the markup, your furniture carries the look, and
engine updates never touch either.

The proof also checks class names for likely LLM typos. It parses every local
stylesheet that ships in `theme.css` and emits `W-DEAD-CLASS` when article
markup names a class that no stylesheet defines. Classes supplied by the
engine's code-highlighting furniture (`language-*` and `token*`) are understood
as built-ins. This is feedback, not a user-maintained class allowlist.

### Furniture that needs a JavaScript library

CSS covers most furniture, and the two components that need a real library,
the equation (KaTeX) and the code listing (Prism), ship with the engine:
`nb.js` loads each version-pinned, SRI-hashed, and only on pages that carry
the furniture. For anything beyond them (more Prism languages than the
shipped python and javascript, a diagram renderer, another typesetter),
declare the library in `press/site.yaml` under `assets`, and the build
injects it into every page:

```yaml
# press/site.yaml
assets:
  scripts:
    - url: https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js
      integrity: sha384-…
    - url: https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-rust.min.js
      integrity: sha384-…
  styles: [] # same shape, for a library that ships CSS
```

Styles in `assets.styles` are included in the proof's class inventory after the
bytes pass SRI verification. The engine parses CSS selectors; it does not load
or execute scripts to discover classes. If a pinned stylesheet cannot be
fetched, fails its hash, contains an import, or cannot be parsed completely,
the proof records a note and suppresses definitive dead-class warnings rather
than guessing that a class is invalid.

A press-declared copy of a library the engine also ships wins: `nb.js` sees
it in the page and loads nothing, so pinning Prism with extra languages (as
above; Prism components load against your copy of its core) or a different
KaTeX version behaves as declared. The component stays pure markup either
way. The article writes `<pre><code class="language-rust">…escaped
code…</code></pre>`, and the highlighter finds it.

This does not weaken the security model, because the trust boundary is
**authorship**, not the presence of JavaScript:

- Assets are declared in `site.yaml`, which lives on `main` and changes only
  through your normal review, never through an auto-merged article PR. An
  untrusted night-shift run cannot add one.
- Every asset must be **https and Subresource-Integrity-pinned**
  (`validate_config` enforces the hash), so the browser refuses a tampered CDN
  response. Pin an exact version.
- Articles themselves stay script-free. The library the article uses reads and
  displays markup; it never runs article-authored code. The article sandbox
  (no `<script>`, no event handlers) is unchanged, so auto-merge is as safe as
  ever.

Readers with JavaScript off still get the raw content (plain monospace code,
the TeX source of an equation), and the engine's own charts are plain PNGs,
readable everywhere.

## Voice: press/editorial.md

Your paper's voice, composed into every article's instructions after the
house style (`spec/editorial.md`) and before any series prompt. Anything that
should hold across every series belongs here: register, language, assumed
background, banned habits, and whatever else your paper will not leave to the
night shift's judgment. Series-specific emphasis belongs in that series'
`prompt.md`. Per-topic angles belong in tag fragments
(`press/series/_tags/`).

The layer order, first to last. Later layers specialize and never override:

```text
PROTOCOL.md > spec/editorial.md > spec/headlines.md > press/editorial.md >
template manifest > template identity > press/series/<id>/prompt.md
> tag fragments > item prompt
```

The template identity (`<id>/identity.md`) is the prose guidance carried in the
template package itself (its editorial character, opener, and structure notes),
distinct from the machine contract in the `manifest.yaml` above it. A
`press/templates/` package supplies its own.

## Banned terms: press/banned-terms.yaml

One banned habit gets mechanical teeth. The proof counts every article against
a list of ruled-out strings, each entry carrying the exact strings to match,
the most uses an article may keep, and the note the writer sees when the count
runs over. The engine seeds the list in `spec/banned-terms.yaml` (the em-dash
as a default connective, "leverage", "load-bearing"); an over-limit count is a
`W-BANNED-TERM` warning, promoted to a block when the series sets `strict`.
Counting covers the rendered text (title, dek, headings, body) minus the
sources section, case-insensitively.

Your press layers `press/banned-terms.yaml` over the seed, by `id`:

```yaml
# A new id adds a ban. State every field: the strings to count, the
# ceiling, and the note the writer acts on.
- id: synergy
  terms: [synergy, synergies]
  max: 0
  suggestion: name the mechanism; what does the combination actually do?

# Reusing an engine id changes only the fields you state.
- id: em-dash
  max: 8

# Retire an engine entry outright.
- id: leverage
  enabled: false
```

Write each `suggestion` as the correction you would give a writer, and aim it
at the rewrite. A ban enforced by swapping in a synonym or a comma trades one
tell for another; the sentence that reached for the term is the thing to fix.
`validate_config.py` checks both files, so a typo surfaces before a nightly
run trips on it.

## Your own templates

A template is a self-contained folder, its folder name the template id,
under `templates/` (shipped) or `press/templates/` (yours):

```text
press/templates/<id>/
  manifest.yaml    the machine contract the proof enforces (required)
  skeleton.html    the scaffold the agent renders (required)
  identity.md      the template's voice and character (optional)
  furniture.md     bespoke furniture catalogue for this template (optional)
  furniture.css    bespoke furniture styles (optional)
```

A `press/templates/<id>/` package replaces a shipped `templates/<id>/` of the
same id **wholesale**. User templates are first class: the proof enforces
whatever the manifest declares, so a template you define gets the same
validation, CI, and site treatment as the shipped templates. Reach for one when a
section needs structure enforced rather than described; for most genres,
describing it in the series prompt on the `article` template is enough (see
[series.md](series.md)).

Manifests come in two styles:

- Fixed outline: declare `sections` and each must appear exactly once.
- Flexible outline: declare anchor `sections` plus
  `bands.flex_sections: [min, max]`, and the agent names that many additional
  sections per article. Either way the cite rule applies to every labeled
  section except `sources` (always exempt) and any you list in the template's
  `cite_exempt` (for a non-cited section like an objectives box).

Worked example: an `interview`, a Q&A transcript with a short introduction,
built as your own template. It looks nothing like a shipped template, so it
shadows none of them, and it still exercises the machinery this section
teaches: a fixed outline, a section that carries no citations, and skeleton
chrome the writer cannot reword.

1. Write `press/templates/interview/manifest.yaml`:

   ```yaml
   class: longread
   bands:
     words: [1200, 3000]
   sections: [preamble, exchange, sources]
   cite_rule: per-section
   cite_exempt: [preamble] # the intro carries no citations
   ```

   Rules: `sections` must include `sources`. Bands are `[low, high]` defaults
   under `bands:` and a series may replace them field by field in its own
   `bands:` block, including in either direction; omitted means no default.
   `cite_rule` is `per-section` or `per-item` (needs `data-nb-item` markers).
   An optional `cite_exempt: [names]` lets a template declare sections that
   need no citations, on top of the always-exempt `sources`. A
   `chrome:` list names raw substrings of the skeleton (the body class,
   fixed labels, fixed headings) that must survive the fill verbatim. The
   proof blocks an article that alters them, so a writer can never unstyle
   a page by rewording its furniture. `validate_config.py` requires each
   string to appear in the skeleton, so rewording skeleton chrome without
   updating this list fails at your desk, not the writer's. The engine
   reads these from the manifest, so any template can use them. Any scheduling
   mode can use any template: a series declares `template:` or a `templates:`
   choice list, and the correspondent records the selected package in
   `nb-meta`. An optional
   `about:` one-liner documents the template for a browsing human; the engine
   ignores it. The test suite exercises this exact interview manifest, so the
   walkthrough cannot drift from what the proof enforces.

2. Scaffold `press/templates/interview/skeleton.html`. Copy a shipped skeleton's
   `<head>` and header chrome verbatim (asset links, nb-meta skeleton,
   eyebrow, title, dek, byline). Keep `class="nb-dekline"` on whatever element
   renders the dek: the front page and the feed print nb-meta's dek, and the
   proof blocks an article whose rendered dekline says something else. Lay out one
   `<section data-nb-section="...">` per declared section. Write placeholder
   prose as instruction (what the slot must contain), never as a model
   sentence: a placeholder that performs its slot gets lifted verbatim, and
   the lifted line then opens that section in every article the template
   renders. Set every placeholder in ALL CAPS, the shipped convention, so
   instruction can never be mistaken for copy; rendered labels a component
   owns (a heading like "Sources", a component's fixed label) stay sentence
   case. The proof backstops the convention: a caps run surviving into an
   article's prose is a `W-PLACEHOLDER` warning. The same holds for
   `identity.md`: describe the move, do not perform it. The note
   component in `templates/FURNITURE.md` carries any labeled aside the
   exchange needs, like an editor's note. The sandbox applies unchanged: no scripts beyond the JSON blocks
   and the engine runtime, citations as `sup.nb-cite` anchors into numbered
   source entries. Give each placeholder source entry a
   `data-nb-kind="primary"` or `"secondary"` next to its `data-nb-source`, as
   the shipped skeletons do: it is how a series constrains its source mix
   (`sources_by_kind`, `per_item_sources` in [series.md](series.md)), and
   `validate_config.py` rejects a series that sets one of those bands on a
   template whose skeleton omits the attribute. Optionally add `identity.md`
   (the template's voice) and
   `furniture.md` + `furniture.css` for bespoke components only this template
   renders.

3. Validate and rehearse: `uv run engine/validate_config.py --repo .`, then point a
   series at the template and run a press check before scheduling it.

## What stays with the engine

Themes, furniture, and templates are yours to define in `press/` with no engine
edit. The site's frame is not. The top nav (`Today`, `Sections`, `Search`,
`RSS`), the front-page night layout, and the way each of the four series-page
modes renders are all fixed in `engine/build_site.py`. Wanting a new nav entry
(an "About" page), a different front page, or a timeline-style index means
editing the engine, which takes you off the conflict-free `press/`-only update
path. The look and structure inside a page are unbounded; the page layout and
navigation are the ceiling of "customize within `press/`".

## site.yaml reference

```yaml
title: "My Paper" # masthead; the accent period is added
theme: press/themes/mytheme.css # default: the shipped newspaper theme
appearance: auto # auto | light | dark
front: compact # compact (default) | comfortable (deks on story cells)
footer: "Filed while you slept." # left imprint on every page (<= 80 chars);
# unset -> "A Nightly Build paper"
assets: # optional; page-injected JS/CSS libraries (see "Furniture that needs
  # a JavaScript library" above). Every entry is https + SRI-pinned.
  scripts: []
  styles: []
directory: # optional, see docs/delivery.md
  description: "One line for your directory card (<= 280 chars)."
  publish: true # set false to opt out of the shared directory
```
