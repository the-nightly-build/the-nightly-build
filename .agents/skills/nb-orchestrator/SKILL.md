---
name: nb-orchestrator
description: >-
  Orchestrate authorized Nightly Build article work through commissioning,
  editorial roles, proof, and publication. Load after a scheduled prompt
  supplies the exact duty result or after the user assistant configures a manual
  article. Do not auto-trigger from an exploratory human request.
---

# The Nightly Build Orchestrator

Commission the authorized work, give each editorial role the context it needs,
and carry every article through publication. Resolve recoverable failures and
report an external blocker only with the evidence and manual action required.
Publish every authorized article. Exhaust the repairs you own before reporting a
blocker. Editor approval and a passing proof are the gate, never the obstacle to
work around.

## Load production in phases

1. Read [commissioning](references/commissioning.md) before planning the
   authorized articles or initializing an article.
2. Before launching the first editorial role, read
   [production and delivery](references/production-and-delivery.md).
3. Load the named role from `.agents/skills/nb-<role>/SKILL.md` when preparing
   its exact invocation. Do not make a bounded role reconstruct the repository.

Do not load a bounded role until its inputs exist. Commissioning owns article
planning and initialization. Production and delivery owns everything after the
commission is complete.

## Hold the invariants

- Process only the authorized work supplied to this run. Scheduled work is the
  exact `nb duty` result. Manual work is the article configured by the user
  assistant.
- Give every article an isolated workspace and one Article PR.
- Run independent articles in parallel when the runtime allows. Never serialize
  one article behind another.
- Complete the commission before editorial roles begin.
- Preserve each role's named input and output as the production record.
- Require editor approval and deterministic proof before PR preparation.
- Never push or merge directly to `library` or `main`.

Coordinate through messages. Record through files. Use the role package and
checkout-owned `nb` command as their current owners rather than copying their
instructions into briefs.
