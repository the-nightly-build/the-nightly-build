"""Validate the editorial record committed with an article.

Git already supplies immutable bytes, file identity, and commit provenance, so
the artifact contract is intentionally structural. Each role invocation has a
semantic brief and output filename. A later article revision adds one numbered
Markdown note without rewriting that production history.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from nb import meta as nb_meta

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Mapping, Sequence

__all__ = (
    "ROLE_FILES",
    "ROOT_FILES",
    "artifact_root",
    "validate_artifacts",
    "validate_revision_note",
)

ROLE_FILES: Mapping[str, tuple[str, str]] = {
    "writing-coach": ("brief.md", "voice-guide.md"),
    "researcher": ("brief.md", "evidence.md"),
    "writer": ("brief.md", "draft-handoff.md"),
    "editor": ("review-brief.md", "editorial-review.md"),
}
ROOT_FILES = ("editorial-direction.md", "commission.md")
INVOCATION_RE = re.compile(r"^[0-9]{2}$")
MAX_REVISION_NUMBER = 99


def artifact_root(root: pathlib.Path, *, series: str, slug: str) -> pathlib.Path:
    return root / "agent-artifacts" / series / slug


def _readable_markdown(path: pathlib.Path) -> str | None:
    if not path.is_file() or path.is_symlink():
        return f"missing regular file: {path.name}"
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"not UTF-8 Markdown: {path.name}"
    if not content.strip():
        return f"empty artifact: {path.name}"
    return None


def _invocation_errors(child: pathlib.Path, *, role: str, expected_files: set[str]) -> list[str]:
    if not child.is_dir() or child.is_symlink():
        return [f"{role}/{child.name}: must be a directory"]
    actual_files = {path.name for path in child.iterdir()}
    if actual_files != expected_files:
        return [f"{role}/{child.name}: expected {sorted(expected_files)}; found {sorted(actual_files)}"]
    errors: list[str] = []
    for filename in sorted(expected_files):
        issue = _readable_markdown(child / filename)
        if issue:
            errors.append(f"{role}/{child.name}: {issue}")
    return errors


def _role_errors(root: pathlib.Path, role: str) -> list[str]:
    role_root = root / role
    if not role_root.is_dir() or role_root.is_symlink():
        return [f"missing role directory: {role}"]

    children = sorted(role_root.iterdir(), key=lambda path: path.name)
    invalid = [path.name for path in children if not INVOCATION_RE.fullmatch(path.name)]
    if invalid:
        return [f"{role}: unexpected invocation entries: {', '.join(invalid)}"]
    invocations = [int(path.name) for path in children]
    if not invocations:
        return [f"{role}: no invocations"]
    expected = list(range(1, len(invocations) + 1))
    if invocations != expected:
        return [
            f"{role}: invocations must be contiguous from 01; found "
            + ", ".join(f"{number:02d}" for number in invocations)
        ]

    errors: list[str] = []
    expected_files = set(ROLE_FILES[role])
    for child in children:
        errors.extend(_invocation_errors(child, role=role, expected_files=expected_files))
    return errors


def validate_artifacts(root: pathlib.Path, *, series: str, slug: str) -> list[str]:
    artifacts = artifact_root(root, series=series, slug=slug)
    if not artifacts.is_dir() or artifacts.is_symlink():
        return [f"missing artifact tree: agent-artifacts/{series}/{slug}"]

    allowed = {*ROOT_FILES, *ROLE_FILES}
    actual = {path.name for path in artifacts.iterdir()}
    errors = [f"unexpected artifact entries: {sorted(actual - allowed)}"] if actual - allowed else []
    for filename in ROOT_FILES:
        issue = _readable_markdown(artifacts / filename)
        if issue:
            errors.append(issue)
    for role in ROLE_FILES:
        errors.extend(_role_errors(artifacts, role))
    return errors


def validate_revision_note(
    root: pathlib.Path,
    *,
    series: str,
    slug: str,
    added_paths: Sequence[str],
    base_paths: Sequence[str],
) -> list[str]:
    prefix = f"agent-artifacts/{series}/{slug}/"
    added = [path for path in added_paths if path.startswith(prefix)]
    if len(added) != 1:
        return [f"revision must add exactly one Markdown note; found {sorted(added)}"]

    path = added[0]
    match = nb_meta.REVISION_NOTE_RE.fullmatch(path)
    if match is None or match.group(1, 2) != (series, slug):
        return [f"invalid revision note path: {path}"]

    prior_numbers = {
        int(prior.group(3))
        for base_path in base_paths
        if (prior := nb_meta.REVISION_NOTE_RE.fullmatch(base_path)) is not None and prior.group(1, 2) == (series, slug)
    }
    expected = max(prior_numbers, default=0) + 1
    number = int(match.group(3))
    errors: list[str] = []
    if expected > MAX_REVISION_NUMBER:
        errors.append(f"revision note numbering is exhausted at {MAX_REVISION_NUMBER}")
    elif number != expected:
        errors.append(f"revision note must be revisions/{expected:02d}.md; found revisions/{number:02d}.md")

    issue = _readable_markdown(root / path)
    if issue:
        errors.append(f"revisions/{number:02d}.md: {issue}")
    return errors
