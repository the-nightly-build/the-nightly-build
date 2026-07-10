#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Validate the press configuration before anything schedules or publishes.

Covers press/site.yaml, the merged template registry, and every
series/<id>/series.yaml. Both setup.sh and the librarian run it after
each configuration change; it applies the same constraints the proof enforces
at publish time, so mistakes surface while a human is watching instead of
during an unattended nightly run.

Run: python3 engine/validate_config.py [--repo .]
Exit 0 iff everything validates.
"""

import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.stderr.write("validate_config.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

SERIES_ID_RE = re.compile(r"^[a-z0-9-]{1,32}$")
SLUG_RE = re.compile(r"^[a-z0-9-]{1,64}$")
MODES = {"collection", "sequence", "rolling", "open"}
TEMPLATE_KEYS = {
    "class",
    "words",
    "items",
    "sections",
    "flex_sections",
    "cite_rule",
    "cite_exempt",
    "require_why",
    "modes",
}
CITE_RULES = {"per-section", "per-item"}
SERIES_KEYS = {
    "name",
    "mode",
    "template",
    "templates",
    "prompt",
    "autopublish",
    "strict",
    "min_sources",
    "words",
    "items",
    "tags",
    "consult",
    "required_docs",
    "sources_exclusive",
    "cadence",
    "paused",
    "selection",
    "section",
}
DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
CADENCE_WORDS = {"daily", "weekdays", "weekends"}
SELECTIONS = {"in-order", "random"}


def cadence_is_valid(cadence):
    if isinstance(cadence, str):
        return cadence in CADENCE_WORDS
    return (
        isinstance(cadence, list)
        and len(cadence) > 0
        and all(d in DAY_NAMES for d in cadence)
    )


def load(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def check_site(repo, errors):
    label = "press"
    path = os.path.join(repo, "press", "site.yaml")
    if not os.path.isfile(path):
        return  # optional: the engine ships defaults
    site = load(path) or {}
    if "title" in site and (
        not isinstance(site["title"], str) or not site["title"].strip()
    ):
        errors.append(f"{label}/site.yaml: 'title' must be a non-empty string")
    theme = site.get("theme")
    if theme is not None and (
        not isinstance(theme, str) or not os.path.isfile(os.path.join(repo, theme))
    ):
        errors.append(f"{label}/site.yaml: theme file not found: {theme!r}")
    if site.get("appearance", "auto") not in ("auto", "light", "dark"):
        errors.append(f"{label}/site.yaml: 'appearance' must be auto | light | dark")
    if site.get("front", "comfortable") not in ("comfortable", "compact"):
        errors.append(f"{label}/site.yaml: 'front' must be comfortable | compact")
    footer = site.get("footer")
    if footer is not None and (
        not isinstance(footer, str) or not footer.strip() or len(footer) > 80
    ):
        errors.append(
            f"{label}/site.yaml: 'footer' must be a non-empty string "
            f"of at most 80 characters"
        )
    check_site_assets(site.get("assets"), errors=errors)
    check_site_directory(site.get("directory"), errors=errors)


def check_site_assets(assets, *, errors):
    # Trusted external libraries a press loads on every page. Owner-authored on
    # main, so they must be https and Subresource-Integrity-pinned: the SRI hash
    # is what lets the browser refuse a tampered CDN response.
    if assets is None:
        return
    prefix = "press/site.yaml"
    if not isinstance(assets, dict):
        errors.append(f"{prefix}: 'assets' must be a mapping of scripts/styles")
        return
    unknown = set(assets) - {"scripts", "styles"}
    if unknown:
        errors.append(f"{prefix}: assets: unknown keys {sorted(unknown)}")
    for kind in ("scripts", "styles"):
        items = assets.get(kind)
        if items is None:
            continue
        if not isinstance(items, list):
            errors.append(f"{prefix}: assets.{kind} must be a list")
            continue
        for i, item in enumerate(items):
            where = f"{prefix}: assets.{kind}[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{where}: must be a mapping with 'url' and 'integrity'")
                continue
            extra = set(item) - {"url", "integrity", "defer"}
            if extra:
                errors.append(f"{where}: unknown keys {sorted(extra)}")
            url = item.get("url")
            if not isinstance(url, str) or not url.startswith("https://"):
                errors.append(f"{where}: 'url' must be an https URL")
            integrity = item.get("integrity")
            if not isinstance(integrity, str) or not re.match(
                r"^sha(256|384|512)-.+", integrity
            ):
                errors.append(
                    f"{where}: 'integrity' is required and must be an SRI hash "
                    f"(sha256-, sha384-, or sha512-...)"
                )
            if "defer" in item and not isinstance(item.get("defer"), bool):
                errors.append(f"{where}: 'defer' must be true or false")


def check_site_directory(directory, *, errors):
    # Directory listing is opt-out: a press is listed unless it sets
    # directory.publish: false. The public URL is derived at build time (from the
    # Pages base URL), never configured, and the description is optional; a 'url'
    # key is intentionally not accepted, which the unknown-key check enforces.
    if directory is None:
        return
    prefix = "press/site.yaml"
    if not isinstance(directory, dict):
        errors.append(f"{prefix}: 'directory' must be a mapping of publish/description")
        return
    unknown = set(directory) - {"publish", "description"}
    if unknown:
        errors.append(f"{prefix}: directory: unknown keys {sorted(unknown)}")
    publish = directory.get("publish", False)
    if not isinstance(publish, bool):
        errors.append(f"{prefix}: directory.publish must be true or false")
    description = directory.get("description")
    if description is not None and (
        not isinstance(description, str)
        or not description.strip()
        or len(description.strip()) > 280
    ):
        errors.append(
            f"{prefix}: directory.description must be a non-empty string "
            f"of at most 280 characters"
        )


def check_registry(repo, errors):
    path = os.path.join(repo, "templates", "registry.yaml")
    if not os.path.isfile(path):
        errors.append("templates/registry.yaml is missing")
        return {}
    registry = load(path) or {}
    press_path = os.path.join(repo, "press", "templates", "registry.yaml")
    if os.path.isfile(press_path):
        registry.update(load(press_path) or {})
    for tid, entry in registry.items():
        where = f"registry '{tid}'"
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        unknown = set(entry) - TEMPLATE_KEYS
        if unknown:
            errors.append(f"{where}: unknown keys {sorted(unknown)}")
        if entry.get("class") not in ("longread", "shortread"):
            errors.append(f"{where}: class must be longread | shortread")
        if not entry.get("sections"):
            errors.append(f"{where}: 'sections' is required")
        elif "sources" not in entry["sections"]:
            errors.append(f"{where}: sections must include 'sources'")
        if entry.get("cite_rule") not in CITE_RULES:
            errors.append(f"{where}: cite_rule must be one of {sorted(CITE_RULES)}")
        if not set(entry.get("modes") or []) <= MODES:
            errors.append(f"{where}: modes must be a subset of {sorted(MODES)}")
        cite_exempt = entry.get("cite_exempt")
        if cite_exempt is not None and not (
            isinstance(cite_exempt, list)
            and all(isinstance(x, str) for x in cite_exempt)
        ):
            errors.append(f"{where}: 'cite_exempt' must be a list of section names")
        if not isinstance(entry.get("require_why", False), bool):
            errors.append(f"{where}: 'require_why' must be true or false")
        for band_key in ("words", "items", "flex_sections"):
            band = entry.get(band_key)
            if band is not None and not (
                isinstance(band, list)
                and len(band) == 2
                and all(isinstance(x, int) for x in band)
                and band[0] <= band[1]
            ):
                errors.append(f"{where}: '{band_key}' must be [low, high] integers")
        candidates = [
            os.path.join(repo, "press", "templates", f"{tid}.html"),
            os.path.join(repo, "templates", f"{tid}.html"),
        ]
        if not any(os.path.isfile(c) for c in candidates):
            errors.append(
                f"{where}: no {tid}.html in the press templates folder or templates/"
            )
    return registry


def check_required_docs(docs, root, sid, where, errors):
    # Shared by series-level and item-level required_docs. Each entry is a
    # mapping carrying an 'id' and a 'path' to a committed file; the proof
    # later demands a matching data-nb-required source entry.
    if docs is None:
        return
    if not isinstance(docs, list):
        errors.append(f"{where}: 'required_docs' must be a list")
        return
    for doc in docs:
        if not isinstance(doc, dict):
            errors.append(
                f"{where}: required_docs entry must be a mapping with 'id' and 'path'"
            )
            continue
        dpath = os.path.join(root, sid, doc.get("path", ""))
        if not doc.get("id") or not os.path.isfile(dpath):
            errors.append(
                f"{where}: required_doc "
                f"{doc.get('id')!r} file not found: {doc.get('path')!r}"
            )


def check_series(repo, registry, *, errors):
    label = "press"
    root = os.path.join(repo, "press", "series")
    if not os.path.isdir(root):
        return
    for sid in sorted(os.listdir(root)):
        if sid.startswith("_") or not os.path.isdir(os.path.join(root, sid)):
            continue
        where = f"{label}/series/{sid}"
        if not SERIES_ID_RE.match(sid):
            errors.append(f"{where}: id must match {SERIES_ID_RE.pattern}")
        path = os.path.join(root, sid, "series.yaml")
        if not os.path.isfile(path):
            errors.append(f"{where}: series.yaml is missing")
            continue
        try:
            cfg = load(path) or {}
        except yaml.YAMLError as e:
            errors.append(
                f"{where}: series.yaml is not valid YAML ({e.__class__.__name__})"
            )
            continue
        if not isinstance(cfg, dict):
            errors.append(f"{where}: series.yaml must be a mapping")
            continue
        unknown = set(cfg) - SERIES_KEYS
        if unknown:
            errors.append(
                f"{where}: unknown keys {sorted(unknown)} — "
                f"typo? (known: {sorted(SERIES_KEYS)})"
            )
        if not isinstance(cfg.get("name"), str) or not cfg["name"].strip():
            errors.append(f"{where}: 'name' must be a non-empty string")
        mode = cfg.get("mode")
        if mode not in MODES:
            errors.append(f"{where}: mode must be one of {sorted(MODES)}")
        cadence = cfg.get("cadence")
        if cadence is not None and not cadence_is_valid(cadence):
            errors.append(
                f"{where}: cadence must be daily | weekdays | "
                f"weekends | a list of day names {list(DAY_NAMES)}"
            )
        if not isinstance(cfg.get("paused", False), bool):
            errors.append(f"{where}: 'paused' must be true or false")
        for flag in ("autopublish", "strict"):
            if not isinstance(cfg.get(flag, False), bool):
                errors.append(f"{where}: '{flag}' must be true or false")
        min_sources = cfg.get("min_sources")
        if min_sources is not None and (
            not isinstance(min_sources, int) or isinstance(min_sources, bool)
        ):
            errors.append(f"{where}: 'min_sources' must be an integer")
        section = cfg.get("section")
        if section is not None and (
            not isinstance(section, str) or not section.strip()
        ):
            errors.append(f"{where}: 'section' must be a non-empty string")
        selection = cfg.get("selection")
        if selection is not None:
            if selection not in SELECTIONS:
                errors.append(f"{where}: selection must be one of {sorted(SELECTIONS)}")
            elif mode != "collection":
                errors.append(f"{where}: 'selection' only applies to collection mode")
        templates = cfg.get("templates")
        if templates is not None and mode != "open":
            errors.append(
                f"{where}: 'templates' (a choice list) is only valid "
                f"in open mode; use 'template'"
            )
            templates = None
        if templates is not None and (not isinstance(templates, list) or not templates):
            errors.append(f"{where}: 'templates' must be a non-empty list")
            templates = None
        if mode == "open" and templates and cfg.get("template"):
            errors.append(f"{where}: use 'template' or 'templates', not both")
        if mode == "open" and not templates and not cfg.get("template"):
            errors.append(
                f"{where}: open mode requires 'template' or a 'templates' choice list"
            )
            allowed = []
        else:
            allowed = templates or [cfg.get("template")]
        tregs = []
        for template in allowed:
            treg = registry.get(template)
            if not treg:
                errors.append(f"{where}: template '{template}' not in the registry")
            else:
                tregs.append(treg)
                if mode in MODES and mode not in (treg.get("modes") or []):
                    errors.append(
                        f"{where}: mode '{mode}' not allowed for "
                        f"template '{template}' "
                        f"(allowed: {treg.get('modes')})"
                    )
        prompt = cfg.get("prompt")
        if prompt and not os.path.isfile(os.path.join(root, sid, prompt)):
            errors.append(f"{where}: prompt file '{prompt}' not found")
        for tag, frag in (cfg.get("tags") or {}).items():
            if not os.path.isfile(os.path.normpath(os.path.join(root, sid, frag))):
                errors.append(f"{where}: tag '{tag}' fragment '{frag}' not found")
        words = cfg.get("words")
        if words is not None:
            floors = [t["words"][0] for t in tregs if t.get("words")]
            if not (
                isinstance(words, list)
                and len(words) == 2
                and all(isinstance(x, int) for x in words)
                and words[0] <= words[1]
            ):
                errors.append(f"{where}: 'words' must be [low, high] integers")
            elif floors and words[0] < max(floors):
                errors.append(
                    f"{where}: words floor {words[0]} loosens the "
                    f"registry floor {max(floors)} (may only tighten)"
                )
        items = cfg.get("items") or []
        if mode in ("collection", "sequence") and not items:
            errors.append(f"{where}: {mode} mode requires 'items'")
        if mode == "rolling" and items:
            errors.append(f"{where}: rolling mode must not define 'items'")
        seen = set()
        for i, item in enumerate(items):
            item = item or {}
            slug = item.get("slug")
            if not isinstance(slug, str) or not SLUG_RE.match(slug):
                errors.append(
                    f"{where}: item #{i + 1} slug {slug!r} must match {SLUG_RE.pattern}"
                )
            else:
                if slug in seen:
                    errors.append(f"{where}: duplicate item slug '{slug}'")
                seen.add(slug)  # only valid slugs seed the duplicate check
            check_required_docs(item.get("required_docs"), root, sid, where, errors)
        check_required_docs(cfg.get("required_docs"), root, sid, where, errors)
        item_consult = [p for item in items for p in (item or {}).get("consult") or []]
        for prefix in (cfg.get("consult") or []) + item_consult:
            if not str(prefix).startswith("https://"):
                errors.append(
                    f"{where}: consult entries must be https:// "
                    f"prefixes, got {prefix!r}"
                )
        exclusive = cfg.get("sources_exclusive", False)
        if not isinstance(exclusive, bool):
            errors.append(f"{where}: sources_exclusive must be true or false")
        elif exclusive:
            has_docs = cfg.get("required_docs") or any(
                (item or {}).get("required_docs") for item in items
            )
            if not (cfg.get("consult") or item_consult or has_docs):
                errors.append(
                    f"{where}: sources_exclusive requires declared "
                    f"sources (consult and/or required_docs)"
                )


def main(argv=None):
    p = argparse.ArgumentParser(description="Validate Nightly Build configuration")
    p.add_argument("--repo", default=".", help="repo root (main checkout)")
    args = p.parse_args(argv)

    errors = []
    check_site(args.repo, errors)
    registry = check_registry(args.repo, errors)
    check_series(args.repo, registry, errors=errors)

    if errors:
        print(f"configuration INVALID — {len(errors)} problem(s):")
        for e in errors:
            print(f"  ✗ {e}")
        return 1
    print("configuration valid: site.yaml, registry, and all series check out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
