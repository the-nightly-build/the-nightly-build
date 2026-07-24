#!/usr/bin/env sh
# Keep the protected library workflows aligned with this fork's main branch.
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
SYNC_BRANCH=${NB_SYNC_BRANCH:-nb/sync-library-workflows}
POLL_SECONDS=${NB_SYNC_POLL_SECONDS:-10}
MAX_POLLS=${NB_SYNC_MAX_POLLS:-60}
UPSTREAM_REPO=${UPSTREAM_REPO:-the-nightly-build/the-nightly-build}
HANDOFF_EXIT=3
CHECK_WORKFLOW=.github/workflows/check.yml
PUBLISH_WORKFLOW=.github/workflows/publish.yml
SYNC_MARKER="Nightly-Build-Sync: v1"
PR_TITLE="Sync library workflows from main"
temp_root=
worktree=

say() { printf '→ %s\n' "$1"; }
ok() { printf '✓ %s\n' "$1"; }
die() {
	printf '✗ %s\n' "$1" >&2
	exit 1
}

cleanup() {
	if [ -n "$worktree" ]; then
		git -C "$ROOT" worktree remove --force "$worktree" >/dev/null 2>&1 || true
		worktree=
	fi
	if [ -n "$temp_root" ] && [ -d "$temp_root" ]; then
		rm -f "$temp_root/pr-body.md"
		rmdir "$temp_root/main/.github/workflows" 2>/dev/null || true
		rmdir "$temp_root/main/.github" 2>/dev/null || true
		rmdir "$temp_root/main" 2>/dev/null || true
		rmdir "$temp_root" 2>/dev/null || true
	fi
}
trap cleanup EXIT HUP INT TERM

require_tools() {
	command -v git >/dev/null 2>&1 || die "git is required"
	command -v uv >/dev/null 2>&1 || die "uv is required: https://docs.astral.sh/uv/"
	git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
		die "scripts/sync.sh must live in a git checkout"
}

repository_name() {
	origin_url=$(git -C "$ROOT" remote get-url origin 2>/dev/null) ||
		return 1
	gh repo view "$origin_url" --json nameWithOwner -q .nameWithOwner 2>/dev/null ||
		return 1
}

ref_has_workflows() {
	ref=$1
	for path in "$CHECK_WORKFLOW" "$PUBLISH_WORKFLOW"; do
		git -C "$ROOT" cat-file -e "$ref:$path" 2>/dev/null || return 1
	done
}

library_matches_main() {
	ref_has_workflows origin/main || return 1
	ref_has_workflows origin/library || return 1
	git -C "$ROOT" diff --quiet --no-ext-diff origin/library origin/main -- \
		"$CHECK_WORKFLOW" "$PUBLISH_WORKFLOW"
}

library_protection_state() {
	repo=$1
	contexts=$(gh api "repos/$repo/branches/library/protection/required_status_checks" \
		--jq '.contexts[]' 2>/dev/null) || return 2
	printf '%s\n' "$contexts" | grep -qx validate
}

remote_sync_branch() {
	git -C "$ROOT" ls-remote --exit-code --heads origin "$SYNC_BRANCH" 2>/dev/null |
		awk 'NR == 1 { print $1 }'
}

generated_branch_is_safe() {
	remote_sha=$1
	base=$(git -C "$ROOT" merge-base origin/library "$remote_sha") || return 1
	[ "$(git -C "$ROOT" rev-list --count "$base..$remote_sha")" = 1 ] || return 1
	[ "$(git -C "$ROOT" rev-parse "$remote_sha^")" = "$base" ] || return 1

	message=$(git -C "$ROOT" log -1 --format=%B "$remote_sha")
	printf '%s\n' "$message" | grep -Fqx "$SYNC_MARKER" || return 1
	recorded_main=$(printf '%s\n' "$message" | sed -n 's/^Main-Oid: //p')
	recorded_library=$(printf '%s\n' "$message" | sed -n 's/^Library-Oid: //p')
	[ -n "$recorded_main" ] || return 1
	[ "$recorded_library" = "$base" ] || return 1

	count=0
	while IFS="$(printf '\t')" read -r status path; do
		[ -n "$path" ] || continue
		case "$status" in
		A | M) ;;
		*) return 1 ;;
		esac
		case "$path" in
		.github/workflows/check.yml | .github/workflows/publish.yml) ;;
		*) return 1 ;;
		esac
		count=$((count + 1))
	done <<EOF
$(git -C "$ROOT" diff --name-status --no-renames "$base" "$remote_sha")
EOF
	[ "$count" -ge 1 ] && [ "$count" -le 2 ] || return 1

	for path in "$CHECK_WORKFLOW" "$PUBLISH_WORKFLOW"; do
		branch_blob=$(git -C "$ROOT" rev-parse "$remote_sha:$path" 2>/dev/null) || return 1
		main_blob=$(git -C "$ROOT" rev-parse "$recorded_main:$path" 2>/dev/null) || return 1
		[ "$branch_blob" = "$main_blob" ] || return 1
	done
}

