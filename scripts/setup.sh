#!/usr/bin/env sh
# The Nightly Build scripts/setup.sh
# Idempotent bootstrap: scaffolds the press, creates the library branch, enables
# Pages and Actions, validates configuration. Safe to re-run; callable by the
# user-assistant skill. Without a signed-in gh it does the git side and prints
# the fork settings only an admin can make.
# POSIX sh so it runs on any shell (dash, bash, zsh, ...), not just zsh.
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT"

say() { printf '→ %s\n' "$1"; }
ok() { printf '✓ %s\n' "$1"; }
warn() { printf '⚠ %s\n' "$1"; }
die() {
	printf '✗ %s\n' "$1" >&2
	exit 1
}

emit_git_handoff() {
	printf '%s\n' "NB_GIT_REQUIRED" "reason=$1" "checkout=$ROOT" >&2
	shift
	printf 'argument=%s\n' "$@" >&2
	cat >&2 <<'EOF'
Use the runtime's connected Git/GitHub tools to resolve Git access and refresh
local refs, or restore CLI Git access. Then rerun the interrupted nb command.
After a failed push, rerun preparation; temporary worktrees may be removed.
EOF
}

remote_git() {
	if git "$@"; then
		return 0
	else
		git_status=$?
		emit_git_handoff "Git remote operation failed (exit $git_status)" "$@"
		return 3
	fi
}

seed_root=
seed_worktree=
cleanup_seed() {
	if [ -n "$seed_worktree" ]; then
		git worktree remove --force "$seed_worktree" >/dev/null 2>&1 || true
		seed_worktree=
	fi
	if [ -n "$seed_root" ] && [ -d "$seed_root" ]; then
		rmdir "$seed_root" 2>/dev/null || true
	fi
}
trap cleanup_seed EXIT HUP INT TERM

# 1. Preconditions -----------------------------------------------------------
command -v git >/dev/null 2>&1 || {
	emit_git_handoff "git is not installed" "nb setup"
	exit 3
}
command -v uv >/dev/null 2>&1 || die "uv is required: https://docs.astral.sh/uv/"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "run this from your fork's checkout"

origin_url=$(git remote get-url origin 2>/dev/null) ||
	die "no 'origin' remote. Is this your fork's checkout?"

# gh makes the settings only an admin can make. Without it the git side still
# completes, and those settings are printed as clicks at the end.
have_gh=false
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
	have_gh=true
	repo=$(gh repo view "$origin_url" --json nameWithOwner -q .nameWithOwner 2>/dev/null) ||
		die "no GitHub repo detected at origin ($origin_url)"
