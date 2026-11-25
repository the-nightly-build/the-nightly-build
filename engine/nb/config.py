"""Read the press configuration used by the engine.

This module owns the shared configuration readers and the small amount of
normalization needed before validation, proof, duty tooling, or site building
consumes a series and its selected template. Keeping template choice and band
precedence here prevents those consumers from silently implementing different
interpretations of the same press configuration.
"""

from __future__ import annotations

import pathlib
import sys
from collections.abc import Mapping

from nb import meta as nb_meta
from nb.site.assets import template_dirs

try:
    import yaml
except ImportError:
    sys.stderr.write("check.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)


TEMPLATE_BAND_KEYS = ("words", "items", "flex_sections")

__all__ = (
    "TEMPLATE_BAND_KEYS",
    "apply_template_bands",
    "find_template",
    "load_banned_terms",
    "load_registry",
    "load_series",
    "load_yaml",
    "published_slugs",
    "template_choices",
)


def load_yaml(path: str | pathlib.Path) -> object:
    with pathlib.Path(path).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_registry(repo: str | pathlib.Path) -> dict[str, object]:
    """Load every template's manifest, press packages shadowing shipped.

    template_dirs owns what counts as a template package and how press/
    shadows shipped; the manifests it finds carry the geometry the proof
    enforces.
    """
    return {
        tid: load_yaml(pathlib.Path(folder) / "manifest.yaml") or {} for tid, folder in template_dirs(str(repo)).items()
    }


def template_choices(series: Mapping[str, object]) -> list[str]:
    """Return the series' allowed template IDs in one normalized shape.

    A valid series declares either one ``template`` string or a non-empty
    ``templates`` list.  This helper remains defensive for proof runs against
    a press that skipped configuration validation: malformed values produce an
    empty or partially usable choice list instead of an unhashable registry
    lookup.
    """
    choices = series.get("templates")
    if isinstance(choices, list):
        return [choice for choice in choices if isinstance(choice, str)]
    template = series.get("template")
    return [template] if isinstance(template, str) else []


def apply_template_bands(template: Mapping[str, object], *, series: Mapping[str, object]) -> dict[str, object]:
    """Layer series policy bands over one template's defaults.

    Only the three public geometry bands are copied.  Structural manifest
    fields remain owned by the template package, while an absent template band
    simply means that no default exists until the series supplies one.
    """
    effective: dict[str, object] = dict(template)
    template_bands = template.get("bands")
    bands: dict[str, object] = (
        {str(key): value for key, value in template_bands.items()} if isinstance(template_bands, Mapping) else {}
    )
    series_bands = series.get("bands")
    if isinstance(series_bands, Mapping):
        bands.update(
            {key: value for key, value in series_bands.items() if isinstance(key, str) and key in TEMPLATE_BAND_KEYS}
        )
    effective["bands"] = bands
    return effective


def find_template(repo: str | pathlib.Path, template_id: str) -> str | None:
    repo_path = pathlib.Path(repo)
    for base in (
        repo_path / "press" / "templates",  # press/ shadows shipped templates/
        repo_path / "templates",
    ):
        path = base / template_id / "skeleton.html"
        if path.is_file():
            return str(path)
    return None


def load_banned_terms(repo: str | pathlib.Path) -> list[dict[str, object]]:
    """Merge the engine's banned-terms list with the press's.

    spec/banned-terms.yaml seeds the list; press/banned-terms.yaml layers
    over it by id — a new id adds a ban, a repeated id updates only the
    fields it states, and enabled false retires an entry. Malformed entries
    are skipped here; validate_config.py is where authors hear about them.
    """
    repo_path = pathlib.Path(repo)
    merged: dict[str, dict[str, object]] = {}
    for path in (
        repo_path / "spec" / "banned-terms.yaml",
        repo_path / "press" / "banned-terms.yaml",
    ):
        if not path.is_file():
            continue
        entries = load_yaml(path) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            normalized = {str(key): value for key, value in entry.items()}
            if not normalized.get("id"):
                continue
            entry_id = str(normalized["id"])
            merged.setdefault(entry_id, {}).update(normalized)
    return [e for e in merged.values() if e.get("enabled", True) and e.get("terms")]


def load_series(repo: str | pathlib.Path, series_id: str) -> tuple[object, str]:
    path = pathlib.Path(repo) / "press" / "series" / series_id / "series.yaml"
    if not path.is_file():
        return None, str(path)
    return load_yaml(path), str(path)


def published_slugs(library_dir: str | pathlib.Path | None, series_id: str) -> set[str] | None:
    """Return the set of published slugs for a series.

    Returns None when no library checkout was provided, which callers
    must treat as unknowable rather than empty: dedupe and sequence
    checks are skipped with a note instead of firing falsely.
    """
    if not library_dir:
        return None
    base = nb_meta.series_dir(library_dir, series_id)
    if base is None:
        return set()  # library exists but series dir doesn't => nothing published
    return {entry.name.removesuffix(".html") for entry in pathlib.Path(base).iterdir() if entry.name.endswith(".html")}
