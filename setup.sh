#!/usr/bin/env sh
# The Nightly Build setup.sh
# Idempotent bootstrap: creates the library branch, enables Pages + auto-merge,
# validates configuration. Safe to re-run; callable by the Librarian skill.
# POSIX sh so it runs on any shell (dash, bash, zsh, ...), not just zsh.
set -eu

say() { printf '→ %s\n' "$1"; }
ok() { printf '✓ %s\n' "$1"; }
warn() { printf '⚠ %s\n' "$1"; }
die() {
	printf '✗ %s\n' "$1" >&2
	exit 1
}

# 1. Preconditions -----------------------------------------------------------
command -v gh >/dev/null 2>&1 || die "gh (GitHub CLI) is required: https://cli.github.com"
command -v git >/dev/null 2>&1 || die "git is required"
command -v python3 >/dev/null 2>&1 || die "python3 is required"
gh auth status >/dev/null 2>&1 || die "gh is not authenticated. Run: gh auth login"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "run this from your fork's checkout"

repo=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null) ||
	die "no GitHub repo detected. Is origin set to your fork?"
ok "repo: $repo"

python3 -c 'import yaml' 2>/dev/null ||
	die "PyYAML is required: pip install pyyaml (with uv: uv pip install pyyaml)"

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

# Morning email delivery (also requires the MAIL_* repo secrets; see
# docs/delivery.md). Without this block, the Atom feed is the push channel.
# email:
#   send_utc_hour: 12
YAML
	cat >press/editorial.md <<'MD'
# Voice

Your editorial voice, composed into every article's instructions after the
house style (spec/editorial.md). Tone, register, language, assumed
background: make the paper yours. Ask your agent to interview you and fill
this in, or write it by hand.
MD
	cat >press/README.md <<'MD'
# press/ is your side of the repo

Everything here is yours; everything outside is the engine. Configure series
under series/, your voice in editorial.md, your look via site.yaml and
themes/. Copy working examples from examples/ to get started.
MD
	ok "press/ scaffolded. Configure it, or ask your agent to set you up"
else
	ok "press/ exists"
fi

# 2. Configuration validates before anything else ----------------------------
say "validating press/ configuration and the template registry"
python3 engine/validate_config.py || die "fix the configuration above, then re-run"

# 3. The library branch (orphan, empty press) --------------------------------
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
	ok "library branch pushed (contains only library/.gitkeep)"
fi

# 3b. Seed trigger workflows onto library ------------------------------------
# GitHub only fires pull_request triggers from workflow files present on the
# PR's base branch, and push triggers from files present on the pushed branch.
# So the editor (check.yml) and the press (publish.yml) must ALSO exist on
# library. They are pure triggers: every real instruction checks out engine
# and templates from main, so no engine logic lands on library.
# Re-running setup.sh re-syncs them after trigger/checkout-step changes on main.
say "syncing trigger workflows onto library"
git fetch -q origin library
wt="$(mktemp -d)/wt"
git worktree add -q "$wt" library
git -C "$wt" merge -q --ff-only origin/library 2>/dev/null || true
mkdir -p "$wt/.github/workflows"
cp .github/workflows/check.yml .github/workflows/publish.yml "$wt/.github/workflows/"
if [ -n "$(git -C "$wt" status --porcelain)" ]; then
	git -C "$wt" add .github
	git -C "$wt" commit -qm "chore: sync trigger workflows from main [skip ci]"
	git -C "$wt" push -q origin library
	ok "trigger workflows seeded onto library"
else
	ok "trigger workflows on library already in sync"
fi
git worktree remove --force "$wt"

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
if gh api -X PUT "repos/$repo/branches/library/protection" --input - >/dev/null 2>&1 <<'JSON'; then
{
  "required_status_checks": { "strict": false, "contexts": ["validate"] },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
	ok "library branch protected (requires the editor's check)"
else
	warn "could not protect library (needs admin / paid plan on private repos)"
	warn "  recommended: require the 'validate' check at"
	warn "  https://github.com/$repo/settings/branches"
fi

# 6. Status ------------------------------------------------------------------
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
