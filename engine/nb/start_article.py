"""Initialize one article with the exact context its editorial team needs.

The orchestrator chooses the commission. This module handles only the
deterministic setup: resolve the selected template, copy its skeleton, and
assemble the current authored directions without paraphrasing them.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import yaml

from nb import meta as nb_meta
from nb.config import apply_template_bands, load_registry, load_series, template_choices
from nb.site.assets import template_dirs

__all__ = ("StartArticleError", "initialize", "main", "parser")


class StartArticleError(RuntimeError):
    pass


@dataclass(frozen=True)
class _Layer:
    title: str
    path: pathlib.Path


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise StartArticleError(f"{label} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _selected_item(series: Mapping[str, object], slug: str) -> dict[str, object] | None:
    items = series.get("items")
    if items is None:
        return None
    if not isinstance(items, list):
        raise StartArticleError("series items must be a list")
    for value in items:
        if isinstance(value, Mapping) and value.get("slug") == slug:
            return {str(key): item for key, item in value.items()}
    return None


def _item_tags(item: Mapping[str, object] | None) -> tuple[str, ...]:
    if item is None or item.get("tags") is None:
        return ()
    value = item["tags"]
    if not isinstance(value, list):
        raise StartArticleError("selected item tags must be a list of tag names")
    tags = tuple(tag for tag in value if isinstance(tag, str))
    if len(tags) != len(value):
        raise StartArticleError("selected item tags must be a list of tag names")
    if len(tags) != len(set(tags)):
        raise StartArticleError("selected item tags must not repeat")
    return tags


def _resolve_tags(
    *,
    item: Mapping[str, object] | None,
    requested: Sequence[str],
) -> tuple[str, ...]:
    configured = _item_tags(item)
    requested_tags = tuple(requested)
    if item is not None and requested_tags and requested_tags != configured:
        raise StartArticleError(
            "--tag values conflict with the selected item's declared tag order"
        )
    tags = configured if item is not None else requested_tags
    if len(tags) != len(set(tags)):
        raise StartArticleError("--tag values must not repeat")
    for tag in tags:
        if not nb_meta.is_safe_tag(tag):
            raise StartArticleError(f"invalid tag: {tag!r}")
    return tags


def _relative(path: pathlib.Path, repo: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _checkout_revision(repo: pathlib.Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _read(path: pathlib.Path, *, label: str) -> str:
    if not path.is_file() or path.is_symlink():
        raise StartArticleError(f"missing {label}: {path}")
    return path.read_text(encoding="utf-8")


def _optional_layer(title: str, path: pathlib.Path) -> _Layer | None:
    return _Layer(title, path) if path.is_file() and not path.is_symlink() else None


def _tag_layers(
    repo: pathlib.Path,
    *,
    series_id: str,
    series: Mapping[str, object],
    tags: Sequence[str],
) -> list[_Layer]:
    configured = series.get("tags") or {}
    mappings = _mapping(configured, label="series tags")
    series_root = repo / "press" / "series" / series_id
    layers: list[_Layer] = []
    for tag in tags:
        fragment = mappings.get(tag)
        if not isinstance(fragment, str) or not fragment:
            raise StartArticleError(f"tag {tag!r} has no configured prompt fragment")
        path = (series_root / fragment).resolve()
        _read(path, label=f"tag fragment for {tag}")
        layers.append(_Layer(f"Tag: {tag}", path))
    return layers


def _editorial_direction(
    repo: pathlib.Path,
    *,
    revision: str,
    series_id: str,
    series: Mapping[str, object],
    template_folder: pathlib.Path,
    tags: Sequence[str],
    item: Mapping[str, object] | None,
) -> str:
    series_root = repo / "press" / "series" / series_id
    layers = [
        _Layer("House editorial standard", repo / "spec" / "editorial.md"),
        _Layer("Slop standard", repo / "spec" / "slop.md"),
        _Layer("Headline standard", repo / "spec" / "headlines.md"),
    ]
    optional = (
        _optional_layer("Press editorial direction", repo / "press" / "editorial.md"),
        _optional_layer("Template identity", template_folder / "identity.md"),
    )
    layers.extend(layer for layer in optional if layer is not None)

    prompt = series.get("prompt")
    if prompt is not None:
        if not isinstance(prompt, str) or not prompt:
            raise StartArticleError("series prompt must be a path string")
        layers.append(_Layer("Series direction", series_root / prompt))
    layers.extend(_tag_layers(repo, series_id=series_id, series=series, tags=tags))

    chunks = [
        "# Editorial direction\n",
        "These are the exact standing directions for this article. Later "
        "sections specialize earlier ones; the orchestrator's commission "
        "adds article-specific decisions without rewriting them.\n\n",
        f"Checkout revision: `{revision}`\n",
    ]
    for index, layer in enumerate(layers, start=1):
        content = _read(layer.path, label=layer.title.lower())
        chunks.extend(
            (
                f"\n## {index}. {layer.title}\n\n",
                f"Source: `{_relative(layer.path, repo)}`\n\n",
                content,
                "" if content.endswith("\n") else "\n",
            )
        )
    if item is not None:
        chunks.extend(
            (
                f"\n## {len(layers) + 1}. Selected item\n\n",
                f"Source: `press/series/{series_id}/series.yaml`\n\n",
                "```yaml\n",
                yaml.safe_dump(dict(item), sort_keys=False, allow_unicode=True),
                "```\n",
            )
        )
    return "".join(chunks)


def _site_assets(repo: pathlib.Path) -> object:
    path = repo / "press" / "site.yaml"
    if not path.is_file():
        return {}
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    site = _mapping(document, label="press/site.yaml")
    return site.get("assets") or {}


def _pinned_voice_guide(
    repo: pathlib.Path,
    *,
    series_id: str,
    series: Mapping[str, object],
) -> tuple[pathlib.Path, str] | None:
    configured = series.get("voice_guide")
    if configured is None:
        return None
    if not isinstance(configured, str) or not configured:
        raise StartArticleError("series voice_guide must be a path string")
    path = repo / "press" / "series" / series_id / configured
    return path, _read(path, label=f"pinned voice guide for {series_id}")


def _write_pinned_coach_record(
    artifacts: pathlib.Path,
    *,
    repo: pathlib.Path,
    revision: str,
    guide_path: pathlib.Path,
    guide: str,
) -> None:
    """Stand the pinned guide in for the coach's first invocation.

    The artifact contract expects a writing-coach invocation whether or not the
    role ran, so a published article carries the guide that governed it either
    way.
    """
    invocation = artifacts / "writing-coach" / "01"
    invocation.mkdir(parents=True)
    (invocation / "brief.md").write_text(
        "# Writing coach brief\n\n"
        f"This series pins a standing voice guide at "
        f"`{_relative(guide_path, repo)}`, so no writing coach was invoked for "
        f"this article. The `voice-guide.md` beside this brief is that file at "
        f"checkout revision `{revision}`.\n\n"
        "Edit the pinned guide in the press to change how the series sounds.\n",
        encoding="utf-8",
    )
    (invocation / "voice-guide.md").write_text(guide, encoding="utf-8")


def _write_context(
    workspace: pathlib.Path,
    *,
    repo: pathlib.Path,
    template_id: str,
    template_folder: pathlib.Path,
    effective_template: Mapping[str, object],
    runtime_assets: object,
) -> None:
    context = workspace / ".nb-context"
    furniture = context / "furniture"
    furniture.mkdir(parents=True)

    contract: dict[str, object] = {
        "template": template_id,
        "source": _relative(template_folder / "manifest.yaml", repo),
        **effective_template,
    }
    (context / "template-contract.yaml").write_text(
        yaml.safe_dump(contract, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (context / "runtime-assets.yaml").write_text(
        yaml.safe_dump({"assets": runtime_assets}, sort_keys=False),
        encoding="utf-8",
    )

    sources = (
        (repo / "templates" / "FURNITURE.md", furniture / "engine.md"),
        (repo / "press" / "furniture" / "catalog.md", furniture / "press.md"),
        (template_folder / "furniture.md", furniture / "template.md"),
    )
    for source, target in sources:
        if source.is_file() and not source.is_symlink():
            shutil.copyfile(source, target)


def initialize(
    *,
    repo: pathlib.Path,
    workspace: pathlib.Path,
    series_id: str,
    slug: str,
    template_id: str,
    tags: Sequence[str] = (),
) -> pathlib.Path:
    repo = repo.resolve()
    workspace = workspace.resolve()
    if nb_meta.SERIES_RE.fullmatch(series_id) is None:
        raise StartArticleError(f"invalid series: {series_id!r}")
    if nb_meta.SLUG_RE.fullmatch(slug) is None:
        raise StartArticleError(f"invalid slug: {slug!r}")
    if workspace.is_symlink() or (workspace.exists() and not workspace.is_dir()):
        raise StartArticleError(f"workspace must be a directory: {workspace}")
    if workspace.exists() and any(workspace.iterdir()):
        raise StartArticleError(f"workspace is not empty: {workspace}")

    loaded, series_path = load_series(str(repo), series_id)
    if loaded is None:
        raise StartArticleError(f"unknown series: {series_path}")
    series = _mapping(loaded, label=f"series {series_id}")
    if template_id not in template_choices(series):
        raise StartArticleError(
            f"template {template_id!r} is not allowed for series {series_id!r}"
        )

    registry = load_registry(str(repo))
    template = registry.get(template_id)
    if not isinstance(template, Mapping):
        raise StartArticleError(f"unknown template: {template_id}")
    folders = template_dirs(str(repo))
    template_folder_value = folders.get(template_id)
    if template_folder_value is None:
        raise StartArticleError(f"template package is missing: {template_id}")
    template_folder = pathlib.Path(template_folder_value)
    skeleton = template_folder / "skeleton.html"
    _read(skeleton, label=f"template skeleton for {template_id}")

    item = _selected_item(series, slug)
    requires_item = series.get("mode") in ("collection", "sequence") or (
        series.get("mode") == "open" and series.get("cadence") == "manual"
    )
    if item is None and requires_item:
        raise StartArticleError(f"series {series_id!r} has no item {slug!r}")
    resolved_tags = _resolve_tags(item=item, requested=tags)
    pinned = _pinned_voice_guide(repo, series_id=series_id, series=series)
    revision = _checkout_revision(repo)
    direction = _editorial_direction(
        repo,
        revision=revision,
        series_id=series_id,
        series=series,
        template_folder=template_folder,
        tags=resolved_tags,
        item=item,
    )
    effective = apply_template_bands(template, series=series)
    runtime_assets = _site_assets(repo)

    workspace.mkdir(parents=True, exist_ok=True)
    article = workspace / "library" / series_id / f"{slug}.html"
    article.parent.mkdir(parents=True)
    shutil.copyfile(skeleton, article)
    _write_context(
        workspace,
        repo=repo,
        template_id=template_id,
        template_folder=template_folder,
        effective_template=effective,
        runtime_assets=runtime_assets,
    )
    artifacts = workspace / "agent-artifacts" / series_id / slug
    artifacts.mkdir(parents=True)
    (artifacts / "editorial-direction.md").write_text(direction, encoding="utf-8")
    if pinned is not None:
        guide_path, guide = pinned
        _write_pinned_coach_record(
            artifacts,
            repo=repo,
            revision=revision,
            guide_path=guide_path,
            guide=guide,
        )
    return article


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Initialize one article with its exact authoring context"
    )
    command.add_argument("series", help="configured series ID")
    command.add_argument("slug", help="article slug")
    command.add_argument("--template", required=True, help="selected template ID")
    command.add_argument("--workspace", required=True, type=pathlib.Path)
    command.add_argument("--tag", action="append", default=[], help="open-item tag")
    command.add_argument(
        "--repo",
        default=os.getenv("NB_ROOT", "."),
        type=pathlib.Path,
        help="main checkout (defaults to the checkout owning nb)",
    )
    return command


def main(arguments: list[str] | None = None) -> None:
    options = parser().parse_args(arguments)
    try:
        article = initialize(
            repo=options.repo,
            workspace=options.workspace,
            series_id=options.series,
            slug=options.slug,
            template_id=options.template,
            tags=options.tag,
        )
    except StartArticleError as error:
        raise SystemExit(f"cannot initialize article: {error}") from error
    print(article)


if __name__ == "__main__":
    main()
