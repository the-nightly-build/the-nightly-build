# Set up

## What you need

- A GitHub account.
- Access to an AI model or agent capable of doing the editorial work.
- A public fork for free GitHub Pages, or a GitHub plan that supports Pages for
  a private repository.
- A scheduled runtime that can check out the repository, browse research
  sources, push a work branch, and open a pull request.

The AI you talk to during setup and the runtime that works overnight can be
different products. Treat their capabilities separately.

## Recommended setup

Start with [Ask your AI](ask-your-ai.md). A capable assistant should:

1. Establish access to your GitHub account and create a fork with only `main`.
2. Clone the fork and run `./nb setup`.
3. Help you define the first version of `press/`.
4. Configure one scheduled runtime using
   [Schedule](../guides/operate/schedule.md).
5. Offer to [verify that runtime](first-run.md) with a non-publishing smoke
   test.

When the assistant cannot perform a step itself, expect one exact manual action
from it, and it continues from your result.

`nb setup` scaffolds `press/`, creates the protected `library` branch, seeds its
publishing workflows, enables Actions, and configures GitHub Pages and
auto-merge. The local command requires `git`, an authenticated `gh`, `uv`, and
Python 3.10 or newer.

Forks start with workflows disabled. If `nb setup` warns that it could not
enable Actions, enable workflows from the fork's Actions tab before relying on
the schedule: without them the `validate` check never runs and no article can
merge.

## Manual fork-and-clone fallback

Fork this repository with **Copy the main branch only** enabled, then:

```sh
git clone https://github.com/<you>/<your-paper>.git
cd <your-paper>
./nb setup
```

Enable Actions in the fork if GitHub asks. Then ask an AI in the checkout to
help create your paper and configure its schedule.

Local validation does not prove the scheduled environment. Run the optional
smoke test there to verify its tools, research access, GitHub permissions, and
CI trigger without publishing an article.
