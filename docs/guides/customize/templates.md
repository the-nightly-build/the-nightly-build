# Templates

Create a template only when the proof should enforce a recurring structure.
Voice, subject, and most genres belong in series prompts; a template is the
stronger tool for invariant sections, citation geometry, chrome, or required
furniture.

Before implementation, write a design brief covering the reading job, fixed
and flexible structure, citation behavior, accessibility, responsive layout,
theme behavior, and how it differs materially from existing templates. Test
the proposal against several representative article ideas and one
counterexample that should use another template.

Then:

1. Create `press/templates/<id>/` with the files defined in
   [Template reference](../../reference/templates.md).
2. Write placeholders as instructions in uppercase, never as sample prose that
   a writer could accidentally preserve.
3. Add bespoke furniture only when the template requires it.
4. Point a test series at the template and run `nb validate`.
5. Fill a realistic test article, build the site, and inspect the result
   in the browser at narrow and wide sizes and in both themes.
6. Revise the manifest and skeleton together until the enforced contract is
   neither weaker nor broader than the design brief.

A `press/templates/<id>` package shadows a shipped template with the same ID
wholesale. Prefer a new ID unless replacement is deliberate.
