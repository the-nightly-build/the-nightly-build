# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "tinycss2"]
# ///
"""Validate the press configuration before anything schedules or publishes.

Covers press/site.yaml, the banned-terms lists, the merged template
registry, and every series/<id>/series.yaml. Both scripts/setup.sh and the user assistant run it after
each configuration change; it applies the same constraints the proof enforces
at publish time, so mistakes surface while a human is watching instead of
during an unattended nightly run.

Run: python3 engine/validate_config.py [--repo .]
Exit 0 iff everything validates.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import TYPE_CHECKING

import build_site
import check
import duty
from nb import meta as nb_meta
from nb.config import TEMPLATE_BAND_KEYS, template_choices
from nb.production_policy import PROFILES, STAGES

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

try:
    import yaml
except ImportError:
    sys.stderr.write("validate_config.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

# The grammar the proof enforces at 2am is the grammar authors validate
# against by daylight — shared definitions, or the two drift apart.
SERIES_ID_RE = nb_meta.SERIES_RE
SLUG_RE = nb_meta.SLUG_RE
MODES = frozenset(nb_meta.MODES)
TEMPLATE_KEYS = {
    "chrome",
    "class",
    "bands",
    "sections",
    "cite_rule",
    "cite_exempt",
    "about",
    "flex_components",
}
CITE_RULES = {"per-section", "per-item"}
SOURCE_KINDS = frozenset(check.SOURCE_KINDS)
SERIES_KEYS = {
    "name",
    "mode",
    "template",
    "templates",
    "prompt",
    "voice_guide",
    "strict",
    "min_sources",
    "sources_by_kind",
    "per_item_sources",
    "rubric",
    "bands",
    "items",
    "tags",
    "consult",
    "required_docs",
    "sources_exclusive",
    "cadence",
    "paused",
    "selection",
    "section",
    "production",
}
BANNED_TERM_KEYS = {"id", "terms", "max", "suggestion", "enabled"}
SELECTIONS = {"in-order", "random"}
PRODUCTION_KEYS = {"profile", "required", "stages"}
PRODUCTION_STAGE_KEYS = {"model", "effort", "required"}
RUBRIC_KEYS = {"id", "name", "note"}
MAX_FOOTER_LEN = 80
MAX_DIRECTORY_DESCRIPTION_LEN = 280
BAND_LEN = 2


def load(path: str | pathlib.Path) -> object:
    with pathlib.Path(path).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def check_site(repo: str | pathlib.Path, errors: list[str]) -> None:
    label = "press"
    repo_path = pathlib.Path(repo)
    path = repo_path / "press" / "site.yaml"
    if not path.is_file():
        return  # optional: the engine ships defaults
    raw_site = load(path) or {}
    if not isinstance(raw_site, dict):
        errors.append(f"{label}/site.yaml: must be a mapping")
        return
    site = {str(key): value for key, value in raw_site.items()}
    if "title" in site and (not isinstance(site["title"], str) or not site["title"].strip()):
        errors.append(f"{label}/site.yaml: 'title' must be a non-empty string")
    theme = site.get("theme")
    if theme is not None and (not isinstance(theme, str) or not (repo_path / theme).is_file()):
        errors.append(f"{label}/site.yaml: theme file not found: {theme!r}")
    if site.get("appearance", "auto") not in ("auto", "light", "dark"):
        errors.append(f"{label}/site.yaml: 'appearance' must be auto | light | dark")
    if site.get("front", "compact") not in ("comfortable", "compact"):
        errors.append(f"{label}/site.yaml: 'front' must be comfortable | compact")
    footer = site.get("footer")
    if footer is not None and (not isinstance(footer, str) or not footer.strip() or len(footer) > MAX_FOOTER_LEN):
        errors.append(f"{label}/site.yaml: 'footer' must be a non-empty string of at most {MAX_FOOTER_LEN} characters")
    check_site_assets(site.get("assets"), errors=errors)
    check_site_directory(site.get("directory"), errors=errors)


def _as_count(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _check_nonempty_str_field(mapping: Mapping[str, object], *, field: str, where: str, errors: list[str]) -> None:
    value = mapping.get(field)
    if value is not None and (not isinstance(value, str) or not value.strip()):
        errors.append(f"{where}: {field} must be a non-empty string")


def _check_production_stage(policy: object, *, stage_where: str, errors: list[str]) -> None:
    if not isinstance(policy, dict):
        errors.append(f"{stage_where}: must be a mapping")
        return
    stage_map = {str(key): item for key, item in policy.items()}
    unknown_stage_keys = set(stage_map) - PRODUCTION_STAGE_KEYS
    if unknown_stage_keys:
        errors.append(f"{stage_where}: unknown keys {sorted(unknown_stage_keys)}")
    for field in ("model", "effort"):
        _check_nonempty_str_field(stage_map, field=field, where=stage_where, errors=errors)
    stage_required = stage_map.get("required")
    if stage_required is not None and not isinstance(stage_required, bool):
        errors.append(f"{stage_where}: required must be true or false")


def _check_production_stages(stages: object, *, where: str, errors: list[str]) -> None:
    if not isinstance(stages, dict):
        errors.append(f"{where}: stages must be a mapping")
        return
    stage_names = {str(key): value for key, value in stages.items()}
    unknown_stages = set(stage_names) - set(STAGES)
    if unknown_stages:
        errors.append(f"{where}: unknown stages {sorted(unknown_stages)} — known: {list(STAGES)}")
    for stage, policy in stage_names.items():
        if stage in STAGES:
            _check_production_stage(policy, stage_where=f"{where}.stages.{stage}", errors=errors)


def check_production_policy(value: object, *, where: str, errors: list[str]) -> None:
    """Validate one press- or series-scoped production policy mapping.

    Model IDs and effort labels intentionally remain open strings because the
    runtime owns their provider-specific vocabulary. The validator owns only
    the stable Nightly Build shape and semantic profile/stage names.
    """
    if not isinstance(value, dict):
        errors.append(f"{where}: must be a mapping")
        return
    policy = {str(key): item for key, item in value.items()}
    unknown = set(policy) - PRODUCTION_KEYS
    if unknown:
        errors.append(f"{where}: unknown keys {sorted(unknown)}")
    profile = policy.get("profile")
    if profile is not None and profile not in PROFILES:
        errors.append(f"{where}: profile must be one of {list(PROFILES)}")
    required = policy.get("required")
    if required is not None and not isinstance(required, bool):
        errors.append(f"{where}: required must be true or false")
    stages = policy.get("stages")
    if stages is not None:
        _check_production_stages(stages, where=where, errors=errors)


def check_production(repo: str | pathlib.Path, errors: list[str]) -> None:
    path = pathlib.Path(repo) / "press" / "production.yaml"
    if not path.is_file():
        return
    try:
        policy = load(path)
    except yaml.YAMLError as error:
        errors.append(f"press/production.yaml: not valid YAML ({error.__class__.__name__})")
        return
    check_production_policy(policy, where="press/production.yaml", errors=errors)


def _check_asset_item(item: object, *, where: str, errors: list[str]) -> None:
    if not isinstance(item, dict):
        errors.append(f"{where}: must be a mapping with 'url' and 'integrity'")
        return
    entry = {str(key): value for key, value in item.items()}
    extra = set(entry) - {"url", "integrity", "defer"}
    if extra:
        errors.append(f"{where}: unknown keys {sorted(extra)}")
    url = entry.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        errors.append(f"{where}: 'url' must be an https URL")
    integrity = entry.get("integrity")
    if not isinstance(integrity, str) or not re.match(r"^sha(256|384|512)-.+", integrity):
        errors.append(f"{where}: 'integrity' is required and must be an SRI hash (sha256-, sha384-, or sha512-...)")
    if "defer" in entry and not isinstance(entry.get("defer"), bool):
        errors.append(f"{where}: 'defer' must be true or false")


def check_site_assets(assets: object, *, errors: list[str]) -> None:
    if assets is None:
        return
    prefix = "press/site.yaml"
    if not isinstance(assets, dict):
        errors.append(f"{prefix}: 'assets' must be a mapping of scripts/styles")
        return
    assets_map = {str(key): value for key, value in assets.items()}
    unknown = set(assets_map) - {"scripts", "styles"}
    if unknown:
        errors.append(f"{prefix}: assets: unknown keys {sorted(unknown)}")
    for kind in ("scripts", "styles"):
        items = assets_map.get(kind)
        if items is None:
            continue
        if not isinstance(items, list):
            errors.append(f"{prefix}: assets.{kind} must be a list")
            continue
        for i, item in enumerate(items):
            _check_asset_item(item, where=f"{prefix}: assets.{kind}[{i}]", errors=errors)


def check_site_directory(directory: object, *, errors: list[str]) -> None:
    if directory is None:
        return
    prefix = "press/site.yaml"
    if not isinstance(directory, dict):
        errors.append(f"{prefix}: 'directory' must be a mapping of publish/description")
        return
    directory_map = {str(key): value for key, value in directory.items()}
    # Directory listing is opt-out (directory.publish: false). The public URL is
    # derived at build time from the Pages base URL, never configured, so a 'url'
    # key is intentionally rejected here by the unknown-key check.
    unknown = set(directory_map) - {"publish", "description"}
    if unknown:
        errors.append(f"{prefix}: directory: unknown keys {sorted(unknown)}")
    if not isinstance(directory_map.get("publish", False), bool):
        errors.append(f"{prefix}: directory.publish must be true or false")
    description = directory_map.get("description")
    if description is not None and (
        not isinstance(description, str)
        or not description.strip()
        or len(description.strip()) > MAX_DIRECTORY_DESCRIPTION_LEN
    ):
        errors.append(
            f"{prefix}: directory.description must be a non-empty string "
            f"of at most {MAX_DIRECTORY_DESCRIPTION_LEN} characters"
        )


def _check_banned_term_fields(entry: Mapping[str, object], *, where: str, partial: bool, errors: list[str]) -> None:
    terms = entry.get("terms")
    if ("terms" in entry or not partial) and not (
        isinstance(terms, list) and terms and all(isinstance(t, str) and t.strip() for t in terms)
    ):
        errors.append(f"{where}: 'terms' must be a non-empty string list")
    if ("max" in entry or not partial) and _as_count(entry.get("max")) is None:
        errors.append(f"{where}: 'max' must be an integer >= 0")
    note = entry.get("suggestion")
    if ("suggestion" in entry or not partial) and not (isinstance(note, str) and note.strip()):
        errors.append(
            f"{where}: 'suggestion' must be a non-empty string — it is "
            "the note the writer sees when the count runs over"
        )
    if not isinstance(entry.get("enabled", True), bool):
        errors.append(f"{where}: 'enabled' must be true or false")


def _check_banned_term_entry(
    raw_entry: object,
    *,
    rel: str,
    where: str,
    seen: set[str],
    engine_ids: set[str],
    is_press: bool,
    errors: list[str],
) -> None:
    if not isinstance(raw_entry, dict):
        errors.append(f"{where}: must be a mapping")
        return
    entry = {str(key): value for key, value in raw_entry.items()}
    unknown = set(entry) - BANNED_TERM_KEYS
    if unknown:
        errors.append(f"{where}: unknown keys {sorted(unknown)} — typo?")
    eid = entry.get("id")
    if not isinstance(eid, str) or not SLUG_RE.match(eid):
        errors.append(f"{where}: 'id' must be a short lowercase slug")
        return
    if eid in seen:
        errors.append(f"{rel}: duplicate id '{eid}'")
    seen.add(eid)
    _check_banned_term_fields(entry, where=where, partial=is_press and eid in engine_ids, errors=errors)


def check_banned_terms(repo: str | pathlib.Path, errors: list[str]) -> None:
    """Validate the engine's banned-terms list and the press's extension.

    The press file may carry partial entries: reusing an engine id overrides
    only the fields it states. A new id must arrive complete, so the proof
    always has strings to count and a suggestion to show the writer.
    """
    repo_path = pathlib.Path(repo)
    engine_ids: set[str] = set()
    for rel in ("spec/banned-terms.yaml", "press/banned-terms.yaml"):
        path = repo_path.joinpath(*rel.split("/"))
        if not path.is_file():
            continue
        entries = load(path)
        if entries is None:
            continue
        if not isinstance(entries, list):
            errors.append(f"{rel}: must be a list of entries")
            continue
        is_press = rel.startswith("press/")
        seen: set[str] = set()
        for n, entry in enumerate(entries, 1):
            _check_banned_term_entry(
                entry,
                rel=rel,
                where=f"{rel} entry #{n}",
                seen=seen,
                engine_ids=engine_ids,
                is_press=is_press,
                errors=errors,
            )
        if not is_press:
            engine_ids = seen


def _load_manifest(folder: str | pathlib.Path, *, name: str, errors: list[str]) -> tuple[bool, object]:
    try:
        return True, load(pathlib.Path(folder) / "manifest.yaml") or {}
    except yaml.YAMLError as e:
        errors.append(f"registry '{name}': manifest.yaml is not valid YAML: {e}")
        return False, None


def _check_registry_flex(
    entry: Mapping[str, object],
    *,
    bands: Mapping[str, object] | None,
    where: str,
    errors: list[str],
) -> list[str] | None:
    flex_components = entry.get("flex_components")
    if flex_components is None:
        return None
    valid = (
        isinstance(flex_components, list)
        and bool(flex_components)
        and all(isinstance(c, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", c) for c in flex_components)
        and len(flex_components) == len(set(flex_components))
    )
    if not valid:
        errors.append(f"{where}: 'flex_components' must be a non-empty list of unique CSS class names")
    if not (bands is not None and "flex_sections" in bands):
        errors.append(f"{where}: 'flex_components' requires 'bands.flex_sections'")
    return [str(c) for c in flex_components] if valid else None


def _check_skeleton_flex_components(
    skel: str,
    *,
    sections: Sequence[object],
    flex_components: Sequence[str],
    where: str,
    errors: list[str],
) -> None:
    parsed = check.Article()
    parsed.feed(skel)
    parsed.close()
    flexible_sections = [s for s in parsed.sections if s not in sections]
    if not flexible_sections:
        errors.append(f"{where}: skeleton.html has no flexible section in which to place 'flex_components'")
    for section in flexible_sections:
        counts = parsed.section_class_counts.get(section, {})
        for component in flex_components:
            count = counts.get(component, 0)
            if count != 1:
                errors.append(
                    f"{where}: skeleton flexible section {section!r} has "
                    f"{count} elements with class {component!r}; expected exactly one"
                )


def _check_registry_skeleton(
    folder: str | pathlib.Path,
    *,
    tid: str,
    entry: Mapping[str, object],
    sections: object,
    flex_components: list[str] | None,
    where: str,
    errors: list[str],
) -> None:
    skeleton = pathlib.Path(folder) / "skeleton.html"
    if not skeleton.is_file():
        errors.append(f"{where}: no skeleton.html in the {tid} template folder")
        return
    skel = skeleton.read_text(encoding="utf-8")
    if flex_components is not None and isinstance(sections, list):
        _check_skeleton_flex_components(
            skel, sections=sections, flex_components=flex_components, where=where, errors=errors
        )
    chrome = entry.get("chrome")
    if chrome is not None and not (isinstance(chrome, list) and all(isinstance(x, str) for x in chrome)):
        errors.append(f"{where}: 'chrome' must be a list of skeleton substrings")
    elif isinstance(chrome, list) and chrome:
        # Anchor each declared string to the skeleton it quotes: reworded
        # skeleton chrome would otherwise B-CHROME every future article
        # and land the blame on the writer instead of this manifest.
        errors.extend(
            f"{where}: chrome not found verbatim in skeleton.html: {piece!r}"
            for piece in chrome
            if isinstance(piece, str) and piece not in skel
        )


def _check_registry_sections(sections: object, *, where: str, errors: list[str]) -> None:
    if not isinstance(sections, list) or not sections:
        errors.append(f"{where}: 'sections' is required")
    elif not all(isinstance(section, str) and section for section in sections):
        errors.append(f"{where}: 'sections' must be a non-empty string list")
    elif "sources" not in sections:
        errors.append(f"{where}: sections must include 'sources'")


def _check_registry_entry(tid: str, raw_entry: object, *, folder: str | pathlib.Path, errors: list[str]) -> None:
    where = f"registry '{tid}'"
    if not isinstance(raw_entry, dict):
        errors.append(f"{where}: must be a mapping")
        return
    entry = {str(key): value for key, value in raw_entry.items()}
    unknown = set(entry) - TEMPLATE_KEYS
    if unknown:
        errors.append(f"{where}: unknown keys {sorted(unknown)}")
    if entry.get("class") not in ("longread", "shortread"):
        errors.append(f"{where}: class must be longread | shortread")
    sections = entry.get("sections")
    _check_registry_sections(sections, where=where, errors=errors)
    if entry.get("cite_rule") not in CITE_RULES:
        errors.append(f"{where}: cite_rule must be one of {sorted(CITE_RULES)}")
    bands = check_template_bands(
        entry.get("bands"),
        where=where,
        mapping_desc="geometry defaults",
        quote_key=True,
        errors=errors,
    )
    cite_exempt = entry.get("cite_exempt")
    if cite_exempt is not None and not (isinstance(cite_exempt, list) and all(isinstance(x, str) for x in cite_exempt)):
        errors.append(f"{where}: 'cite_exempt' must be a list of section names")
    flex_components = _check_registry_flex(entry, bands=bands, where=where, errors=errors)
    _check_registry_skeleton(
        folder,
        tid=tid,
        entry=entry,
        sections=sections,
        flex_components=flex_components,
        where=where,
        errors=errors,
    )


def check_registry(repo: str | pathlib.Path, errors: list[str]) -> dict[str, object]:
    registry: dict[str, object] = {}
    folders: dict[str, str | pathlib.Path] = {}
    for name, folder in build_site.template_dirs(str(repo)).items():
        ok, manifest = _load_manifest(folder, name=name, errors=errors)
        if ok:
            registry[name] = manifest
            folders[name] = folder
    if not registry:
        errors.append("no template packages found (templates/<id>/manifest.yaml)")
        return {}
    for tid, entry in registry.items():
        _check_registry_entry(tid, entry, folder=folders[tid], errors=errors)
    return registry


def check_required_docs(docs: object, root: str | pathlib.Path, *, sid: str, where: str, errors: list[str]) -> None:
    if docs is None:
        return
    if not isinstance(docs, list):
        errors.append(f"{where}: 'required_docs' must be a list")
        return
    root_path = pathlib.Path(root)
    for raw_doc in docs:
        if not isinstance(raw_doc, dict):
            errors.append(f"{where}: required_docs entry must be a mapping with 'id' and 'path'")
            continue
        doc = {str(key): value for key, value in raw_doc.items()}
        doc_id, doc_path = doc.get("id"), doc.get("path")
        if not isinstance(doc_id, str) or not doc_id.strip():
            errors.append(f"{where}: required_doc id must be a non-empty string")
        if not isinstance(doc_path, str) or not doc_path:
            errors.append(f"{where}: required_doc path must be a non-empty string")
            continue
        if not doc.get("id") or not (root_path / sid / doc_path).is_file():
            errors.append(f"{where}: required_doc {doc.get('id')!r} file not found: {doc.get('path')!r}")


def _check_one_kind_band(band: object, *, label: str, errors: list[str]) -> None:
    if not isinstance(band, list) or len(band) != BAND_LEN:
        errors.append(f"{label} must be [low, high]")
        return
    low = _as_count(band[0])
    if low is None:
        errors.append(f"{label} low must be an integer >= 0")
        return
    raw_high = band[1]
    if raw_high is not None:
        high = _as_count(raw_high)
        if high is None or high < low:
            errors.append(f"{label} high must be null (no upper bound) or an integer >= the low")


def check_kind_bands(bands: object, *, key: str, where: str, errors: list[str]) -> None:
    if bands is None:
        return
    if not isinstance(bands, dict) or not bands:
        errors.append(f"{where}: '{key}' must be a mapping of source kind to [low, high], e.g. primary: [1, 1]")
        return
    bands_map = {str(k): v for k, v in bands.items()}
    unknown = sorted(set(bands_map) - SOURCE_KINDS)
    if unknown:
        errors.append(f"{where}: {key}: unknown source kind(s) {unknown} (the kinds are {sorted(SOURCE_KINDS)})")
    for kind in sorted(set(bands_map) & SOURCE_KINDS):
        _check_one_kind_band(bands_map[kind], label=f"{where}: {key}.{kind}", errors=errors)


def check_template_bands(
    bands: object,
    *,
    where: str,
    errors: list[str],
    mapping_desc: str = "geometry bands",
    quote_key: bool = False,
) -> dict[str, object] | None:
    """Validate series geometry policy without requiring template defaults.

    The series layer is allowed to introduce a band that a template omitted;
    omission means that the template has no recommendation, not that the
    series is forbidden from setting an explicit policy. Every supplied band
    must still be one of the three engine-understood count ranges.
    """
    if bands is None:
        return None
    if not isinstance(bands, dict):
        errors.append(f"{where}: 'bands' must be a mapping of {mapping_desc}")
        return None
    bands_map = {str(key): value for key, value in bands.items()}
    unknown_bands = sorted(set(bands_map) - set(TEMPLATE_BAND_KEYS))
    if unknown_bands:
        errors.append(f"{where}: bands has unknown keys {unknown_bands} (known: {sorted(TEMPLATE_BAND_KEYS)})")
    for band_key in sorted(set(bands_map) & set(TEMPLATE_BAND_KEYS)):
        band = bands_map[band_key]
        low = _as_count(band[0]) if isinstance(band, list) and len(band) == BAND_LEN else None
        high = _as_count(band[1]) if isinstance(band, list) and len(band) == BAND_LEN else None
        if low is None or high is None or low > high:
            label = f"'bands.{band_key}'" if quote_key else f"bands.{band_key}"
            errors.append(f"{where}: {label} must be [low, high] non-negative integers with low <= high")
    return bands_map


def check_kinded_skeletons(
    repo: str | pathlib.Path, templates: Sequence[str], *, where: str, errors: list[str]
) -> None:
    """Check that templates used by a composition rule declare data-nb-kind.

    A skeleton whose sources carry no `data-nb-kind` renders an article the
    writer fills faithfully and the proof then blocks for "0 primary source(s)".
    Report it while the author is configuring the template instead.
    """
    for tid, folder in build_site.template_dirs(str(repo)).items():
        skeleton = pathlib.Path(folder) / "skeleton.html"
        if tid not in templates or not skeleton.is_file():
            continue
        ed = check.Article()
        ed.feed(skeleton.read_text(encoding="utf-8"))
        ed.close()
        if any(s["kind"] is None for s in ed.sources):
            errors.append(
                f"{where}: a source composition needs a template whose skeleton "
                f"declares data-nb-kind on its source entries; '{tid}' does not"
            )


def _check_rubric_criterion(raw_criterion: object, *, spot: str, seen: set[str], errors: list[str]) -> None:
    if not isinstance(raw_criterion, dict):
        errors.append(f"{spot} must be a mapping with id and name")
        return
    criterion = {str(key): value for key, value in raw_criterion.items()}
    unknown = set(criterion) - RUBRIC_KEYS
    if unknown:
        errors.append(f"{spot}: unknown keys {sorted(unknown)} (known: {sorted(RUBRIC_KEYS)})")
    cid = criterion.get("id")
    if not isinstance(cid, str) or not SLUG_RE.match(cid):
        errors.append(f"{spot}: 'id' must match {SLUG_RE.pattern}")
    elif cid in seen:
        errors.append(f"{spot}: duplicate id '{cid}'")
    else:
        seen.add(cid)
    name = criterion.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{spot}: 'name' must be a non-empty string")
    note = criterion.get("note")
    if note is not None and (not isinstance(note, str) or not note.strip()):
        errors.append(f"{spot}: 'note' must be a non-empty string when present")


def check_rubric_config(rubric: object, *, where: str, errors: list[str]) -> None:
    """Validate a pinned rubric that the proof holds every review to.

    Each criterion is {id, name, note?}: the id is the slug rows carry in
    data-nb-criterion, the name is what the reader sees, and the optional
    note briefs the writer. Ids must be unique — the proof matches rows to
    pinned criteria by id, and a duplicate makes that match ambiguous.
    """
    if rubric is None:
        return
    if not isinstance(rubric, list) or not rubric:
        errors.append(f"{where}: 'rubric' must be a non-empty list of criteria")
        return
    seen: set[str] = set()
    for i, criterion in enumerate(rubric):
        _check_rubric_criterion(criterion, spot=f"{where}: rubric criterion #{i + 1}", seen=seen, errors=errors)


def _load_series_yaml(path: pathlib.Path, *, where: str, errors: list[str]) -> dict[str, object] | None:
    if not path.is_file():
        errors.append(f"{where}: series.yaml is missing")
        return None
    try:
        cfg = load(path) or {}
    except yaml.YAMLError as e:
        errors.append(f"{where}: series.yaml is not valid YAML ({e.__class__.__name__})")
        return None
    if not isinstance(cfg, dict):
        errors.append(f"{where}: series.yaml must be a mapping")
        return None
    return {str(key): value for key, value in cfg.items()}


def _check_series_header(cfg: Mapping[str, object], *, where: str, errors: list[str]) -> None:
    if "autopublish" in cfg:
        errors.append(
            f"{where}: 'autopublish' was removed; every valid new article "
            "now publishes automatically. Report this to the paper owner "
            "and delete the key to acknowledge the new behavior"
        )
    unknown = set(cfg) - SERIES_KEYS - {"autopublish"}
    if unknown:
        errors.append(f"{where}: unknown keys {sorted(unknown)} — typo? (known: {sorted(SERIES_KEYS)})")
    name = cfg.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{where}: 'name' must be a non-empty string")
    if cfg.get("mode") not in MODES:
        errors.append(f"{where}: mode must be one of {sorted(MODES)}")
    cadence = cfg.get("cadence")
    if cadence is not None and not duty.cadence_is_valid(cadence):
        errors.append(
            f"{where}: cadence must be daily | weekdays | weekends | "
            f"manual | a list of day names {list(duty.DAY_NAMES)}"
        )


def _check_series_flags(cfg: Mapping[str, object], *, where: str, errors: list[str]) -> None:
    errors.extend(
        f"{where}: '{flag}' must be true or false"
        for flag in ("paused", "strict")
        if not isinstance(cfg.get(flag, False), bool)
    )
    production = cfg.get("production")
    if production is not None:
        check_production_policy(production, where=f"{where}/series.yaml: production", errors=errors)
    min_sources = cfg.get("min_sources")
    if min_sources is not None and _as_count(min_sources) is None:
        errors.append(f"{where}: 'min_sources' must be an integer >= 0")
    section = cfg.get("section")
    if section is not None and (not isinstance(section, str) or not section.strip()):
        errors.append(f"{where}: 'section' must be a non-empty string")


def _check_series_selection(cfg: Mapping[str, object], *, where: str, errors: list[str]) -> None:
    selection = cfg.get("selection")
    if selection is None:
        return
    if selection not in SELECTIONS:
        errors.append(f"{where}: selection must be one of {sorted(SELECTIONS)}")
    elif cfg.get("mode") != "collection":
        errors.append(f"{where}: 'selection' only applies to collection mode")


def _check_series_template_choices(cfg: Mapping[str, object], *, where: str, errors: list[str]) -> list[str]:
    template = cfg.get("template")
    if template is not None and not isinstance(template, str):
        errors.append(f"{where}: 'template' must be a template ID string")
    templates = cfg.get("templates")
    if templates is not None and (not isinstance(templates, list) or not templates):
        errors.append(f"{where}: 'templates' must be a non-empty list")
        templates = None
    elif templates is not None and not all(isinstance(c, str) and c for c in templates):
        errors.append(f"{where}: 'templates' must contain template ID strings")
        templates = None
    if templates and template:
        errors.append(f"{where}: use 'template' or 'templates', not both")
    allowed = template_choices(cfg)
    if not allowed:
        errors.append(f"{where}: requires 'template' or a non-empty 'templates' choice list")
    return allowed


def _check_series_templates(
    cfg: Mapping[str, object],
    *,
    repo: pathlib.Path,
    registry: Mapping[str, object],
    where: str,
    errors: list[str],
) -> None:
    allowed = _check_series_template_choices(cfg, where=where, errors=errors)
    check_template_bands(cfg.get("bands"), where=where, errors=errors)
    tregs: list[dict[str, object]] = []
    for template in allowed:
        treg = registry.get(template)
        if isinstance(treg, dict):
            tregs.append({str(k): v for k, v in treg.items()})
        elif (repo / "examples" / "templates" / template).is_dir():
            errors.append(
                f"{where}: template '{template}' is an example package;"
                f" copy examples/templates/{template} to press/templates/{template}"
            )
        else:
            errors.append(f"{where}: template '{template}' not a known template")
    check_kind_bands(cfg.get("sources_by_kind"), key="sources_by_kind", where=where, errors=errors)
    per_item_sources = cfg.get("per_item_sources")
    check_kind_bands(per_item_sources, key="per_item_sources", where=where, errors=errors)
    # per_item_sources constrains what each data-nb-item cites, which only a
    # per-item template has. EVERY template the series may use must cite per
    # item: a rule the night's template choice can dodge is not a rule.
    per_section = [
        t for t in allowed if isinstance(entry := registry.get(t), dict) and entry.get("cite_rule") != "per-item"
    ]
    if per_item_sources is not None and tregs and per_section:
        errors.append(
            f"{where}: 'per_item_sources' needs every template the series may "
            f"use to cite per item; {', '.join(per_section)} cite(s) per section"
        )
    if per_item_sources is not None or cfg.get("sources_by_kind") is not None:
        check_kinded_skeletons(repo, allowed, where=where, errors=errors)
    check_rubric_config(cfg.get("rubric"), where=where, errors=errors)


def _check_series_paths(cfg: Mapping[str, object], *, series_dir: pathlib.Path, where: str, errors: list[str]) -> None:
    # A pinned voice guide stands in for the writing coach, so a broken path
    # would silently cost the series the voice it had settled on rather than fail.
    for field, label in (("prompt", "prompt file"), ("voice_guide", "voice guide file")):
        rel = cfg.get(field)
        if rel is not None and not isinstance(rel, str):
            errors.append(f"{where}: '{field}' must be a path string")
        elif rel and not (series_dir / rel).is_file():
            errors.append(f"{where}: {label} '{rel}' not found")


def _check_series_tags(tags: object, *, series_dir: pathlib.Path, where: str, errors: list[str]) -> None:
    if tags is None:
        return
    if not isinstance(tags, dict):
        errors.append(f"{where}: 'tags' must be a mapping of tag to fragment path")
        return
    for tag, frag in tags.items():
        if not isinstance(tag, str) or not nb_meta.is_safe_tag(tag):
            errors.append(f"{where}: tag fragment name {tag!r} must match {nb_meta.TAG_RE.pattern}")
        elif not isinstance(frag, str) or not frag:
            errors.append(f"{where}: tag '{tag}' fragment path must be a string")
        elif not (series_dir / frag).is_file():
            errors.append(f"{where}: tag '{tag}' fragment '{frag}' not found")


def _check_series_items(
    cfg: Mapping[str, object],
    *,
    root: pathlib.Path,
    sid: str,
    where: str,
    errors: list[str],
) -> list[dict[str, object]]:
    mode = cfg.get("mode")
    raw_items = cfg.get("items")
    if raw_items is not None and not isinstance(raw_items, list):
        errors.append(f"{where}: 'items' must be a list")
        items: list[object] = []
    else:
        items = raw_items or []
    if mode in ("collection", "sequence") and not items:
        errors.append(f"{where}: {mode} mode requires 'items'")
    if mode == "rolling" and items:
        errors.append(f"{where}: rolling mode must not define 'items'")
    seen: set[str] = set()
    valid_items: list[dict[str, object]] = []
    for i, raw_item in enumerate(items):
        if not isinstance(raw_item, dict):
            errors.append(f"{where}: item #{i + 1} must be a mapping")
            continue
        item = {str(key): value for key, value in raw_item.items()}
        valid_items.append(item)
        slug = item.get("slug")
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            errors.append(f"{where}: item #{i + 1} slug {slug!r} must match {SLUG_RE.pattern}")
        else:
            if slug in seen:
                errors.append(f"{where}: duplicate item slug '{slug}'")
            seen.add(slug)  # only valid slugs seed the duplicate check
        check_required_docs(item.get("required_docs"), root, sid=sid, where=where, errors=errors)
    return valid_items


def _collect_item_consult(items: Sequence[Mapping[str, object]], *, where: str, errors: list[str]) -> list[object]:
    item_consult: list[object] = []
    for item in items:
        item_values = item.get("consult")
        if item_values is None:
            continue
        if not isinstance(item_values, list):
            errors.append(f"{where}: item consult must be a list of https:// prefixes")
            continue
        item_consult.extend(item_values)
    return item_consult


def _check_series_consult(
    cfg: Mapping[str, object],
    *,
    items: Sequence[Mapping[str, object]],
    where: str,
    errors: list[str],
) -> None:
    consult = cfg.get("consult")
    if consult is not None and not isinstance(consult, list):
        errors.append(f"{where}: 'consult' must be a list of https:// prefixes")
        consult = []
    item_consult = _collect_item_consult(items, where=where, errors=errors)
    errors.extend(
        f"{where}: consult entries must be https:// prefixes, got {prefix!r}"
        for prefix in (consult or []) + item_consult
        if not str(prefix).startswith("https://")
    )
    exclusive = cfg.get("sources_exclusive", False)
    if not isinstance(exclusive, bool):
        errors.append(f"{where}: sources_exclusive must be true or false")
    elif exclusive:
        has_docs = cfg.get("required_docs") or any(item.get("required_docs") for item in items)
        if not (consult or item_consult or has_docs):
            errors.append(f"{where}: sources_exclusive requires declared sources (consult and/or required_docs)")


def check_series(repo: str | pathlib.Path, registry: Mapping[str, object], *, errors: list[str]) -> None:
    label = "press"
    repo_path = pathlib.Path(repo)
    root = repo_path / "press" / "series"
    if not root.is_dir():
        return
    for series_dir in sorted(root.iterdir(), key=lambda entry: entry.name):
        sid = series_dir.name
        if sid.startswith("_") or not series_dir.is_dir():
            continue
        where = f"{label}/series/{sid}"
        if not SERIES_ID_RE.match(sid):
            errors.append(f"{where}: id must match {SERIES_ID_RE.pattern}")
        cfg = _load_series_yaml(series_dir / "series.yaml", where=where, errors=errors)
        if cfg is None:
            continue
        _check_series_header(cfg, where=where, errors=errors)
        _check_series_flags(cfg, where=where, errors=errors)
        _check_series_selection(cfg, where=where, errors=errors)
        _check_series_templates(cfg, repo=repo_path, registry=registry, where=where, errors=errors)
        _check_series_paths(cfg, series_dir=series_dir, where=where, errors=errors)
        _check_series_tags(cfg.get("tags"), series_dir=series_dir, where=where, errors=errors)
        items = _check_series_items(cfg, root=root, sid=sid, where=where, errors=errors)
        check_required_docs(cfg.get("required_docs"), root, sid=sid, where=where, errors=errors)
        _check_series_consult(cfg, items=items, where=where, errors=errors)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate Nightly Build configuration")
    p.add_argument("--repo", default=".", help="repo root (main checkout)")
    args = p.parse_args(argv)

    errors: list[str] = []
    check_site(args.repo, errors)
    check_production(args.repo, errors)
    check_banned_terms(args.repo, errors)
    registry = check_registry(args.repo, errors)
    check_series(args.repo, registry, errors=errors)

    if errors:
        sys.stdout.write(f"configuration INVALID — {len(errors)} problem(s):\n")
        for e in errors:
            sys.stdout.write(f"  ✗ {e}\n")
        return 1
    sys.stdout.write(
        "configuration valid: site.yaml, production policy, banned terms, registry, and all series check out\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