else
	repo=$(printf '%s\n' "$origin_url" |
		sed -e 's#^https://github\.com/##' -e 's#^git@github\.com:##' -e 's#\.git$##' -e 's#/$##')
	case "$repo" in
	*/*) ;;
	*) die "origin is not a GitHub repository ($origin_url)" ;;
	esac
	warn "gh is not signed in: the fork settings that need an admin are listed at the end"
fi
ok "repo: $repo"
clicks=
click() {
	clicks="${clicks}
  - $1"
}

# 1b. This repo is a press; the canonical repo is engine-only ------------------
UPSTREAM_REPO="${UPSTREAM_REPO:-the-nightly-build/the-nightly-build}"
if [ "$repo" = "$UPSTREAM_REPO" ]; then
	die "this is the engine repo; it runs no press. Fork it, then run setup there."
fi

# 1c. Scaffold press/ (your side of the repo) ---------------------------------
scaffolded=false
if [ ! -d press ]; then
	scaffolded=true
	say "scaffolding press/ (your side of the repo)"
	mkdir -p press/series press/themes press/templates
	cat >press/site.yaml <<'YAML'
title: "The Nightly Build"
theme: engine/assets/themes/newspaper.css   # or press/themes/<yours>.css
appearance: auto   # auto | light | dark
front: compact     # compact | comfortable (deks on front-page story cells)
YAML
	cat >press/editorial.md <<'MD'
# Voice

The reader is a professional who reads widely and does not need a field
explained from the beginning. Write every piece for the people around that
reader, never for one person.

The register is a serious daily newspaper. Report first. State a judgment once
the reporting has earned it, and say where the record stops and the paper's
own reading begins.

Assume the headline has been seen, and spend the words on what it left out.
MD
	cat >press/production.yaml <<'YAML'
# Portable role guidance. See docs/reference/production.md.
profile: balanced
required: false
YAML
	mkdir -p press/series/dispatches
	cat >press/series/dispatches/series.yaml <<'YAML'
# Articles you asked for, on any subject, whenever you ask. nb duty never
# schedules this series; every article in it started as a request.
name: Dispatches
mode: open
cadence: manual
template: article
prompt: prompt.md
strict: false
min_sources: 5
bands:
  words: [800, 2500]
YAML
	cat >press/series/dispatches/prompt.md <<'MD'
Someone asked for this article. The request is the commission: find the
question it raises and establish the answer rather than mention it. Whatever
the request supplied, a link, a document, a claim, is starting material, not
the evidence: read it, then read past it until the piece stands on sources the
reader can check. Cover what was asked and nothing that was not.
MD
	mkdir -p press/series/news-brief
	cat >press/series/news-brief/series.yaml <<'YAML'
# One brief a day on the subjects in prompt.md. Rolling: the date is the item,
# and a missed day is skipped, never backfilled.
name: News Brief
mode: rolling
template: brief
prompt: prompt.md
strict: false
min_sources: 6
# Every item carries the document that owns its claim and one account from
# someone with no stake in it.
per_item_sources:
  primary: [1, null]
  secondary: [1, null]
cadence: daily
YAML
	cat >press/series/news-brief/prompt.md <<'MD'
# News Brief

What moved since yesterday in technology and the industries it is changing. A
development qualifies when it changes what can be built, what it costs, who
sells it, or what a government, court, or standards body does about it. A
launch, a funding round, or a viral post qualifies only when it changes one of
those.

Being widely discussed does not qualify an item. Apply the same test to the
story everyone is talking about.

A second source that repeats the announcement is coverage, not an independent
account. For each item, find someone with no stake in the claim who has read
the same record.
MD
	mkdir -p press/series/feature
	cat >press/series/feature/series.yaml <<'YAML'
# One longer read a day in whichever of its packages fits the material. Open:
# the beat in prompt.md chooses the subject and the orchestrator chooses the
# package, recorded per article in nb-meta.
name: Feature
mode: open
templates: [article, paper]
prompt: prompt.md
strict: false
min_sources: 5
bands:
  words: [800, 2500]
cadence: daily
YAML
	cat >press/series/feature/prompt.md <<'MD'
# Feature

One piece a day on technology, science, and the businesses built on them, in
whatever form the material deserves. Some days the subject is the week's most
consequential development, reported past the headline. Other days it is a
question nobody is asking this week that is worth understanding anyway. Do not
let the news set every day's subject.

Use `paper` when the subject is one research paper and the piece reports and
weighs it. Use `article` otherwise.

Choose the subject by what will still be useful in a month.
MD
	cat >press/README.md <<'MD'
# press/ is your side of the repo

Everything here is yours; everything outside is the engine. Three series come
scaffolded under series/: Dispatches takes the articles you ask for, News Brief
is a daily brief, and Feature is a daily longer read whose form varies. The
first paragraph of each prompt.md is that series' territory. Rewrite it to make
the paper yours, or ask your assistant to. Your reader and register live in
editorial.md, role cost in production.yaml, and your look in site.yaml and
themes/. Working examples live under examples/.
MD
	ok "press/ scaffolded. Configure it, or ask your agent to set you up"
else
	ok "press/ exists"
fi

# 2. Configuration validates before anything else ----------------------------
say "validating press/ configuration and the template packages"
"$ROOT/nb" validate || die "fix the configuration above, then re-run"

# 2b. Publish the scaffold ---------------------------------------------------
# The check reads the press from remote main, so a scaffold that exists only
# in this checkout publishes nothing. Commit it and push it now; a refused
# push becomes a step to make rather than a silent gap.
if [ "$scaffolded" = true ]; then
	branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)
	author_name=$(git config user.name 2>/dev/null || printf 'The Nightly Build')
	author_email=$(git config user.email 2>/dev/null || printf 'nightly-build@users.noreply.github.com')
	git add press
	git -c "user.name=$author_name" -c "user.email=$author_email" \
		commit -qm "press: scaffold the paper"
	if [ "$branch" = main ]; then
		remote_git push -q origin main || exit $?
		ok "press/ committed and pushed to main"
	else
		warn "press/ is committed on $branch but not on remote main"
		click "required: get the press/ commit onto remote main (git push origin main, or merge $branch into main); the check reads the press from there"
	fi
fi

# 3. The library branch (orphan, empty press) --------------------------------
library_created=false
library_ref=$(remote_git ls-remote --heads origin library) || exit $?
if [ -n "$library_ref" ]; then
	ok "library branch already exists on origin"
else
	say "creating orphan library branch"
	# Plumbing instead of 'git checkout --orphan' on purpose: an orphan
	# checkout starts from the current working tree, so it would need the
	# tree emptied and risks committing strays. Building the two-object
	# commit directly touches no checkout and is deterministic.
	blob=$(printf '' | git hash-object -w --stdin)
	subtree=$(printf '100644 blob %s\t.gitkeep\n' "$blob" | git mktree)
	tree=$(printf '040000 tree %s\tlibrary\n' "$subtree" | git mktree)
	commit=$(git commit-tree "$tree" -m "library: initialize the empty press")
	git branch --force library "$commit"
	remote_git push -u origin library || exit $?
	library_created=true
	ok "library branch pushed (contains only library/.gitkeep)"
fi

# 3b. Seed a new library before protecting it --------------------------------
# GitHub only fires pull_request triggers from workflow files present on the
# PR's base branch, and push triggers from files present on the pushed branch.
# Recurring updates take the protected PR path in sync.sh. Only a branch made
# moments ago is seeded directly, before protection exists.
if [ "$library_created" = true ]; then
	say "seeding trigger workflows onto the new library"
	remote_git fetch -q origin main library || exit $?
	seed_root=$(mktemp -d)
	seed_worktree="$seed_root/worktree"
	git worktree add -q --detach "$seed_worktree" origin/library
	mkdir -p "$seed_worktree/.github/workflows"
	for path in .github/workflows/check.yml .github/workflows/publish.yml; do
		git show "origin/main:$path" >"$seed_worktree/$path" ||
			die "origin/main does not contain $path"
	done
	git -C "$seed_worktree" add .github
	git -C "$seed_worktree" -c user.name="The Nightly Build" \
		-c user.email="nightly-build@users.noreply.github.com" \
		commit -qm "chore: seed library workflows [skip ci]"
	remote_git -C "$seed_worktree" push -q origin HEAD:refs/heads/library || exit $?
	git worktree remove --force "$seed_worktree"
	seed_worktree=
	rmdir "$seed_root"
	seed_root=
	ok "trigger workflows seeded onto library"
fi

# 4. GitHub Pages (Actions-based deploy; publish.yml uploads site/) ----------
# The deploy runs on the main ref and reads library at build time, so the
# github-pages environment needs no branch policy for library.
pages_click="required: set Pages Source to 'GitHub Actions' at https://github.com/$repo/settings/pages"
if [ "$have_gh" = false ]; then
	click "$pages_click"
elif gh api "repos/$repo/pages" >/dev/null 2>&1; then
	gh api -X PUT "repos/$repo/pages" -f build_type=workflow >/dev/null 2>&1 ||
		true
	ok "GitHub Pages already enabled"
elif gh api -X POST "repos/$repo/pages" -f build_type=workflow >/dev/null 2>&1; then
	ok "GitHub Pages enabled (workflow deploy)"
else
	warn "could not enable Pages via API (a private repo on the free plan"
	warn "  has no Pages: make it public, or use Pro)"
	click "$pages_click"
fi

# 4c. Actions run the publishing gate; forks start with workflows disabled ---
actions_click="required: enable workflows at https://github.com/$repo/actions (forks start with them off)"
if [ "$have_gh" = false ]; then
	click "$actions_click"
elif [ "$(gh api "repos/$repo/actions/permissions" -q .enabled 2>/dev/null)" = "true" ]; then
	ok "GitHub Actions enabled"
elif gh api -X PUT "repos/$repo/actions/permissions" -F enabled=true >/dev/null 2>&1; then
	ok "GitHub Actions enabled (forks start with workflows disabled)"
else
	warn "could not enable GitHub Actions. Without it the 'validate' check never"
	warn "  runs and no article can merge"
	click "$actions_click"
fi

# 5. Auto-merge + library protection -----------------------------------------
# Article PRs are merged by the check itself. nb sync asks GitHub to auto-merge
# its own PR once 'validate' passes, which needs the repository setting; without
# it, sync hands that PR to the runtime's GitHub tool instead.
if [ "$have_gh" = true ]; then
	if gh api -X PATCH "repos/$repo" -F allow_auto_merge=true >/dev/null 2>&1; then
		ok "repository auto-merge enabled"
	else
		warn "could not enable auto-merge; nb sync will hand its PR to your GitHub tool"
	fi
fi
# enforce_admins:true is deliberate: the scheduled runtime holds your (admin) token,
# so the required 'validate' check must bind admins too, or a prompt-injected
# run could merge past the proof. Auto-merge still works (it merges only after
# 'validate' passes). See docs/concepts/publishing-and-security.md.
protect_click="recommended: require the 'validate' check on library, enforced for admins, at https://github.com/$repo/settings/branches"
if [ "$have_gh" = false ]; then
	click "$protect_click"
elif gh api -X PUT "repos/$repo/branches/library/protection" --input - >/dev/null 2>&1 <<'JSON'; then
{
  "required_status_checks": { "strict": false, "contexts": ["validate"] },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
	ok "library branch protected (the editor's check gates every merge, incl. admins)"
else
	warn "could not protect library (needs admin / paid plan on private repos)"
	click "$protect_click"
fi

# 6. Existing libraries synchronize through the protected PR path ------------
if [ "$library_created" = false ]; then
	sync_rc=0
	"$ROOT/nb" sync || sync_rc=$?
	if [ "$sync_rc" -eq 3 ]; then
		warn "the publishing workflows need a protected update: open and merge"
		warn "  the sync PR described above, then re-run nb setup"
	elif [ "$sync_rc" -ne 0 ]; then
		die "nb sync failed; fix the failure above, then re-run nb setup"
	fi
fi

# 7. Status ------------------------------------------------------------------
owner=$(printf '%s' "${repo%%/*}" | tr '[:upper:]' '[:lower:]')
name=$(printf '%s' "${repo#*/}" | tr '[:upper:]' '[:lower:]')
if [ "$name" = "$owner.github.io" ]; then
	site_url="https://$owner.github.io/"
else
	site_url="https://$owner.github.io/$name/"
fi
echo
if [ -n "$clicks" ]; then
	ok "The git side is done."
	printf '%s\n' "
Still to do:$clicks
  Without Pages nothing deploys; without workflows the 'validate' check never
  runs and no article can merge. Re-running nb setup with gh signed in makes
  and verifies them instead."
else
	ok "The presses are ready."
fi
printf '%s\n' "
Next steps:
  1. Ask for an article: open this checkout in your AI tool and say what you
                 want to read. The Dispatches series takes it; see
                 docs/getting-started/ask-your-ai.md.
  2. Morning paper, when you want one: schedule the run. News Brief and
                 Feature are already daily; see docs/guides/operate/schedule.md.
  3. Your site:  $site_url, once Pages is on and the first article merges.
"
