#!/usr/bin/env zsh
# The Nightly Build — setup.sh
# Idempotent bootstrap: creates the library branch, enables Pages + auto-merge,
# validates configuration. Safe to re-run; callable by the Librarian skill.
set -euo pipefail

say() { print -- "→ $1"; }
ok() { print -- "✓ $1"; }
warn() { print -- "⚠ $1"; }
die() {
	print -- "✗ $1" >&2
	exit 1
}

# 1. Preconditions -----------------------------------------------------------
command -v gh >/dev/null 2>&1 || die "gh (GitHub CLI) is required: https://cli.github.com"
command -v git >/dev/null 2>&1 || die "git is required"
command -v python3 >/dev/null 2>&1 || die "python3 is required"
gh auth status >/dev/null 2>&1 || die "gh is not authenticated — run: gh auth login"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "run this from your fork's checkout"

repo=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null) ||
	die "no GitHub repo detected — is 'origin' set to your fork?"
ok "repo: $repo"

python3 -c 'import yaml' 2>/dev/null ||
	die "PyYAML is required: pip install pyyaml (or: uv pip install pyyaml)"

# 1b. Forks must not run the upstream dogfood series --------------------------
is_fork=$(gh repo view --json isFork -q .isFork 2>/dev/null || print false)
if [[ "$is_fork" == "true" ]] &&
	[[ -d series/semiconductors || -d series/ai-briefs ]]; then
	warn "the upstream dogfood series are still configured on this fork."
	warn "they are the upstream project's own assignments — remove them and"
	warn "add your own series before scheduling anything:"
	warn "  rm -r series/semiconductors series/ai-briefs series/_tags"
fi

# 2. Configuration validates before anything else ----------------------------
say "validating site.yaml, templates/registry.yaml, series/*/series.yaml"
python3 engine/validate_config.py || die "fix the configuration above, then re-run"

# 3. The library branch (orphan, empty press) --------------------------------
if git ls-remote --exit-code --heads origin library >/dev/null 2>&1; then
	ok "library branch already exists on origin"
else
	say "creating orphan library branch"
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
# library. They are pure triggers — every real instruction checks out engine
# and templates from main — so no engine logic lands on library (§1 invariant).
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
		warn "could not enable Pages via API — enable it manually:"
		warn "  https://github.com/$repo/settings/pages → Source: GitHub Actions"
	fi
fi

# 5. Auto-merge + library protection -----------------------------------------
if gh api -X PATCH "repos/$repo" -F allow_auto_merge=true >/dev/null 2>&1; then
	ok "repository auto-merge enabled"
else
	warn "could not enable auto-merge — flip it at https://github.com/$repo/settings"
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
print
ok "The presses are ready."
print -- "
Next steps:
  1. Configure a series (or ask your agent: 'set me up' → the Librarian skill).
  2. Rehearse:   run a press check — see skills/correspondent/SKILL.md §press-check.
  3. Schedule:   pick your harness in harnesses/ (claude-code.md, jules.md, codex.md)
                 and paste the filled schedule prompt it gives you.
  4. Morning:    your site lives at the Pages URL for $repo.
"
