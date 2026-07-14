"""What the press configured: series, template manifests, banned terms, library state."""

import os
import sys

from nb import meta as nb_meta
from nb.site.assets import template_dirs

try:
    import yaml
except ImportError:
    sys.stderr.write("check.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)


def load_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_registry(repo):
    """Load every template's manifest, press packages shadowing shipped.

    template_dirs owns what counts as a template package and how press/
    shadows shipped; the manifests it finds carry the geometry the proof
    enforces.
    """
    return {
        tid: load_yaml(os.path.join(folder, "manifest.yaml")) or {}
        for tid, folder in template_dirs(repo).items()
    }


def find_template(repo, template_id):
    for base in (
        os.path.join(repo, "press", "templates"),  # press/ shadows shipped templates/
        os.path.join(repo, "templates"),
    ):
        path = os.path.join(base, template_id, "skeleton.html")
        if os.path.isfile(path):
            return path
    return None


def load_banned_terms(repo):
    """Merge the engine's banned-terms list with the press's.

    spec/banned-terms.yaml seeds the list; press/banned-terms.yaml layers
    over it by id — a new id adds a ban, a repeated id updates only the
    fields it states, and enabled false retires an entry. Malformed entries
    are skipped here; validate_config.py is where authors hear about them.
    """
    merged = {}
    for path in (
        os.path.join(repo, "spec", "banned-terms.yaml"),
        os.path.join(repo, "press", "banned-terms.yaml"),
    ):
        if not os.path.isfile(path):
            continue
        entries = load_yaml(path) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("id"):
                continue
            merged.setdefault(entry["id"], {}).update(entry)
    return [e for e in merged.values() if e.get("enabled", True) and e.get("terms")]


def load_series(repo, series_id) -> tuple[dict | None, str]:
    path = os.path.join(repo, "press", "series", series_id, "series.yaml")
    if not os.path.isfile(path):
        return None, path
    return load_yaml(path), path


def published_slugs(library_dir, series_id) -> set[str] | None:
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
    return {f[:-5] for f in os.listdir(base) if f.endswith(".html")}
