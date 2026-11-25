"""PR mode: the exact shape and contents of one proposed library change.

The library accepts one new article bundle, one reviewed revision, an
owner-authorized retraction, or an exact workflow sync from the fork's main
branch. New bundles include the complete role record; revisions preserve that
history and add one numbered explanation of the change.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING

from nb import meta as nb_meta
from nb.artifacts import validate_artifacts, validate_revision_note
from nb.config import load_series
from nb.proof import check_article
from nb.workflow_sync import classify_workflow_sync

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from nb.report import Report

__all__ = (
    "materialize_bundle",
    "pr_changed_files",
    "run_pr_mode",
)

PR_PATH_RE = nb_meta.PR_PATH_RE
MIN_STATUS_PARTS = 2


def _git_executable() -> str:
    git = shutil.which("git")
    if git is None:
        msg = "git executable not found on PATH"
        raise FileNotFoundError(msg)
    return git


def _split_pr_path(path: str) -> tuple[str, str]:
    match = PR_PATH_RE.match(path)
    if match is None:
        msg = f"unexpected article path: {path}"
        raise ValueError(msg)
    return match.group(1), match.group(2)


def pr_changed_files(repo: str | pathlib.Path, *, base: str, head: str) -> list[tuple[str, str]]:
    git = _git_executable()
    out = subprocess.run(
        [
            git,
            "-C",
            str(repo),
            "diff",
            "--name-status",
            "--no-renames",
            f"{base}...{head}",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    changes: list[tuple[str, str]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= MIN_STATUS_PARTS:
            changes.append((parts[0], parts[-1]))
    return changes


def materialize_bundle(
    repo: str | pathlib.Path,
    head: str,
    *,
    changes: Sequence[tuple[str, str]],
    dest: str | pathlib.Path,
    extra_paths: Iterable[str] = (),
) -> None:
    """Write the PR's files, as `head` has them, under dest.

    The proof reads the bundle from disk (the article, then its bundle assets
    by size and image header), but the checkout at --repo can be on any branch:
    the documented preflight runs it from the library checkout, where the new
    bundle does not exist yet. What the PR would merge is the blob at head, so
    that is what gets checked, whatever happens to be checked out.
    """
    git = _git_executable()
    dest_path = pathlib.Path(dest)
    paths = [relpath for status, relpath in changes if status != "D"]
    paths.extend(path for path in extra_paths if path not in paths)
    for relpath in paths:
        blob = subprocess.run(
            [git, "-C", str(repo), "show", f"{head}:{relpath}"],
            capture_output=True,
            check=True,
        ).stdout
        target = dest_path / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)


def _tree_paths(repo: str | pathlib.Path, *, ref: str, prefix: str) -> list[str]:
    git = _git_executable()
    result = subprocess.run(
        [git, "-C", str(repo), "ls-tree", "-r", "--name-only", ref, "--", prefix],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def _is_regular_blob(repo: str | pathlib.Path, *, ref: str, path: str) -> bool:
    git = _git_executable()
    result = subprocess.run(
        [git, "-C", str(repo), "ls-tree", ref, "--", path],
        capture_output=True,
        text=True,
        check=True,
    )
    mode, _separator, _rest = result.stdout.partition(" ")
    return mode in {"100644", "100755"}


def _handle_workflow_sync(
    repo: str | pathlib.Path,
    cfg_repo: str | pathlib.Path,
    *,
    head: str,
    changes: list[tuple[str, str]],
    rep: Report,
) -> bool:
    workflow_sync = classify_workflow_sync(
        repo,
        cfg_repo,
        head=head,
        changes=changes,
    )
    if not workflow_sync.attempted:
        return False
    if workflow_sync.valid:
        rep.outcome = "SYNC"
        rep.notes.append("workflow sync: exact copies from the fork's main branch")
    else:
        rep.block(
            "B-WORKFLOW-SYNC",
            workflow_sync.reason or "invalid workflow sync",
        )
    return True


def _handle_owner_retraction(
    repo: str | pathlib.Path,
    *,
    base: str,
    changes: list[tuple[str, str]],
    rep: Report,
) -> None:
    retracted = nb_meta.article_bundle_path(changes, status="D")
    if retracted is None:
        rep.block(
            "B-DIFF-SHAPE",
            "an owner curation PR deletes one article with its matching "
            f"local assets and agent-artifacts record; found {changes}",
        )
        return
    series_id, slug = _split_pr_path(retracted)
    deleted = {path for _, path in changes}
    remaining = [
        path
        for prefix in (
            f"library/{series_id}/{slug}/",
            f"agent-artifacts/{series_id}/{slug}/",
        )
        for path in _tree_paths(repo, ref=base, prefix=prefix)
        if path not in deleted
    ]
    if remaining:
        rep.block(
            "B-DIFF-SHAPE",
            "a retraction deletes the article, its full asset directory, and "
            f"its full agent-artifacts record; still present: {remaining}",
        )
    else:
        rep.notes.append(
            "owner curation: retracts one published article with its assets and production record; nothing to proof"
        )


def _select_bundle_path(changes: list[tuple[str, str]], rep: Report) -> tuple[str, bool] | None:
    path = nb_meta.article_bundle_path(changes)
    if path is not None:
        return path, False
    path = nb_meta.revision_bundle_path(changes)
    if path is not None:
        return path, True
    rep.block(
        "B-DIFF-SHAPE",
        "PR must add one article bundle or revise one article with matching "
        "assets and one new revision note; found "
        f"{[(status, changed_path) for status, changed_path in changes]}",
    )
    return None


def _all_regular_blobs(
    repo: str | pathlib.Path,
    *,
    head: str,
    changes: Sequence[tuple[str, str]],
    rep: Report,
) -> bool:
    for status, changed_path in changes:
        if status != "D" and not _is_regular_blob(repo, ref=head, path=changed_path):
            rep.block(
                "B-DIFF-SHAPE",
                f"every changed path must be a regular file: {changed_path}",
            )
            return False
    return True


def _validate_bundle_artifacts(
    bundle_dir: pathlib.Path,
    *,
    repo: str | pathlib.Path,
    base: str,
    series_id: str,
    slug: str,
    changes: Sequence[tuple[str, str]],
    revision: bool,
    rep: Report,
) -> None:
    if revision:
        artifact_prefix = f"agent-artifacts/{series_id}/{slug}/"
        added_paths = [changed_path for status, changed_path in changes if status == "A"]
        issues = validate_revision_note(
            bundle_dir,
            series=series_id,
            slug=slug,
            added_paths=added_paths,
            base_paths=_tree_paths(repo, ref=base, prefix=artifact_prefix),
        )
    else:
        issues = validate_artifacts(bundle_dir, series=series_id, slug=slug)
    for issue in issues:
        rep.block("B-REVISION-NOTE" if revision else "B-AGENT-ARTIFACTS", issue)


def run_pr_mode(
    *,
    repo: str | pathlib.Path,
    base: str,
    head: str,
    library: str | pathlib.Path | None,
    rep: Report,
    main: str | pathlib.Path | None = None,
    today: str | None = None,
    check_links: bool = True,
    deletions_by_owner: bool = False,
) -> None:
    try:
        changes = pr_changed_files(repo, base=base, head=head)
    except subprocess.CalledProcessError as e:
        rep.block("B-DIFF-SHAPE", f"git diff failed: {e.stderr or e}")
        return
    cfg_repo = main or repo
    if _handle_workflow_sync(repo, cfg_repo, head=head, changes=changes, rep=rep):
        return
    if deletions_by_owner and changes and all(status == "D" for status, _ in changes):
        _handle_owner_retraction(repo, base=base, changes=changes, rep=rep)
        return
    selected = _select_bundle_path(changes, rep)
    if selected is None:
        return
    path, revision = selected
    if not _all_regular_blobs(repo, head=head, changes=changes, rep=rep):
        return
    series_id, slug = _split_pr_path(path)
    series_cfg, _ = load_series(cfg_repo, series_id)
    rep.strict = bool(isinstance(series_cfg, dict) and series_cfg.get("strict"))
    with tempfile.TemporaryDirectory() as bundle_dir:
        bundle_root = pathlib.Path(bundle_dir)
        asset_prefix = f"library/{series_id}/{slug}/"
        extra_paths = [path, *_tree_paths(repo, ref=head, prefix=asset_prefix)] if revision else []
        materialize_bundle(
            repo,
            head,
            changes=changes,
            dest=bundle_root,
            extra_paths=extra_paths,
        )
        _validate_bundle_artifacts(
            bundle_root,
            repo=repo,
            base=base,
            series_id=series_id,
            slug=slug,
            changes=changes,
            revision=revision,
            rep=rep,
        )
        check_article(
            bundle_root / path,
            series_id,
            repo=cfg_repo,
            library_dir=library,
            rep=rep,
            today=dt.date.fromisoformat(today) if today else None,
            check_links=check_links,
            revision=revision,
        )
