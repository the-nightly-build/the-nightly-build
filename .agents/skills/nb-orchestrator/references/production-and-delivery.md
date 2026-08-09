# Production and delivery

Coordinate the editorial roles without duplicating their judgment. The
orchestrator owns sequencing, context, and delivery. Each named role owns its
bounded editorial decisions.

## Run the edition as a parallel pipeline

Launch every commissioned article at once. When isolated children are available,
fire each article's `nb-writing-coach` and `nb-researcher` together in one burst
at the start of production. Do not stage a warmup article and do not hold one
article's roles for another's progress. The edition finishes when its slowest
article finishes, so start every article at once.

A series that sets `voice_guide` in its `series.yaml` has already settled how it
sounds. `nb start-article` writes that guide into the article's
`writing-coach/01` pair, so launch only `nb-researcher` for those articles and
brief the writer against the guide already on disk. Launching the coach anyway
spends a role invocation to restate what the press already wrote.

Within one article, brief `nb-writer` only after the voice guide and evidence
both exist. Brief `nb-editor` only after the writer proves the article. Use
these semantic role identities and artifacts:

| Role ID         | Input brief       | Output                |
| --------------- | ----------------- | --------------------- |
| `writing-coach` | `brief.md`        | `voice-guide.md`      |
| `researcher`    | `brief.md`        | `evidence.md`         |
| `writer`        | `brief.md`        | `draft-handoff.md`    |
| `editor`        | `review-brief.md` | `editorial-review.md` |

The `nb-*` names identify skill packages. Production-policy keys (called
`stages:` in `press/production.yaml`) and artifact directories use the
unprefixed role IDs in this table.

Store each pair beneath the artifact root created by `nb start-article`:
`<role>/01/<input-and-output>`. A later invocation of that role uses the next
contiguous directory (`02`, `03`, and so on) and never overwrites an earlier
brief or output. `commission.md` and the generated `editorial-direction.md`
remain at the artifact root.

Every role receives `editorial-direction.md` with its brief. The writer's brief
carries the recent openers, conclusions, and outline shapes the commission
recorded as habits not to inherit. The voice guide says how the article should
sound and never names the last article, so the habits to avoid travel with the
article rather than with the guide. The editor also receives the exact writer
brief and `commission.md`, because a leak is invisible against a file the editor
does not hold and the commission is where the reader's own situation is written
down. A `review-brief.md` carries the named inputs, your recent-pattern notes,
and the round's focus. Nothing more. The editor needs your recent-pattern notes
to catch a formula or a catchphrase, which no single article can show. Never
send a review brief without them.

Every launch begins with its named inputs and permits focused tool use. When a
role asks for more context, expand its inputs or route the question to the owner
rather than inviting repository exploration.

If isolated children are unavailable, perform the same numbered sequence in one
context and preserve the same artifacts. Isolation changes execution, not the
editorial record or gate.

## Follow each invocation

Artifacts flow role to role by name, never through your context. Ask each role
to report its output path, decision, and any missing input in plain language,
then act on the report.

Before treating an invocation as complete, verify the named pair structurally:
present in the right place, not empty. The file, not a chat phrase, is the
production record, and the consuming role judges its content. Read an artifact's
content only on exception: a report flags a contradiction, a role stalls or
repeats a failed round, or you take the work over.

Use the harness's actual task state to supervise active roles. When a role
fails, stalls, or returns without its artifact, inspect the available evidence
and supply missing context before relaunching it. Do not start a duplicate while
the original invocation is still active. Do not assume silence means progress: a
role can fail or stall without any notification. Check on any invocation that
has been silent for more than 10 minutes.

Interrupt, reassign, or take over only when the owning role cannot complete the
work.

## Route repairs without waiving gates

Missing voice guidance returns to the coach, including for a series whose guide
is pinned: the coach's repair lands in the next numbered invocation and governs
this article only. A pinned guide belongs to the paper owner, so record what it
could not support instead of editing it. Missing evidence returns to the
researcher. The writer takes back what the editor cannot settle from the
evidence record: reporting a claim needs, a broken claim the argument rests on,
a redraft where the piece needs rewriting past what editing reaches, source
assets, chart provenance, and the proof. The editor edits prose, structure, and
documented furniture itself, so expect those to be fixed in place rather than
routed. Give every repair a new numbered brief and output, then require a fresh
writer proof and editor read.

A single-owner repair needs no authored brief. Relaunch the role with a stub
that names the review or request to apply, and write real content only when
routing work between owners or resolving a loop that stopped progressing.

Only an editorial review with no required change settles an article. There is no
round cap, but do not repeat an unchanged attempt or prolong the loop for
optional polish. Clarify, reassign, or take over work a role cannot complete,
and record that resolution in the next brief. A takeover never waives writer
proof or editor approval. Stop only for an external constraint no role can
change.

## Prepare and monitor the Article PR

When the editor approves after making direct cuts, no writer round is owed for
the proof alone. Run `nb stamp` and `nb check` on the edited article yourself.
Return to the writer only if the proof demands new prose.

After editor approval and a fresh proof, deliver that article immediately. Do
not hold a finished article for the rest of the edition. Run:

```text
nb prepare-pr <workspace>/library/<series>/<slug>.html --library <library>
```

The command creates the branch and commit from current `origin/library`, proves
the submitted diff, pushes it, and opens or describes the one Article PR. If it
prints `NB_ARTICLE_PR_REQUIRED`, use the connected GitHub tool exactly as the
handoff directs. Never recreate or edit its generated branch manually. When its
proof fails, fix a mechanical fault yourself or route the finding to its owning
role. A prose change needs a fresh editor approval before preparing again.

Monitor every Article PR through CI, merge, and the published website while
other articles continue. Route a CI failure back through production, update the
existing PR, and prove it again. The run ends only with published articles or a
clearly recorded external blocker. It never leaves an abandoned red PR.

Never merge or push to `library` directly. The protected workflow branch created
by `nb sync` is the sole non-article exception and may be used only as that
command directs.
