# Production and delivery

Read this reference before launching an editorial role. The orchestrator owns
movement and context; each named role owns its bounded editorial decisions.

## Run the role sequence

Start `nb-writing-coach` and `nb-researcher` in parallel when isolated children
are available. Brief `nb-writer` only after both outputs exist. Brief
`nb-editor` only after the writer proves the article. Use these semantic role
identities and artifacts:

| Role ID         | Input brief       | Output                |
| --------------- | ----------------- | --------------------- |
| `writing-coach` | `brief.md`        | `voice-guide.md`      |
| `researcher`    | `brief.md`        | `evidence.md`         |
| `writer`        | `brief.md`        | `draft-handoff.md`    |
| `editor`        | `review-brief.md` | `editorial-review.md` |

The `nb-*` names identify skill packages. Production-policy keys, artifact
directories, and control signals continue to use the unprefixed role IDs in
this table.

Store each pair beneath the artifact root created by `nb start-article`:
`<role>/01/<input-and-output>`. A later invocation of that role uses the next
contiguous directory (`02`, `03`, and so on) and never overwrites an earlier
brief or output. `commission.md` and the generated `editorial-direction.md`
remain at the artifact root.

The writer and editor both receive `editorial-direction.md`; the editor also
receives the exact writer brief so instruction leakage remains visible. Every
launch begins with its named inputs and permits focused tool use. A role may
ask for more context; expand its inputs or route the question to the owner
rather than inviting repository exploration.

If isolated children are unavailable, perform the same numbered sequence in
one context and preserve the same artifacts. Isolation changes execution, not
the editorial record or gate.

## Require explicit control signals

Require one line from each invocation:

- `DONE <role> <output-path>`
- `REQUEST <role-or-owner> <one-sentence need>`
- `BLOCKED <role> <one-sentence reason>`

Messages are control signals; Markdown files are the record. A completion
signal may be lost, so accept an output without one when the named artifact is
complete and validated.

Keep launched roles under active supervision with bounded waits. If twenty
minutes pass without a relevant result, meaningful artifact change, or
concrete control message, inspect the activity and ask what is missing.
Clarify or supply context before relaunching. Confirm a role has stopped before
replacing it; interrupt, reassign, or take over only as a last resort.

## Route repairs without waiving gates

Missing voice guidance returns to the coach. Missing evidence returns to the
researcher. Prose, structure, markup, assets, and proof return through the
writer. Give every repair a new numbered brief and output, then require a fresh
writer proof and editor read.

Only an editor `DONE` with no required change settles an article. There is no
round cap, but do not repeat an unchanged attempt or prolong the loop for
optional polish. A blocked role escalates to the orchestrator, which clarifies,
reassigns, or takes over the owning work and records that resolution in the
next brief. A takeover never waives writer proof or editor approval. Stop only
for an external constraint no role can change.

## Prepare and monitor the Article PR

After editor approval and a fresh writer proof, run:

```text
nb prepare-pr <workspace>/library/<series>/<slug>.html --library <library>
```

The command creates the branch and commit from current `origin/library`, proves
the submitted diff, pushes it, and opens or describes the one Article PR. If it
prints `NB_ARTICLE_PR_REQUIRED`, use the connected GitHub tool exactly as the
handoff directs. Never recreate or edit its generated branch manually.

Monitor every Article PR through CI, merge, and the published website. Route a
failure back through production, update the existing PR, and prove it again.
The run ends only with published articles or a clearly recorded external
blocker; it never leaves an abandoned red PR.

Never merge or push to `library` directly. The protected workflow branch
created by `nb sync` is the sole non-article exception and may be used only as
that command directs.
