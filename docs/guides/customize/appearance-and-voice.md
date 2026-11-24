# Appearance and voice

Paper-wide identity lives in two files:

- `press/editorial.md`: target reader, register, point of view, recurring
  editorial moves, and habits to avoid.
- `press/site.yaml`: masthead, theme, color appearance, front-page density,
  footer, and directory settings. See [Site reference](../../reference/site.md).

Write `press/editorial.md` as concrete decisions with examples and
counterexamples, not vague adjectives like "engaging". Keep paper-wide rules
here, beat territory in each series `prompt.md`, and one-off angles in item
prompts.

## Create a custom theme

1. Copy `engine/assets/themes/newspaper.css` to `press/themes/<name>.css`.
2. Update all light, dark, and manual-override token blocks.
3. Keep chart colors distinguishable without color alone and verify text and
   status contrast.
4. Set `theme: press/themes/<name>.css` in `press/site.yaml`.
5. Build a preview and inspect generated pages and several past articles in both
   color schemes.

The builder publishes the active theme as `assets/theme.css`, so theme and
furniture CSS restyle the back catalog. Because published article HTML keeps its
original font links, changing a font token alone does not load a new web font.

Themes, furniture, and templates live in `press/` without engine changes. The
site frame (top navigation, front-page layout, and series-page modes) is fixed
by the engine. Changing it requires editing engine files and leaves the
conflict-free `press/` update path.

## Pinning a series voice guide

By default, the writing coach studies exemplars fresh for every article. For a
section with a settled sound (such as a course), pin a guide with `voice_guide:`
in `series.yaml` to skip the coach run. See
[Series reference](../../reference/series.md#pinning-a-voice-guide) and
[Production](../../reference/production.md).

Write the guide as the coach would, because the writer and editor read it
directly:

- Ask your assistant to study strong writers in the series's territory rather
  than drafting cold. See `examples/series/kernels/voice-guide.md` for a working
  example.
- Open with `## How this series should sound` (written last so it references the
  selected passages).
- Give each exemplar two or three passages from different parts of the piece,
  preserving domain vocabulary, followed by two or three sentences explaining
  why each passage works. Describe the passage instead of issuing instructions.
- Do not add a list of "permitted moves" (writers treat checklists as mandatory
  quotas regardless of fit).
- Verify every quotation against its raw source per
  `.agents/skills/nb-writing-coach/SKILL.md`. No later role re-checks a pinned
  guide.
- Keep the guide general to the series, never tied to one article. Revisit it if
  the series's voice shifts.

## Banned terms (`press/banned-terms.yaml`)

The proof checks rendered article text (title, dek, headings, and body,
excluding the sources section) case-insensitively against a list of banned
strings seeded in `spec/banned-terms.yaml`. Exceeding a limit raises
`W-BANNED-TERM` (promoted to a block when the series sets `strict: true`).

Layer `press/banned-terms.yaml` over the seed by `id`:

```yaml
# Add a new ban (all fields required).
- id: synergy
  terms: [synergy, synergies]
  max: 0
  suggestion: name the mechanism. What does the combination actually do?

# Override selected fields on an engine entry.
- id: em-dash
  max: 8

# Disable an engine entry.
- id: leverage
  enabled: false
```

Write `suggestion` as an actionable rewrite instruction rather than a synonym
swap. Run `nb validate` to catch typos before a scheduled run.