write_canonical_workflows() {
	target=$1
	mkdir -p "$target/.github/workflows"
	for path in "$CHECK_WORKFLOW" "$PUBLISH_WORKFLOW"; do
		git -C "$ROOT" show "origin/main:$path" >"$target/$path" ||
			die "origin/main does not contain $path"
	done
}

emit_pr_body() {
	cat <<'EOF'
Copies the protected publishing workflows from this fork's `main` branch.

The editor accepts this PR only when both workflow blobs match `main` exactly
and no other files changed.
EOF
}

emit_agent_handoff() {
	reason=$1
	repo=${2-}
	printf '%s\n' \
		"NB_SYNC_PR_REQUIRED" \
		"reason=$reason"
	if [ -n "$repo" ]; then
		printf 'repository=%s\n' "$repo"
	fi
	printf '%s\n' \
		"base=library" \
		"head=$SYNC_BRANCH" \
		"title=$PR_TITLE" \
		"body<<NB_SYNC_BODY"
	emit_pr_body
	cat <<'EOF'
NB_SYNC_BODY

Use the runtime's connected GitHub tools to finish this generated sync:
1. Reuse an open PR with this base and head, or open it with the title and body above.
2. Never edit the generated branch or reproduce its commit by hand.
3. Wait for the `validate` check. If it fails or never appears, stop and report it.
4. After `validate` passes, squash-merge the PR through the protected branch.
5. Rerun `scripts/sync.sh`; continue the night only after it verifies the blobs.
EOF
}

prepare_sync_commit() {
	remote_sha=$1
	main_oid=$(git -C "$ROOT" rev-parse origin/main)
	library_oid=$(git -C "$ROOT" rev-parse origin/library)
	temp_root=$(mktemp -d)
	worktree="$temp_root/worktree"
	git -C "$ROOT" worktree add -q --detach "$worktree" origin/library
	write_canonical_workflows "$worktree"
	write_canonical_workflows "$temp_root/main"
	git -C "$worktree" add -- "$CHECK_WORKFLOW" "$PUBLISH_WORKFLOW"
	git -C "$worktree" -c user.name="The Nightly Build" \
		-c user.email="nightly-build@users.noreply.github.com" \
		commit -qm "chore: sync library workflows from main" \
		-m "$SYNC_MARKER" -m "Main-Oid: $main_oid" -m "Library-Oid: $library_oid"

	uv run "$ROOT/engine/check.py" --pr \
		--repo "$worktree" --main "$temp_root/main" \
		--base origin/library --head HEAD >/dev/null ||
		die "the generated workflow sync did not pass the local proof"

	if [ -n "$remote_sha" ]; then
		git -C "$worktree" push -q \
			--force-with-lease="refs/heads/$SYNC_BRANCH:$remote_sha" \
			origin "HEAD:refs/heads/$SYNC_BRANCH" ||
			die "the sync branch changed while it was being prepared; run scripts/sync.sh again"
	else
		git -C "$worktree" push -q origin "HEAD:refs/heads/$SYNC_BRANCH"
	fi
	git -C "$ROOT" worktree remove --force "$worktree"
	worktree=
}

