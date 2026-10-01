"""Turn one approved article workspace into an exact Article PR.

Editorial roles work in a small directory whose ``library/`` and
``agent-artifacts/`` subtrees already have their final repository paths. This
module copies that finished bundle onto a generated branch, proves the exact
commit, pushes it, and opens or describes the pull request. This module never
edits the article or interprets editorial quality.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from nb import meta as nb_meta
from nb.artifacts import validate_artifacts
from nb.git_handoff import GitHandoffError
from nb.library_checkout import LibraryCheckoutError, ensure_library, repo_root
from nb.proof.pr import run_pr_mode
from nb.report import Report, emit

__all__ = ("main",)

HANDOFF_EXIT = 3
COMMIT_MARKER = "Nightly-Build-Article: v1"


class _PrepareError(RuntimeError):
    pass


@dataclass(frozen=True)
class _Article:
    path: pathlib.Path
    workspace: pathlib.Path
    series: str
    slug: str
    title: str


@dataclass(frozen=True)
class _PreparedBranch:
    article: _Article
    name: str
    commit: str


# Git's argv is naturally variadic; ``check`` remains explicit at the call site.
# ast-grep-ignore: keyword-only-args
def _git(repo: pathlib.Path, *arguments: str, check: bool = True) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *arguments],
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise GitHandoffError(
            repo=repo, arguments=arguments, reason=str(error)
        ) from error
    if result.returncode and arguments[0] in ("fetch", "push", "ls-remote"):
        raise GitHandoffError(
            repo=repo,
            arguments=arguments,
            reason=result.stderr.strip()
            or result.stdout.strip()
            or "Git remote operation failed",
        )
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise _PrepareError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout.strip()


def _article_from_workspace(path: pathlib.Path) -> _Article:
    article_path = path.resolve()
    if not article_path.is_file() or article_path.is_symlink():
        raise _PrepareError(f"article must be a regular file: {article_path}")
    metadata = nb_meta.read_meta(str(article_path))
    if metadata is None:
        raise _PrepareError("article has no readable nb-meta block")

    series = metadata.get("series")
    slug = metadata.get("slug")
    title = metadata.get("title")
    if not isinstance(series, str) or nb_meta.SERIES_RE.fullmatch(series) is None:
        raise _PrepareError("article nb-meta has an invalid series")
    if not isinstance(slug, str) or nb_meta.SLUG_RE.fullmatch(slug) is None:
        raise _PrepareError("article nb-meta has an invalid slug")
    if not isinstance(title, str) or not title.strip():
        raise _PrepareError("article nb-meta has no title")

    expected_tail = pathlib.Path("library") / series / f"{slug}.html"
    if pathlib.Path(*article_path.parts[-3:]) != expected_tail:
        raise _PrepareError(
            f"article must be at <workspace>/{expected_tail.as_posix()}"
        )
    workspace = article_path.parents[2]
    errors = validate_artifacts(workspace, series=series, slug=slug)
    if errors:
        raise _PrepareError("invalid agent artifacts:\n- " + "\n- ".join(errors))
    return _Article(article_path, workspace, series, slug, title.strip())


def _remote_branch(library: pathlib.Path, name: str) -> str | None:
    output = _git(
        library,
        "ls-remote",
        "--heads",
        "origin",
        f"refs/heads/{name}",
        check=False,
    )
    return output.split(maxsplit=1)[0] if output else None


def _generated_branch_is_safe(
    library: pathlib.Path,
    *,
    name: str,
    remote_commit: str,
    article: _Article,
) -> bool:
    remote_ref = f"refs/remotes/origin/{name}"
    _git(
        library,
        "fetch",
        "-q",
        "origin",
        f"refs/heads/{name}:{remote_ref}",
    )
    base = _git(library, "merge-base", "origin/library", remote_commit)
    if _git(library, "rev-list", "--count", f"{base}..{remote_commit}") != "1":
        return False
    if _git(library, "rev-parse", f"{remote_commit}^") != base:
        return False
    message = _git(library, "log", "-1", "--format=%B", remote_commit)
    expected_lines = {
        COMMIT_MARKER,
        f"Series: {article.series}",
        f"Slug: {article.slug}",
        f"Library-Oid: {base}",
    }
    if not expected_lines.issubset(set(message.splitlines())):
        return False
    changes = []
    for line in _git(
        library, "diff", "--name-status", "--no-renames", base, remote_commit
    ).splitlines():
        state, separator, changed_path = line.partition("\t")
        if not separator:
            return False
        changes.append((state, changed_path))
    expected_article = f"library/{article.series}/{article.slug}.html"
    return nb_meta.article_bundle_path(changes) == expected_article


def _copy_bundle(
    article: _Article,
    worktree: pathlib.Path,
) -> None:
    relative_article = article.path.relative_to(article.workspace)
    target_article = worktree / relative_article
    target_article.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(article.path, target_article)

    source_assets = article.path.with_suffix("")
    target_assets = worktree / source_assets.relative_to(article.workspace)
    if source_assets.exists():
        if not source_assets.is_dir() or source_assets.is_symlink():
            raise _PrepareError(f"article assets must be a directory: {source_assets}")
        if any(path.is_symlink() for path in source_assets.rglob("*")):
            raise _PrepareError("article assets cannot contain symbolic links")
        shutil.copytree(source_assets, target_assets)

    source_artifacts = (
        article.workspace / "agent-artifacts" / article.series / article.slug
    )
    target_artifacts = worktree / source_artifacts.relative_to(article.workspace)
    target_artifacts.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_artifacts, target_artifacts)


def _prove_branch(
    worktree: pathlib.Path,
    *,
    main_root: pathlib.Path,
    library: pathlib.Path,
    base: str,
    check_links: bool,
    today: dt.date | None,
) -> None:
    report = Report()
    run_pr_mode(
        repo=str(worktree),
        main=str(main_root),
        base=base,
        head="HEAD",
        library=str(library),
        today=today.isoformat() if today else None,
        check_links=check_links,
        deletions_by_owner=False,
        rep=report,
    )
    emit(report, False)
    if report.blocks:
        raise _PrepareError("the generated Article PR did not pass nb check")


def _prepare_branch(
    article: _Article,
    *,
    main_root: pathlib.Path,
    library: pathlib.Path,
    check_links: bool,
    today: dt.date | None,
) -> _PreparedBranch:
    _git(library, "rev-parse", "--is-inside-work-tree")
    _git(library, "fetch", "-q", "origin", "library")
    base = _git(library, "rev-parse", "origin/library")
    article_target = f"library/{article.series}/{article.slug}.html"
    published = subprocess.run(
        ["git", "-C", str(library), "cat-file", "-e", f"{base}:{article_target}"],
        capture_output=True,
    )
    is_published = published.returncode == 0
    if is_published:
        raise _PrepareError(f"article is already published: {article_target}")
    name = f"nb/article/{article.series}/{article.slug}"
    remote_commit = _remote_branch(library, name)
    if remote_commit and not _generated_branch_is_safe(
        library,
        name=name,
        remote_commit=remote_commit,
        article=article,
    ):
        raise _PrepareError(
            f"origin/{name} contains unrecognized edits; preserve or remove it first"
        )

    with tempfile.TemporaryDirectory(prefix="nb-article-pr-") as temporary:
        worktree = pathlib.Path(temporary) / "worktree"
        _git(library, "worktree", "add", "-q", "--detach", str(worktree), base)
        try:
            _copy_bundle(article, worktree)
            _git(worktree, "add", "--", "library", "agent-artifacts")
            _git(
                worktree,
                "-c",
                "user.name=The Nightly Build",
                "-c",
                "user.email=nightly-build@users.noreply.github.com",
                "commit",
                "-qm",
                f"article: publish {article.series}/{article.slug}",
                "-m",
                COMMIT_MARKER,
                "-m",
                f"Series: {article.series}",
                "-m",
                f"Slug: {article.slug}",
                "-m",
                f"Library-Oid: {base}",
            )
            _prove_branch(
                worktree,
                main_root=main_root,
                library=library,
                base=base,
                check_links=check_links,
                today=today,
            )
            commit = _git(worktree, "rev-parse", "HEAD")
            destination = f"HEAD:refs/heads/{name}"
            if remote_commit:
                _git(
                    worktree,
                    "push",
                    "-q",
                    f"--force-with-lease=refs/heads/{name}:{remote_commit}",
                    "origin",
                    destination,
                )
            else:
                _git(worktree, "push", "-q", "origin", destination)
        finally:
            _git(library, "worktree", "remove", "--force", str(worktree), check=False)
    return _PreparedBranch(article, name, commit)


def _pr_title(prepared: _PreparedBranch) -> str:
    return f"Publish {prepared.article.title}"


def _pr_body(prepared: _PreparedBranch) -> str:
    article = prepared.article
    return (
        f"Publishes **{article.title}** in `{article.series}`.\n\n"
        "This PR contains the article, its assets, and the exact inputs and "
        "outputs from every editorial role.\n\n"
        f"Generated commit: `{prepared.commit}`\n"
    )


def _repository_name(library: pathlib.Path, gh: str) -> str | None:
    origin = _git(library, "remote", "get-url", "origin")
    result = subprocess.run(
        [gh, "repo", "view", origin, "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _handoff(
    prepared: _PreparedBranch, *, reason: str, repository: str | None, hold: bool
) -> int:
    print("NB_ARTICLE_PR_REQUIRED")
    print(f"reason={reason}")
    if repository:
        print(f"repository={repository}")
    print("base=library")
    if hold:
        print("draft=true")
    print(f"head={prepared.name}")
    print(f"title={_pr_title(prepared)}")
    print("body<<NB_ARTICLE_BODY")
    print(_pr_body(prepared), end="")
    print("NB_ARTICLE_BODY")
    print()
    print("Use the runtime's connected GitHub tools to finish this exact request:")
    print("1. Reuse an open PR with this base and head, or open it as specified.")
    print("2. Do not edit the generated branch or recreate its commit.")
    print("3. Monitor CI and route any failure back to the orchestrator.")
    return HANDOFF_EXIT


def _open_pr(prepared: _PreparedBranch, *, library: pathlib.Path, hold: bool) -> int:
    gh = shutil.which("gh")
    if gh is None:
        return _handoff(
            prepared, reason="gh is not installed", repository=None, hold=hold
        )
    authenticated = subprocess.run(
        [gh, "auth", "status"], capture_output=True, text=True
    )
    if authenticated.returncode:
        return _handoff(
            prepared, reason="gh is not authenticated", repository=None, hold=hold
        )
    repository = _repository_name(library, gh)
    if repository is None:
        return _handoff(
            prepared,
            reason="gh cannot resolve the origin repository",
            repository=None,
            hold=hold,
        )

    existing = subprocess.run(
        [
            gh,
            "pr",
            "list",
            "--repo",
            repository,
            "--base",
            "library",
            "--head",
            prepared.name,
            "--state",
            "open",
            "--json",
            "url",
            "--jq",
            '.[0].url // ""',
        ],
        capture_output=True,
        text=True,
    )
    if existing.returncode:
        return _handoff(
            prepared,
            reason="gh cannot inspect Article PRs",
            repository=repository,
            hold=hold,
        )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8") as body_file:
        body_file.write(_pr_body(prepared))
        body_file.flush()
        url = existing.stdout.strip()
        if url:
            command = [
                gh,
                "pr",
                "edit",
                url,
                "--repo",
                repository,
                "--title",
                _pr_title(prepared),
                "--body-file",
                body_file.name,
            ]
        else:
            command = [
                gh,
                "pr",
                "create",
                "--repo",
                repository,
                "--base",
                "library",
                "--head",
                prepared.name,
                "--title",
                _pr_title(prepared),
                "--body-file",
                body_file.name,
            ]
            if hold:
                command.append("--draft")
        result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        return _handoff(
            prepared,
            reason="gh cannot open or update the Article PR",
            repository=repository,
            hold=hold,
        )
    if url and hold:
        # an existing PR is re-held rather than left ready to merge
        held = subprocess.run(
            [gh, "pr", "ready", "--undo", url, "--repo", repository],
            capture_output=True,
            text=True,
        )
        if held.returncode:
            return _handoff(
                prepared,
                reason="gh cannot mark the Article PR as a draft",
                repository=repository,
                hold=hold,
            )
    print(url or result.stdout.strip())
    return 0


def _prepare(
    article_path: pathlib.Path,
    *,
    main_root: pathlib.Path,
    library: pathlib.Path | None,
    check_links: bool,
    hold: bool,
    today: dt.date | None = None,
) -> int:
    article = _article_from_workspace(article_path)
    checkout = (library or ensure_library(main_root)).resolve()
    prepared = _prepare_branch(
        article,
        main_root=main_root.resolve(),
        library=checkout,
        check_links=check_links,
        today=today,
    )
    return _open_pr(prepared, library=checkout, hold=hold)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate, commit, push, and open one exact Article PR"
    )
    parser.add_argument("article", type=pathlib.Path)
    parser.add_argument(
        "--library",
        type=pathlib.Path,
        help="library checkout; defaults to one kept under .nb-work/ at origin/library",
    )
    parser.add_argument(
        "--hold",
        action="store_true",
        help="open the Article PR as a draft that CI validates and never merges",
    )
    parser.add_argument(
        "--check-links",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="verify source URLs during the final local proof",
    )
    parser.add_argument("--today", type=dt.date.fromisoformat, help=argparse.SUPPRESS)
    return parser


def main(arguments: list[str] | None = None) -> int:
    parsed = _parser().parse_args(arguments)
    try:
        return _prepare(
            parsed.article,
            main_root=repo_root(),
            library=parsed.library,
            check_links=parsed.check_links,
            hold=parsed.hold,
            today=parsed.today,
        )
    except (_PrepareError, LibraryCheckoutError) as error:
        print(f"nb prepare-pr: {error}", file=sys.stderr)
        return 1
    except GitHandoffError as error:
        return error.emit()


if __name__ == "__main__":
    raise SystemExit(main())
