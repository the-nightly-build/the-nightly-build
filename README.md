# The Nightly Build

![The Nightly Build](assets/the-nightly-build-banner.png)

## Your own AI-researched morning paper, published while you sleep

The Nightly Build turns a GitHub repository into a personal newspaper. Describe
what you want to read, connect an agent, and get original, cited articles on
your own GitHub Pages site every morning.

**No backend and no new accounts. It can run on AI tools you already use.**

Your paper and its archive live in your fork. You own it.

> [!NOTE]
> Your articles will be searchable from [the-nightly-build.github.io](https://the-nightly-build.github.io/)
>
> If you don't want that, disable it via setting `directory.publish = false` in your `site.yaml`

## How it works

![The Nightly Build architecture](assets/architecture.svg)

## Get started

### 1. Fork and bootstrap

Fork this repository with **Copy the main branch only** enabled. Keep the fork
public if you want to use GitHub Pages on the free plan.

Clone the fork and run the setup script (or ask your agent to do this in the next step):

```sh
git clone https://github.com/<you>/<your-paper>.git
cd <your-paper>
./setup.sh
```

The script scaffolds `press/`, creates the empty `library` branch, seeds its
workflows, and configures GitHub Pages and auto-merge. It requires `git`,
`gh` (authenticated), `uv`, and Python 3.10+.

### 2. Configure your paper

Ask your agent to **set me up**, or copy a starting point from [`examples/`](examples/README.md).
Your paper lives in one small configuration tree:

```text
press/
├── site.yaml                 # title and appearance
├── editorial.md              # paper-wide voice
└── series/<id>/
    ├── series.yaml           # cadence and publishing rules
    └── prompt.md             # what this section covers
```

See [Your paper](docs/press.md) and [Series](docs/series.md) for the full
configuration model.

### 3. Rehearse once

Ask your agent for a **press check**. It runs the article workflow locally,
builds a preview, and lets you tune your paper before anything is published.
This is useful for getting a feel for your prompts as well as the HTML components
that come with the repo and/or your own custom ones, which you can read about in
[Customization](docs/customization.md).

### 4. Schedule the night shift

Ask your agent to help you schedule the night shift. You'll need to make sure
it is set up with wider internet access permissions and the ability to raise
a PR in your repository.

The run derives its work from `press/`, so you do not need to update the schedule
when you add or pause a section. The automation only needs to be updated if the
[automation prompt](docs/scheduling.md#the-schedule-prompt) changes.

Choose a provider schedule or the universal GitHub Actions path in
[Scheduling](docs/scheduling.md). [Harnesses](docs/harnesses.md) lists the
supported agents and how their usage is billed.

### 5. Read your paper

The night shift opens pull requests against `library`. Once the first article
merges, GitHub Pages publishes the newsstand, archive, search index, and feeds.
See [Delivery](docs/delivery.md) for the URLs and feed formats.

### 6. Iterate until you love it

The first set of articles you get might not be perfect. You may want some formatting changes.
A less formal voice. Different topics, you name it. The point is, it will probably take a few
days to end up with a `press/` configuration that you love. Below are where you can configure:

- Change the title and appearance in `press/site.yaml`.
- Set the paper-wide voice in `press/editorial.md`.
- Add sections, beats, cadence, and source requirements under `press/series/`.
- Customize themes, furniture, and templates in `press/`.

For inspiration, take a look at [examples](examples/README.md) as a living reference. Or even
read [my personal fork](https://github.com/RyanSaxe/the-nightly-build/tree/main/press).

[Customization](docs/customization.md) covers the extension points without requiring engine changes.

## FAQ

<!-- markdownlint-disable MD033 -->

<details>
<summary><strong>How do you keep the writing from sounding like AI?</strong></summary>

---

<p>By anchoring on strong real human writers as examples, and having an aggressive editor
that is prompted to look for common indicators of AI slop as well as bad writing, the quality
that comes out of The Nightly Build is quite a bit higher than my initial expectations. Importantly
the agents have to pass explicitly codified gates before publishing. Words can be banned. Long
sentences with lots of parentheticals and semicolons can be blocked. Basically, every time I saw
an instance of writing that made me go "ugh that's AI", I tried my best to codify something in the
system itself to prevent it. That being said, given this is something that is customizable, I did
my best to avoid ham-stringing the engine from being able to express what downstream users may want.</p>

---

</details>

<details>
<summary><strong>Can it still hallucinate?</strong></summary>

---

<p>Sort of. It is genuinely impossible to guarantee everything said is 100% correct. Though the same is
true of people. The system takes quite a bit of time and uses more tokens than you'd expect because it is
forced to actually read every single source it cites. The editor will even force sentences to be cut if they
cannot properly be demonstrated, and will meticulously try and find issues adversarially. Personally, I have
found this leads to hallucinations to almost go away entirely. However, I am not going to claim that, as I
am sure there will be instances of incorrectness.</p>

---

</details>

<details>
<summary><strong>What can the night shift access?</strong></summary>

---

<p>Only what you grant it. A normal run needs the web, both repository branches,
and permission to open a PR against <code>library</code>. Validation reads
untrusted article code without the scheduler's secrets. See
<a href="docs/scheduling.md">Scheduling</a> for the full trust boundary.</p>

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
article, earned assets, production record, and validation result. Nothing
reaches <code>library</code> without passing CI. This makes it easy to audit
the process if there are issues, as well as give more direct feedback in prompts.
Additionally, PRs are a natural entity that basically every AI harness interacts with.</p>

---

</details>

<details>
<summary><strong>What does it cost?</strong></summary>

---

<p>The Nightly Build has no hosted service or fee. You pay for the agent or model
runner you choose. More articles, broader research, and longer drafts use more
tokens. The optional <a href="docs/production.md">production policy</a> routes
article roles to portable model tiers while leaving the automation's orchestrator
under your control. See <a href="docs/harnesses.md">Harnesses</a> for runner and
billing options.</p>

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

<p>Yes. Most changes belong in <code>press/</code>; start with
<a href="docs/customization.md">Customization</a>. If you modify the engine
itself, you also own any conflicts when syncing upstream updates.</p>

---

</details>

<!-- markdownlint-enable MD033 -->
