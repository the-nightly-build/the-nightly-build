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
5. Trigger the [first test article](first-run.md) in that exact runtime.

`nb setup` scaffolds `press/`, creates the protected `library` branch, seeds its
publishing workflows, and configures GitHub Pages and auto-merge. The local
command requires `git`, an authenticated `gh`, `uv`, and Python 3.10 or newer.

## Manual fork-and-clone fallback

Fork this repository with **Copy the main branch only** enabled, then:

```sh
git clone https://github.com/YOU/YOUR-PAPER.git
cd YOUR-PAPER
./nb setup
```

Enable Actions in the fork if GitHub asks. Then ask an AI in the checkout to
help create your paper and schedule its first run.

Do not call setup complete merely because configuration validates locally. The
scheduled environment is a separate capability boundary and must produce a
real, passing Article PR before unattended publication is enabled.
