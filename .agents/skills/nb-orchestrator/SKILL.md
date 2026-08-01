---
name: nb-orchestrator
description: >
  Orchestrate authorized Nightly Build article work through commissioning,
  editorial roles, proof, and publication. Load after a scheduled prompt supplies
  the exact duty result or after the user assistant configures a manual article.
  Do not auto-trigger from an exploratory human request.
---

# The Nightly Build Orchestrator

Remain the orchestrator for the complete production run. Hold the whole-paper
view, commission the authorized work, prepare each role to succeed, and keep
every article moving until it publishes or reaches an external blocker. Do not
delegate orchestration to another agent. If a genuine blocker appears, try to
resolve it before reporting the run as blocked.

## Load production in phases

1. Read [commissioning](references/commissioning.md) before planning the
   authorized articles or initializing an article.
2. Before launching the first editorial role, read
   [production and delivery](references/production-and-delivery.md) and keep it
   available through publication or a recorded external blocker.
3. Load the named role from `.agents/skills/nb-<role>/SKILL.md` when preparing
   its exact invocation. Do not make a bounded role reconstruct the repository.

Do not load a bounded role until its inputs exist. Commissioning owns article
planning and initialization; production and delivery owns everything after the
commission is complete.

## Hold the invariants

- Process only the authorized work supplied to this run. Scheduled work is the
  exact `nb duty` result; manual work is the article configured by the user
  assistant.
- Give every article an isolated workspace and one Article PR.
- Complete the commission before editorial roles begin.
- Preserve each role's named input and output as the production record.
- Require editor approval and deterministic proof before PR preparation.
- Never push or merge directly to `library`.

Messages coordinate the work; files record it. Use the role package and
checkout-owned `nb` command as their current owners rather than copying their
instructions into briefs.
