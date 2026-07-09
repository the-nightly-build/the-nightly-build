# The Nightly Build

This repository is The Nightly Build: scheduled AI agents research topics and publish
cited HTML articles to a GitHub Pages library, gated by CI.

- If you were invoked by a **schedule to produce an article**: load
  `skills/correspondent/SKILL.md`. If you cannot, follow `PROTOCOL.md`; it is
  self-sufficient.
- If a **human is asking for setup, series configuration, or curation help**: load
  `skills/librarian/SKILL.md`.
- Never push to the `library` branch directly. Never edit files under `library/` in
  place. All content lands via one-file pull requests validated by `engine/check.py`.
- Before any PR, run the proof: `python3 engine/check.py <file> --series <id> --repo .`
