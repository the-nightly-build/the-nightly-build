# Set up your paper

Fork this repository with **Copy the main branch only** checked, then choose a
setup path.

## Terminal with `gh`

Sign in to `gh` with an account that owns the fork, clone it, and open it in
Claude Code or Codex. Either let the agent run setup or run `./nb setup`
yourself.

With `gh`, `./nb setup`:

- creates the default `press/` and `library` branch
- seeds the publishing workflows
- enables Actions, Pages, and repository auto-merge
- attempts to protect `library` with the `validate` check

If your account cannot change a setting, setup prints the GitHub settings link
and what to update.

## ChatGPT Work

Connect GitHub in ChatGPT Work for the fork's owner account or organization,
granting permission to push branches and open pull requests. Before asking for
an article, enable workflows in the fork's **Actions** tab and set
**Settings → Pages → Source** to **GitHub Actions**.

Without `gh`, `./nb setup` creates and pushes the git branches and config but
cannot read or change repository settings. It lists Pages and Actions under
"Still to do" even if already enabled. Follow any link whose setting is missing.
Protecting `library` behind the `validate` check is recommended.

## Ask for your first article

> Help me set up my Nightly Build paper in `<owner>/<repo>` and write my first
> article about `<topic>`. Follow the repository's instructions.

`./nb setup` requires `git`, `uv`, and Python 3.10+. Do not paste a GitHub token
into chat.

The default press includes **Dispatches** (on-demand requests) plus
**News Brief** and **Feature** (scheduled runs). Your site goes live once Pages
is enabled and the first article merges. Next:
[Your first article](./first-article.md) or
[Schedule publication](../guides/operate/schedule.md).
