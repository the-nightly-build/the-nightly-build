# The Nightly Build

![The Nightly Build](assets/the-nightly-build-banner.png)

## Your own AI-researched morning paper, published while you sleep

The Nightly Build turns a GitHub repository into a personal newspaper. Describe
what you want to read, connect an agent, and get original, cited articles on
your own GitHub Pages site every morning.

**No backend and no new accounts. It can run on AI tools you already use.**

Your paper and its archive live in your fork. You own it.

> [!NOTE] Your articles will be searchable from
> [the-nightly-build.github.io](https://the-nightly-build.github.io/)
>
> If you don't want that, opt out in your `site.yaml`:
>
> ```yaml
> directory:
>   publish: false
> ```

## Get started

Give this repository URL to the AI tool you already use and say:

> Help me set up my own Nightly Build paper. Follow the repository's
> instructions, tell me only the manual action you need from me right now, and
> offer to verify the actual scheduled environment before we rely on it.

The assistant will determine what it can do, walk you through the few actions
that require your permission, interview you about the paper, configure the fork,
and verify the actual scheduled environment. The AI you talk to now and the AI
that works overnight can be different products.

Start with [Ask your AI](docs/getting-started/ask-your-ai.md), or read the full
[documentation](docs/README.md). The [feature catalog](docs/reference/README.md)
lists everything the released engine supports and where to configure it.

### Manual fallback

If your current AI cannot access GitHub, fork this repository with **Copy the
main branch only** enabled, then:

```sh
git clone https://github.com/<you>/<your-paper>.git
cd <your-paper>
./nb setup
```

Open that checkout in a coding agent and ask it to continue setup. Keep the fork
public for GitHub Pages on the free plan; private Pages requires a supporting
GitHub plan.

Before unattended publication, you can verify that the exact scheduled runtime
can reach the repository, install the required tools, browse real sources, and
open and then clean up a draft smoke-test PR. See
[Verify the scheduled runtime](docs/getting-started/first-run.md).

## How it works

![The Nightly Build architecture](assets/architecture.svg)

[Read how the pieces fit together](docs/concepts/architecture.md).

## FAQ

<!-- markdownlint-disable MD033 -->

<details>
<summary><strong>Why did you build this?</strong></summary>

---

<p>I built The Nightly Build because I could not get the morning reading I
wanted. Asking an AI for each subject was manual, checking its citations often
erased the time saved, and news coverage still began from other people's
frames. I wanted to choose what I read, how it was presented, and what evidence
it had to earn.</p>

<p>An overnight schedule makes a different production process practical: the
paper can spend an hour researching, writing, checking, and revising without
making me wait. I wanted to see how far that process could push two problems:
the writing should stop advertising that an AI wrote it, and citations should
support the claims that depend on them. It cannot guarantee truth, but it can
make unsupported work harder to publish.</p>

<p>I also wanted to test a different way to distribute software. Each paper is
a fork, so its owner holds the code, configuration, archive, and deployment
environment. The upstream project provides a system that owners change and
operate for themselves, using the AI provider they choose.</p>

---

</details>

<details>
<summary><strong>How do you keep the writing from sounding like AI?</strong></summary>

---

<p>By anchoring on strong real human writers as examples, and having an aggressive editor
that is prompted to look for common indicators of AI slop as well as bad writing, the quality
that comes out of The Nightly Build is quite a bit higher than my initial expectations. Importantly,
the agents have to pass explicitly codified gates before publishing. Words can be banned. Long
sentences with lots of parentheticals and semicolons can be blocked. Basically, every time I saw
an instance of writing that made me go "ugh that's AI", I tried my best to codify something in the
system itself to prevent it. That being said, given this is something that is customizable, I did
my best to avoid hamstringing the engine from being able to express what downstream users may want.</p>

---

</details>

<details>
<summary><strong>Can it still hallucinate?</strong></summary>

---

<p>Sort of. It is genuinely impossible to guarantee everything said is 100% correct. Though the same is
true of people. The system takes quite a bit of time and uses more tokens than you'd expect because it is
forced to actually read every single source it cites. The editor will even force sentences to be cut if they
cannot properly be demonstrated, and will meticulously try and find issues adversarially. Personally, I have
found this makes hallucinations almost go away entirely. However, I will not promise it.</p>

---

</details>

<details>
<summary><strong>What can the scheduled runtime access?</strong></summary>

---

<p>Only what you grant it. A normal run needs the web, both repository branches,
and permission to open a PR against <code>library</code>. Validation reads
untrusted article code without the scheduler's secrets. See
<a href="docs/concepts/publishing-and-security.md">Publishing and security</a>
for the full trust boundary.</p>

---

</details>

<details>
<summary><strong>Can it read paywalled or authenticated sources?</strong></summary>

---

<p>This is not something that is natively enabled, however you can set that up directly with
your respective AI agent. If you'd like to see how that might work, take a look at
<a href="https://github.com/the-nightly-build/the-nightly-build/issues/127">issue #127</a>.</p>

---

</details>

<details>
<summary><strong>Why does every article use a pull request?</strong></summary>

---

<p>The PR is both the review record and the publishing gate. It carries the
article, its assets, exact agent inputs and outputs, and validation result. Nothing
reaches <code>library</code> without passing CI. This makes it easy to audit
the process if there are issues, as well as give more direct feedback in prompts.
Additionally, PRs are a natural entity that basically every AI harness interacts with.</p>

---

</details>

<details>
<summary><strong>What does it cost?</strong></summary>

---

<p>There is no hosted-service fee. You pay for the AI runtime you choose, and
hosting can be free. One five-to-seven-article configuration took roughly
45–90 minutes per run, but provider billing and limits vary. See
<a href="docs/reference/production.md">Production cost and role models</a> for
the observed workload and controls.</p>

---

</details>

<details>
<summary><strong>Can I keep my paper private?</strong></summary>

---

<p>Yes, if your GitHub plan supports Pages for private repositories. A public
fork is the simplest free setup.</p>

---

</details>

<details>
<summary><strong>Can I change the engine?</strong></summary>

---

<p>Yes. Most changes belong in <code>press/</code>. Start with
<a href="docs/README.md">the documentation</a>. If you modify the engine
itself, you also own any conflicts when syncing upstream updates.</p>

---

</details>

<!-- markdownlint-enable MD033 -->
