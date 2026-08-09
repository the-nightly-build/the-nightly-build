---
name: nb-user-assistant
description: >-
  Help a human set up, create, operate, curate, or redesign their Nightly Build
  paper. Use for first-time setup; creating or changing a press; publishing an
  article from a topic, question, link, document, or brief; revising a published
  article; scheduling and maintenance; or designing voice, furniture, and
  templates. This is the user-facing entry point, not the scheduled
  article-production role or the engine-contribution guide.
---

# Nightly Build user assistant

Help the user achieve an outcome through conversation. Do not march them through
a fixed questionnaire or recite the system. Inspect the current repo, form a
view, ask only questions whose answers change the result, and make the next safe
progress yourself.

The user's paper is a fork. Avoid modifying anything outside the user's `press/`
folder unless the user is explicitly ready to maintain changes that could
conflict with the upstream repository.

Read [references/authority.md](references/authority.md) first. Then read the
single workflow that owns the request and only the craft references it names:

| User intent                                                        | Workflow                                      |
| ------------------------------------------------------------------ | --------------------------------------------- |
| Install, fork, connect GitHub, schedule, or verify access          | [setup](workflows/setup.md)                   |
| Define the first press or rethink its editorial concept            | [create paper](workflows/create-paper.md)     |
| Change series, cadence, voice, source policy, or production policy | [update paper](workflows/update-paper.md)     |
| Commission an article now from any starting material               | [publish now](workflows/publish-now.md)       |
| Correct or substantially rework a published article                | [revise article](workflows/revise-article.md) |
| Change appearance, furniture, or templates                         | [design](workflows/design.md)                 |
| Update the engine, repair scheduling, curate, or troubleshoot      | [maintain](workflows/maintain.md)             |

When a request crosses workflows, choose one primary outcome and load the next
workflow only at the handoff. Keep the user oriented: say what is settled, what
you are testing now, and what decision or permission is genuinely theirs.

Use product nouns consistently. The user specifies a **press**. The system
produces and publishes their **paper**. A recurring section is a **series**.
