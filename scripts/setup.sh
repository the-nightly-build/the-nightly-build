#!/usr/bin/env sh
# The Nightly Build scripts/setup.sh
# Idempotent bootstrap: creates the library branch, enables Pages + auto-merge,
# validates configuration. Safe to re-run; callable by the Librarian skill.
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
command -v gh >/dev/null 2>&1 || die "gh (GitHub CLI) is required: https://cli.github.com"
command -v git >/dev/null 2>&1 || die "git is required"
command -v uv >/dev/null 2>&1 || die "uv is required: https://docs.astral.sh/uv/"
gh auth status >/dev/null 2>&1 || die "gh is not authenticated. Run: gh auth login"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "run this from your fork's checkout"

origin_url=$(git remote get-url origin 2>/dev/null) ||
	die "no 'origin' remote. Is this your fork's checkout?"
repo=$(gh repo view "$origin_url" --json nameWithOwner -q .nameWithOwner 2>/dev/null) ||
	die "no GitHub repo detected at origin ($origin_url)"
ok "repo: $repo"

# 1b. This repo is a press; the canonical repo is engine-only ------------------
UPSTREAM_REPO="${UPSTREAM_REPO:-the-nightly-build/the-nightly-build}"
if [ "$repo" = "$UPSTREAM_REPO" ]; then
	die "this is the engine repo; it runs no press. Fork it, then run setup there."
fi

# 1c. Scaffold press/ (your side of the repo) ---------------------------------
if [ ! -d press ]; then
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

Your editorial voice, composed into every article's instructions after the
house style (spec/editorial.md). Tone, register, language, assumed
background: make the paper yours. Ask your agent to interview you and fill
this in, or write it by hand.
MD
	cat >press/production.yaml <<'YAML'
# Portable role guidance. See docs/production.md.
profile: balanced
required: false
YAML
	cat >press/README.md <<'MD'
# press/ is your side of the repo

Everything here is yours; everything outside is the engine. Configure series
under series/, your voice in editorial.md, role cost in production.yaml, and
your look via site.yaml and themes/. Copy working examples from examples/ to
get started.
MD
	ok "press/ scaffolded. Configure it, or ask your agent to set you up"
else
	ok "press/ exists"
fi

# 2. Configuration validates before anything else ----------------------------
say "validating press/ configuration and the template packages"
uv run engine/validate_config.py || die "fix the configuration above, then re-run"

# 3. The library branch (orphan, empty press) --------------------------------
library_created=false
if git ls-remote --exit-code --heads origin library >/dev/null 2>&1; then
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
	git push -u origin library
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
	git fetch -q origin main library
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
	git -C "$seed_worktree" push -q origin HEAD:refs/heads/library
	git worktree remove --force "$seed_worktree"
	seed_worktree=
	rmdir "$seed_root"
	seed_root=
	ok "trigger workflows seeded onto library"
fi

# 4. GitHub Pages (Actions-based deploy; publish.yml uploads site/) ----------
if gh api "repos/$repo/pages" >/dev/null 2>&1; then
	gh api -X PUT "repos/$repo/pages" -f build_type=workflow >/dev/null 2>&1 ||
		true
	ok "GitHub Pages already enabled"
else
	if gh api -X POST "repos/$repo/pages" -f build_type=workflow >/dev/null 2>&1; then
		ok "GitHub Pages enabled (workflow deploy)"
	else
		warn "could not enable Pages via API (a private repo on the free plan"
		warn "  has no Pages: make it public, or use Pro). Then enable it at:"
		warn "  https://github.com/$repo/settings/pages, Source: GitHub Actions"
	fi
fi

# 4b. Let the library branch deploy Pages ------------------------------------
# publish.yml runs on library, but a fresh github-pages environment only lets
# the default branch deploy, so its uploads are rejected until library is
# allowed. Idempotent: skip if Pages is off or the policy already exists.
if gh api "repos/$repo/pages" >/dev/null 2>&1; then
	gh api -X PUT "repos/$repo/environments/github-pages" \
		-F "deployment_branch_policy[protected_branches]=false" \
		-F "deployment_branch_policy[custom_branch_policies]=true" >/dev/null 2>&1 || true
	if gh api "repos/$repo/environments/github-pages/deployment-branch-policies" \
		-q '.branch_policies[].name' 2>/dev/null | grep -qx library; then
		ok "library branch already cleared to deploy Pages"
	elif gh api -X POST \
		"repos/$repo/environments/github-pages/deployment-branch-policies" \
		-f name=library -f type=branch >/dev/null 2>&1; then
		ok "library branch cleared to deploy Pages"
	else
		warn "could not authorize the library branch for Pages deploys"
		warn "  add 'library' under Settings, Environments, github-pages"
	fi
fi

# 5. Auto-merge + library protection -----------------------------------------
if gh api -X PATCH "repos/$repo" -F allow_auto_merge=true >/dev/null 2>&1; then
	ok "repository auto-merge enabled"
else
	warn "could not enable auto-merge. Flip it at https://github.com/$repo/settings"
fi
# enforce_admins:true is deliberate: the night shift holds your (admin) token,
# so the required 'validate' check must bind admins too, or a prompt-injected
# run could merge past the proof. Auto-merge still works (it merges only after
# 'validate' passes). See docs/scheduling.md § Security.
if gh api -X PUT "repos/$repo/branches/library/protection" --input - >/dev/null 2>&1 <<'JSON'; then
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
	warn "  recommended: require the 'validate' check (enforce for admins) at"
	warn "  https://github.com/$repo/settings/branches"
fi

# 6. Existing libraries synchronize through the protected PR path ------------
if [ "$library_created" = false ]; then
	"$SCRIPT_DIR/sync.sh"
fi

# 7. Status ------------------------------------------------------------------
echo
ok "The presses are ready."
printf '%s\n' "
Next steps:
  1. Configure a series, or ask your agent to set you up (the Librarian skill).
  2. Rehearse:   run a press check; see skills/correspondent/SKILL.md.
  3. Schedule:   pick a path in docs/scheduling.md (a native scheduler, or the
                 universal GitHub Actions cron) and use the schedule prompt there.
  4. Morning:    your site lives at the Pages URL for $repo.
"
