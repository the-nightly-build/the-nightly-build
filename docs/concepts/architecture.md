# Architecture

![The Nightly Build production flow](../../assets/architecture.svg)

The diagram shows the normal scheduled path from an editorial specification to
a published paper. The important boundary is the Article PR: agents may choose
and produce work, but only the deterministic engine and CI decide whether that
work is safe to publish.

## The press defines intent

The paper owner describes the publication under `press/` on `main`:

- `site.yaml` defines paper-wide identity, appearance, and delivery;
- `editorial.md` defines the shared editorial direction;
- each `series/` entry defines a recurring section, its cadence, article mode,
  source policy, prompt, and publication policy; and
- production policy selects the model profile and reasoning effort available to
  each article-making role.

This is configuration, not publication state. Scheduled work always starts
from the current `main` branch, while prior articles and the generated site live
on `library`. `nb duty` compares the press with that published catalog and
returns the work that is due. A `manual` series never becomes due on its own.

## The orchestrator owns the run

The scheduled agent follows the repository's scheduled-publication prompt,
resolves the work list, and then loads the orchestrator skill in the same
context. It does not launch an orchestrator subagent. The orchestrator turns
each authorized item into a precise commission, creates an isolated article
workspace, and manages that article until it either produces a valid PR or
reports a real blocker. A manual article enters at the same boundary after the
user assistant configures it.

When the runtime supports isolated child agents, separate articles can proceed
in parallel. A runtime without that capability can execute the same commissions
sequentially. Isolation prevents one article's sources, drafts, or instructions
from leaking into another article's context; it does not change the published
result or the CI contract.

## One article run has four editorial roles

The large box in the diagram expands one isolated article run. The
orchestrator prepares the exact input for each role, and each role records its
exact output:

1. The **writing coach** studies strong writing relevant to the commission and
   produces a practical voice guide.
2. The **researcher** finds and reads sources, verifies usable claims, and
   produces the evidence record.
3. The **writer** drafts from the commission, voice guide, evidence, and chosen
   template. The writer also runs the deterministic article proof and fixes
   failures.
4. The **editor** reads as skeptic, line editor, and reader. It can request
   prose changes, more evidence, or better source support before approval.

The arrows returning to earlier roles are deliberate. A question about voice
returns to the writing coach, an unsupported claim returns to research, and an
editorial revision returns to the writer. The orchestrator carries those
requests with exact context instead of asking one general-purpose agent to keep
the whole production process in memory.

The role artifacts make a new article auditable: they preserve the commission,
briefs, evidence, voice guidance, draft handoff, and editorial review that
produced the submitted article. They are evidence of the run, not executable
content.

## The CLI supplies deterministic operations

Agents use the repository-owned `nb` command for operations that should not
depend on model judgment. The right side of the diagram calls out four common
ones:

- searching published history for narrowly requested prior coverage;
- checking article structure, metadata, sources, prose, and PR shape;
- rendering charts and capturing permitted article assets; and
- previewing the article with its real template and site styles.

The same proof code runs locally and in CI. Local success is therefore useful
evidence before delivery, but it never replaces the server-side gate.

## Preparing an Article PR fixes the delivery shape

After editorial approval, `nb prepare-pr` starts from the current remote
`library` branch, copies the article bundle into a generated branch, runs proof
against the exact commit, and creates or describes an Article PR. A normal new
article PR contains one HTML article, its local assets, and its complete role
record.

Generated branches and `.nb-work/` are disposable production machinery. The PR
commit is the proposed publication; merging that commit is the only way an
article becomes part of the paper.

## CI is the trust boundary

Article HTML and assets are untrusted input. The Article PR workflow uses the
trusted engine and press configuration from `main`, read-only repository
permissions, and no scheduler secrets. It verifies the narrow diff shape,
article metadata, source and prose contracts, artifact history, rendered site,
and article behavior in a browser.

If CI fails, the failure returns to the orchestrator for a targeted repair and
another proof. If it passes, GitHub may merge a new article automatically only
when that series explicitly enables `autopublish`. Otherwise a person reviews
and merges it. Revisions and owner curation always require human review.

See [Publishing and security](publishing-and-security.md) for the complete
permission and threat model.

## Publication is a static build

Merging the Article PR changes `library`. The protected publication workflow
then rebuilds the paper from that branch: article pages, local assets, indexes,
search data, feeds, and `catalog.json`. GitHub Pages serves the result without
an application server or publication database.

The public directory can discover papers through their published catalog, but
the fork remains the source of truth for its press and archive. See
[Ownership and branches](ownership-and-branches.md) for the exact division of
state.

## Manual articles and revisions use the same gate

A manually commissioned article skips only the cadence decision. Once its
series configuration admits it, the orchestrator and Article PR path are the
same as for scheduled work.

A revision may be as small as a typo correction or as large as a new
LLM-assisted treatment of the article and its figures. The owner chooses the
process. The submitted PR still changes exactly one published article, may
change that article's local assets, records why the revision was needed, and
passes the normal proof and browser checks before a person can merge it.
