#!/usr/bin/env python3
"""
The Nightly Build — engine/validate_config.py

Validates the repo's configuration surface: site.yaml, templates/registry.yaml,
and every series/<id>/series.yaml. Used by setup.sh and the Librarian; the same
constraints the proof enforces at publish time, caught at configuration time.

Run: python3 engine/validate_config.py [--repo .]
Exit 0 iff everything validates.
"""

import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("validate_config.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

SERIES_ID_RE = re.compile(r"^[a-z0-9-]{1,32}$")
SLUG_RE = re.compile(r"^[a-z0-9-]{1,64}$")
MODES = {"collection", "sequence", "rolling"}
TEMPLATE_KEYS = {"class", "words", "items", "slides", "sections", "cite_rule",
                 "modes", "furniture"}
CITE_RULES = {"per-section", "per-item", "per-slide"}


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def check_site(repo, errors):
    path = os.path.join(repo, "site.yaml")
    if not os.path.isfile(path):
        errors.append("site.yaml is missing")
        return
    site = load(path) or {}
    if not isinstance(site.get("title"), str) or not site["title"].strip():
        errors.append("site.yaml: 'title' must be a non-empty string")
    theme = site.get("theme")
    if not isinstance(theme, str) or not os.path.isfile(os.path.join(repo, theme)):
        errors.append(f"site.yaml: theme file not found: {theme!r}")
    if site.get("appearance") not in ("auto", "light", "dark"):
        errors.append("site.yaml: 'appearance' must be auto | light | dark")


def check_registry(repo, errors):
    path = os.path.join(repo, "templates", "registry.yaml")
    if not os.path.isfile(path):
        errors.append("templates/registry.yaml is missing")
        return {}
    registry = load(path) or {}
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
        for band_key in ("words", "items", "slides"):
            band = entry.get(band_key)
            if band is not None and not (
                    isinstance(band, list) and len(band) == 2
                    and all(isinstance(x, int) for x in band)
                    and band[0] <= band[1]):
                errors.append(f"{where}: '{band_key}' must be [low, high] integers")
        template_file = os.path.join(repo, "templates", f"{tid}.html")
        if not os.path.isfile(template_file):
            errors.append(f"{where}: templates/{tid}.html does not exist")
    return registry


def check_series(repo, registry, errors):
    root = os.path.join(repo, "series")
    if not os.path.isdir(root):
        return
    for sid in sorted(os.listdir(root)):
        if sid.startswith("_") or not os.path.isdir(os.path.join(root, sid)):
            continue
        where = f"series/{sid}"
        if not SERIES_ID_RE.match(sid):
            errors.append(f"{where}: id must match {SERIES_ID_RE.pattern}")
        path = os.path.join(root, sid, "series.yaml")
        if not os.path.isfile(path):
            errors.append(f"{where}: series.yaml is missing")
            continue
        cfg = load(path) or {}
        if not isinstance(cfg.get("name"), str) or not cfg["name"].strip():
            errors.append(f"{where}: 'name' must be a non-empty string")
        mode = cfg.get("mode")
        if mode not in MODES:
            errors.append(f"{where}: mode must be one of {sorted(MODES)}")
        template = cfg.get("template")
        treg = registry.get(template)
        if not treg:
            errors.append(f"{where}: template '{template}' not in the registry")
        elif mode in MODES and mode not in (treg.get("modes") or []):
            errors.append(f"{where}: mode '{mode}' not allowed for template "
                          f"'{template}' (allowed: {treg.get('modes')})")
        prompt = cfg.get("prompt")
        if prompt and not os.path.isfile(os.path.join(root, sid, prompt)):
            errors.append(f"{where}: prompt file '{prompt}' not found")
        for tag, frag in (cfg.get("tags") or {}).items():
            if not os.path.isfile(os.path.normpath(os.path.join(root, sid, frag))):
                errors.append(f"{where}: tag '{tag}' fragment '{frag}' not found")
        words = cfg.get("words")
        if words is not None:
            reg_band = (treg or {}).get("words")
            if not (isinstance(words, list) and len(words) == 2
                    and all(isinstance(x, int) for x in words)
                    and words[0] <= words[1]):
                errors.append(f"{where}: 'words' must be [low, high] integers")
            elif reg_band and words[0] < reg_band[0]:
                errors.append(f"{where}: words floor {words[0]} loosens the "
                              f"registry floor {reg_band[0]} (may only tighten)")
        items = cfg.get("items") or []
        if mode in ("collection", "sequence") and not items:
            errors.append(f"{where}: {mode} mode requires 'items'")
        if mode == "rolling" and items:
            errors.append(f"{where}: rolling mode must not define 'items'")
        seen = set()
        for i, item in enumerate(items):
            slug = (item or {}).get("slug")
            if not isinstance(slug, str) or not SLUG_RE.match(slug):
                errors.append(f"{where}: item #{i + 1} slug {slug!r} must match "
                              f"{SLUG_RE.pattern}")
            elif slug in seen:
                errors.append(f"{where}: duplicate item slug '{slug}'")
            seen.add(slug)
            for doc in (item or {}).get("required_docs") or []:
                dpath = os.path.join(root, sid, doc.get("path", ""))
                if not doc.get("id") or not os.path.isfile(dpath):
                    errors.append(f"{where}: required_doc "
                                  f"{doc.get('id')!r} file not found: {doc.get('path')!r}")
        item_consult = [p for item in items
                        for p in (item or {}).get("consult") or []]
        for prefix in (cfg.get("consult") or []) + item_consult:
            if not str(prefix).startswith("https://"):
                errors.append(f"{where}: consult entries must be https:// "
                              f"prefixes, got {prefix!r}")
        exclusive = cfg.get("sources_exclusive", False)
        if not isinstance(exclusive, bool):
            errors.append(f"{where}: sources_exclusive must be true or false")
        elif exclusive:
            has_docs = (cfg.get("required_docs")
                        or any((item or {}).get("required_docs") for item in items))
            if not (cfg.get("consult") or item_consult or has_docs):
                errors.append(f"{where}: sources_exclusive requires declared "
                              f"sources (consult and/or required_docs)")


def main(argv=None):
    p = argparse.ArgumentParser(description="Validate Nightly Build configuration")
    p.add_argument("--repo", default=".", help="repo root (main checkout)")
    args = p.parse_args(argv)

    errors = []
    check_site(args.repo, errors)
    registry = check_registry(args.repo, errors)
    check_series(args.repo, registry, errors)

    if errors:
        print(f"configuration INVALID — {len(errors)} problem(s):")
        for e in errors:
            print(f"  ✗ {e}")
        return 1
    print("configuration valid: site.yaml, registry, and all series check out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
