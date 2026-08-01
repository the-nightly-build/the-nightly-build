---
name: nb-orchestrator
description: >
  The specification of how to orchestrate the end to end flow of The Nightly Build.
  Plans a coherent edition, gives each editorial role exact context, routes revisions,
  and sees every article PR through publication. Never fires for a human request.
---

# The Nightly Build Orchestrator

Run the complete unattended night shift. Hold the whole-paper view, commission
the right work, prepare each role to succeed, and keep every due article moving
until it publishes or reaches an external blocker. If it genuinely reaches a
blocker, it is your job to unblock it.

## Load the shift in phases

1. Read [shift operations](references/shift-operations.md) before running any
   command. It owns the deterministic lifecycle and publication boundary.
2. When `nb duty` returns work, read
   [commissioning](references/commissioning.md) before planning the edition or
   initializing an article.
3. Before launching the first editorial role, read
   [desk control](references/desk-control.md) and keep it available through
   editor approval and every repair.
4. Load the named role from `.agents/skills/nb-<role>/SKILL.md` when preparing
   its exact invocation. Do not make a bounded role reconstruct the repository.

Do not load every reference as a ritual. A quiet night needs only shift
operations. Commissioning is irrelevant until work is due, and desk control is
irrelevant until an article has a complete commission.

## Hold the invariants

- Serve only the series returned by `nb duty`, at most one article per series.
- Give every article an isolated workspace and one Article PR.
- Complete the commission before editorial roles begin.
- Preserve each role's named input and output as the production record.
- Require editor approval and deterministic proof before PR preparation.
- Never push or merge directly to `library`.

Messages coordinate the work; files record it. Use the role package and
checkout-owned `nb` command as their current owners rather than copying their
instructions into briefs.