open_or_update_pr() {
	repo=$1
	pr=$(gh pr list --repo "$repo" --base library --head "$SYNC_BRANCH" \
		--state open --json number --jq '.[0].number // ""') || return 1
	emit_pr_body >"$temp_root/pr-body.md"
	if [ -n "$pr" ]; then
		gh pr edit "$pr" --repo "$repo" \
			--title "$PR_TITLE" \
			--body-file "$temp_root/pr-body.md" >/dev/null || return 1
	else
		pr_url=$(gh pr create --repo "$repo" --base library --head "$SYNC_BRANCH" \
			--title "$PR_TITLE" \
			--body-file "$temp_root/pr-body.md") || return 1
		pr=${pr_url##*/}
	fi
	printf '%s\n' "$pr"
}

wait_for_library() {
	repo=$1
	pr=$2
	attempt=0
	while [ "$attempt" -le "$MAX_POLLS" ]; do
		git -C "$ROOT" fetch -q origin library
		if library_matches_main; then
			ok "library workflows match origin/main"
			return 0
		fi
		state=$(gh pr view "$pr" --repo "$repo" --json state --jq .state 2>/dev/null) ||
			return "$HANDOFF_EXIT"
		if [ "$state" = CLOSED ]; then
			die "sync PR #$pr closed without updating library"
		fi
		if failures=$(gh pr checks "$pr" --repo "$repo" \
			--json bucket,name,link \
			--jq '.[] | select(.bucket == "fail" or .bucket == "cancel") | "\(.name): \(.link)"' \
			2>/dev/null); then
			:
		else
			checks_status=$?
			[ "$checks_status" -eq 8 ] || return "$HANDOFF_EXIT"
		fi
		if [ -n "$failures" ]; then
			printf '%s\n' "$failures" >&2
			die "sync PR #$pr failed. Fix the canonical engine on main, then rerun scripts/sync.sh; do not edit the generated branch"
		fi
		attempt=$((attempt + 1))
		[ "$attempt" -le "$MAX_POLLS" ] && sleep "$POLL_SECONDS"
	done
	gh pr checks "$pr" --repo "$repo" 2>/dev/null || true
	die "sync PR #$pr did not merge in time. Inspect https://github.com/$repo/pull/$pr, fix main, then rerun scripts/sync.sh"
}

sync_library() {
	say "checking protected library workflows"
	git -C "$ROOT" fetch -q origin main library
	ref_has_workflows origin/main || die "origin/main is missing a publishing workflow"
	if library_matches_main; then
		ok "library workflows already match origin/main"
		return 0
	fi

	remote_sha=$(remote_sync_branch || true)
	if [ -n "$remote_sha" ]; then
		git -C "$ROOT" fetch -q origin \
			"refs/heads/$SYNC_BRANCH:refs/remotes/origin/$SYNC_BRANCH"
		if ! generated_branch_is_safe "origin/$SYNC_BRANCH"; then
			die "origin/$SYNC_BRANCH contains unrecognized edits. Preserve or remove that branch, then retry"
		fi
	fi

	prepare_sync_commit "$remote_sha"

	if ! command -v gh >/dev/null 2>&1; then
		emit_agent_handoff "gh is not installed"
		return "$HANDOFF_EXIT"
	fi
	if ! gh auth status >/dev/null 2>&1; then
		emit_agent_handoff "gh is not authenticated"
		return "$HANDOFF_EXIT"
	fi
	if ! repo=$(repository_name); then
		emit_agent_handoff "gh cannot resolve the origin repository"
		return "$HANDOFF_EXIT"
	fi
	if library_protection_state "$repo"; then
		:
	else
		protection_status=$?
		if [ "$protection_status" -eq 2 ]; then
			emit_agent_handoff "gh cannot read library branch protection" "$repo"
			return "$HANDOFF_EXIT"
		fi
		die "library is not protected by the required 'validate' check. Run ./setup.sh"
	fi

	if ! pr=$(open_or_update_pr "$repo"); then
		emit_agent_handoff "gh cannot open or update the sync PR" "$repo"
		return "$HANDOFF_EXIT"
	fi
	ok "workflow sync proposed in PR #$pr"
	if ! gh pr merge "$pr" --repo "$repo" --auto --squash >/dev/null; then
		git -C "$ROOT" fetch -q origin library
		if ! library_matches_main; then
			emit_agent_handoff "gh cannot enable protected auto-merge for PR #$pr" "$repo"
			return "$HANDOFF_EXIT"
		fi
	fi
	if wait_for_library "$repo" "$pr"; then
		return 0
	else
		wait_status=$?
		if [ "$wait_status" -eq "$HANDOFF_EXIT" ]; then
			emit_agent_handoff "gh cannot inspect sync PR #$pr" "$repo"
			return "$HANDOFF_EXIT"
		fi
		return "$wait_status"
	fi
}

update_main_from_upstream() {
	[ "$(git -C "$ROOT" branch --show-current)" = main ] ||
		die "--update-main-from-upstream requires the main branch"
	[ -z "$(git -C "$ROOT" status --porcelain)" ] ||
		die "--update-main-from-upstream requires a clean working tree"
	git -C "$ROOT" fetch -q origin main
	[ "$(git -C "$ROOT" rev-parse HEAD)" = "$(git -C "$ROOT" rev-parse origin/main)" ] ||
		die "local main must match origin/main. Reconcile it before importing upstream"

	if ! git -C "$ROOT" remote get-url upstream >/dev/null 2>&1; then
		git -C "$ROOT" remote add upstream "https://github.com/$UPSTREAM_REPO.git"
	fi
	say "fetching the engine's upstream main branch"
	git -C "$ROOT" fetch upstream main
	if ! git -C "$ROOT" merge --no-edit upstream/main; then
		printf '%s\n' "Conflicts:" >&2
		git -C "$ROOT" diff --name-only --diff-filter=U >&2
		die "resolve and commit these paths, push main, then run scripts/sync.sh; or run git merge --abort"
	fi
	git -C "$ROOT" push origin main
	ok "fork main updated from upstream"
	sync_library
}

main() {
	require_tools
	case "${1-}" in
	"") sync_library ;;
	--update-main-from-upstream)
		[ "$#" = 1 ] || die "usage: scripts/sync.sh [--update-main-from-upstream]"
		update_main_from_upstream
		;;
	*) die "usage: scripts/sync.sh [--update-main-from-upstream]" ;;
	esac
}

main "$@"
