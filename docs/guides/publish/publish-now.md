# Publish an article now

Commission an article from any starting material: a topic, question, URL, set of
documents, or detailed brief.

> Write an article about birds for my paper today.

The assistant inspects your press, picks a series and template, asks only
clarifying questions that change the piece, and records the commission. Every
article needs a series; a fresh paper's **Dispatches** series accepts any
request without editing `press/`.

## Series eligibility by mode

| Mode              | How manual requests work                                                                                          |
| ----------------- | ----------------------------------------------------------------------------------------------------------------- |
| `cadence: manual` | Accepts any slug and never runs on a schedule. `items` suggests topics without restricting commissions.           |
| `open`            | Accepts any new slug. If the series has a pending commission queue, add the article to `items` to join the queue. |
| `collection`      | Accepts any configured unpublished item (add one to `items` if needed).                                           |
| `sequence`        | Accepts only the next unpublished item in order.                                                                  |
| `rolling`         | Publishes today's UTC edition early. A second same-day edition is not allowed.                                    |

Publishing early never consumes a future day's slot. A scheduled run skips a
series only if an article dated the same UTC day is already published, so a
manual article counts as that day's scheduled piece without affecting tomorrow.

After any `press/` edit validates and lands on `main`, production produces a
normal Article PR through the full CI proof and render gate. Clean PRs
auto-merge; ask to read the article first to open a draft PR that publishes when
you mark it ready.
