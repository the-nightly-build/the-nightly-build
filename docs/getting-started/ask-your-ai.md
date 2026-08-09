# Ask your AI

The easiest setup path is to give this repository to the AI tool you already
use. It needs to be able to work with GitHub. It does not need to be the same
tool that will run scheduled publication.

Send it this repository URL and say:

> Help me set up my own Nightly Build paper. Follow the repository's
> instructions, tell me only the manual action you need from me right now, and
> offer to verify the actual scheduled environment before we rely on it.

The assistant should first determine what it can do in the current chat. It may
be able to fork, clone, configure, push, and open pull requests itself. When it
lacks a permission, it should give you one precise action, wait for the result,
and continue from there. Never paste API keys or access tokens into chat.

You will make editorial decisions in conversation: what the paper is for, who it
serves, which recurring series it carries, and what excellent output looks like.
The assistant should test those decisions with examples rather than hand you a
generic questionnaire.

If your current AI cannot access GitHub, use the manual fork-and-clone path in
[Set up](./setup.md), then open the checkout in a coding agent and repeat the
request above.
