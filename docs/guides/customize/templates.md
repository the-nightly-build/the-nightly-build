# Templates

A template is an enforceable article package. The proof blocks any article that
breaks its declared sections, bands, or citation rules. That enforcement is
permanent, so create a custom template only when a recurring article type truly
requires invariant structure, citation geometry, chrome, or required furniture.

Voice, beat, and most genres belong in series prompts using the shipped
`article` template. If a fixed outline would distort even one article you want
the series to publish, describe the genre in `prompt.md` instead.

## Creating or adopting a template

- **Start from an example package.** Copy `lesson`, `opinion`, or `unbiased`
  from `examples/templates/` into `press/templates/<id>/` to use as-is or adapt.
- **Design a new package with your assistant.** Define which sections must be
  fixed and why, where reasoning stays flexible, and what citations and
  furniture are required. Rehearse with materially different subjects in the
  browser before freezing the contract. Approved fills can serve as the
  package's sample pages.

A package in `press/templates/<id>/` shadows a shipped template with the same ID
wholesale. Pick a new ID unless you intend to replace the shipped one.

See [Template reference](../../reference/templates.md) for package files,
manifest keys, skeleton rules, and shipped templates.
