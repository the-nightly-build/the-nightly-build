# Ownership and branches

The repository has three distinct kinds of state.

## Your press

`press/` belongs to the paper owner. It holds title, appearance, editorial
direction, production guidance, series, prompt fragments, themes, furniture, and
custom templates. The canonical upstream repository carries no `press/`, so a
user who confines customization to this directory gets a conflict-free engine
update path.

`examples/` is documentation: a complete sample press the engine never reads.

## The engine

Everything outside `press/` and the published branch is maintained by the
software project. A fork may change it, but that fork then owns conflicts with
future upstream changes in the same files.

`main` contains the engine and the user's press. Scheduled work always begins
from current `main`. Engine updates and press edits target this branch.

## The published paper

`library` is downstream publication state. Article HTML, article assets, role
artifacts, and protected publishing workflows live there. It changes only
through its validated PR boundary. The Pages workflow builds the static site
from that state and deploys it as a GitHub Pages artifact. The generated site,
including `catalog.json`, is not committed to the branch.

Never push directly to `library`, edit its article files in place, merge it back
into `main`, or include it when forking upstream. New articles, revisions,
retractions, and workflow synchronization each have a deliberately narrow PR
shape.

Generated article branches are disposable working state. `nb prepare-pr` creates
them from the current `origin/library`, proves their one commit, and opens or
describes the exact PR. The commit and PR are evidence. The workspace under
`.nb-work/` is private production state and is never published.

See [Update the engine](../guides/operate/update-engine.md) for the fork
lifecycle and [Publishing and security](publishing-and-security.md) for the
trust boundary.
