# Use ChatGPT Work

ChatGPT Work sets up your paper, publishes articles, and runs scheduled editions
from a cloud checkout with no local terminal or API key.

## 1. Connect GitHub

Connect the GitHub app in ChatGPT for the account or organization that owns your
fork, allowing branch pushes and pull requests. Workspace admins may need to
enable the app or write actions. See OpenAI's guides on
[connecting GitHub](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt)
and [connected apps](https://help.openai.com/en/articles/11487775).

## 2. Publish an article now

Fork this repository, open a Work conversation, and ask:

> Help me set up my Nightly Build paper in `<owner>/<repo>` and publish my first
> article about `<topic>`. Follow the repository's instructions. Let me review
> the article before it publishes.

Work runs setup and the article pipeline in a cloud checkout. Omit the last
sentence to auto-merge after checks pass instead of opening a draft PR.

## Schedule publication

Create a recurring scheduled task in ChatGPT Work naming your fork, daily time
and timezone, and publication mode (auto-publish or draft PR):

> Schedule The Nightly Build in `<owner>/<repo>` every day at 5:00 AM Eastern.
> Follow the repository's scheduled publication instructions and auto-publish
> after checks pass.

Ensure the task starts from current remote `main` and follows
`.agents/prompts/run-scheduled-publication.md`. See
[Schedule publication](../guides/operate/schedule.md) for the canonical prompt,
and OpenAI's
[scheduled tasks guide](https://help.openai.com/en/articles/10291617-tasks-in-chatgpt)
for task controls and run history.

## After publication

Your paper publishes to `https://<owner>.github.io/<repo>/`. If `validate` never
starts on an Article PR, enable Actions in the fork's **Actions** tab, then
close and reopen the PR. See
[Troubleshoot setup and scheduling](../troubleshooting/setup-and-scheduling.md).
