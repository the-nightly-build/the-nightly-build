"""Parse article metadata and bind it to the configured series contract.

The metadata block is intentionally a small, explicit boundary between an
article and the engine. This module validates its primitive fields, resolves a
series' allowed template choices, and applies only the series-owned policy
bands after one template has been selected.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import TYPE_CHECKING

import yaml

from nb import meta as nb_meta
from nb.article import collapse_space
from nb.config import apply_template_bands, load_registry, load_series, template_choices

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from nb.article import Article
    from nb.report import Report

PROTOCOL_MAJOR = "1"
MAX_BYTES = 2 * 1024 * 1024
SLUG_RE = nb_meta.SLUG_RE
SERIES_RE = nb_meta.SERIES_RE
TAG_RE = nb_meta.TAG_RE
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

__all__ = (
    "bind_template",
    "check_meta_agreement",
    "parse_meta",
    "read_article_source",
    "resolve_series_and_template",
    "validate_meta_fields",
)

_META_TYPE_NAMES: dict[type, str] = {
    str: "a string",
    int: "an integer",
    list: "a list",
    bool: "true or false",
}


def _need_meta_field(
    meta: Mapping[str, object],
    field: str,
    *,
    typ: type,
    rep: Report,
    pattern: str | None = None,
    enum: Sequence[str] | None = None,
) -> object:
    v = meta.get(field)
    if v is None:
        rep.block("B-META-PARSE", f"nb-meta missing required field '{field}'")
        return None
    if not isinstance(v, typ):
        rep.block(
            "B-META-PARSE",
            f"nb-meta field '{field}' must be {_META_TYPE_NAMES.get(typ, 'the right type')}",
        )
        return None
    if pattern and not re.match(pattern, str(v)):
        rep.block("B-META-PARSE", f"nb-meta field '{field}' fails pattern {pattern}")
    if enum and v not in enum:
        rep.block("B-META-PARSE", f"nb-meta field '{field}' must be one of {enum}")
    return v


def _validate_meta_tags(tags: object, rep: Report) -> None:
    if tags is None:
        return
    if not isinstance(tags, list):
        rep.block("B-META-PARSE", "nb-meta field 'tags' must be a list")
        return
    for tag in tags:
        if not isinstance(tag, str) or not nb_meta.is_safe_tag(tag):
            rep.block(
                "B-META-PARSE",
                f"nb-meta tag {tag!r} must match {TAG_RE.pattern} (lowercase slug: a-z, 0-9, hyphen)",
            )


def validate_meta_fields(meta: Mapping[str, object], rep: Report) -> None:
    _need_meta_field(meta, "protocol", typ=str, rep=rep)
    protocol = meta.get("protocol")
    if isinstance(protocol, str) and protocol.split(".")[0] != PROTOCOL_MAJOR:
        rep.block(
            "B-META-PARSE",
            f"protocol major must be {PROTOCOL_MAJOR}, got {protocol}",
        )
    _need_meta_field(meta, "series", typ=str, rep=rep, pattern=SERIES_RE.pattern)
    _need_meta_field(meta, "slug", typ=str, rep=rep, pattern=SLUG_RE.pattern)
    # template membership is validated against the merged registry (B-SERIES /
    # B-META-MATCH) — user templates in press/templates/ are first-class
    _need_meta_field(meta, "template", typ=str, rep=rep)
    _need_meta_field(meta, "title", typ=str, rep=rep)
    _need_meta_field(meta, "mode", typ=str, rep=rep, enum=list(nb_meta.MODES))
    _need_meta_field(meta, "date", typ=str, rep=rep, pattern=DATE_RE.pattern)
    _need_meta_field(meta, "dek", typ=str, rep=rep)
    _need_meta_field(meta, "sources", typ=int, rep=rep)
    _need_meta_field(meta, "harness", typ=str, rep=rep)
    _need_meta_field(meta, "model", typ=str, rep=rep)
    order = meta.get("order")
    if order is not None and (not isinstance(order, int) or order < 1):
        rep.block("B-META-PARSE", "nb-meta 'order' must be a positive integer or null")
    _validate_meta_tags(meta.get("tags"), rep)


def resolve_series_and_template(
    repo: str | pathlib.Path,
    series_id: str,
    *,
    rep: Report,
    allow_paused: bool = False,
) -> tuple[dict[str, object], dict[str, object], list[str]] | None:
    """B-SERIES: load the series config and resolve its template choices.

    Returns ``(series, registry, allowed_templates)`` or None when a blocking
    failure means the check cannot continue. The manifest is bound only after
    article metadata names one choice from the series' list, regardless of
    scheduling mode.
    """
    raw_series, spath = load_series(repo, series_id)
    if raw_series is None:
        rep.block("B-SERIES", f"series '{series_id}' not found at {spath}")
        return None
    if not isinstance(raw_series, dict):
        rep.block("B-SERIES", f"series '{series_id}' config must be a mapping")
        return None
    series = {str(key): value for key, value in raw_series.items()}
    if series.get("paused") and not allow_paused:
        rep.block(
            "B-SERIES",
            f"series '{series_id}' is paused — remove 'paused: true' from series.yaml to publish",
        )
    try:
        registry = load_registry(repo)
    except (OSError, yaml.YAMLError, TypeError, ValueError) as e:
        rep.block("B-SERIES", f"template manifests unreadable: {e}")
        return None

    allowed_templates = template_choices(series)
    unknown = [t for t in allowed_templates if not isinstance(registry.get(t), dict)]
    if not allowed_templates or unknown:
        rep.block(
            "B-SERIES",
            f"series templates {unknown or 'missing'} are not known templates",
        )
        return None
    return series, registry, allowed_templates


def read_article_source(html_path: str | pathlib.Path, rep: Report) -> str | None:
    path = pathlib.Path(html_path)
    if not path.is_file():
        rep.block("B-HTML", f"file not found: {html_path}")
        return None
    size = path.stat().st_size
    if size > MAX_BYTES:
        rep.block("B-HTML", f"file is {size} bytes; limit is {MAX_BYTES}")
    return path.read_text(encoding="utf-8", errors="replace")


def parse_meta(ed: Article, rep: Report) -> dict[str, object] | None:
    if not ed.meta_raw:
        rep.block("B-META-PARSE", 'no <script type="application/json" id="nb-meta"> block')
        return None
    if ed.meta_count > 1:
        # The browser + build read the first #nb-meta; validating a second one
        # would let the proof approve metadata that never ships. One only.
        rep.block("B-META-PARSE", f"exactly one #nb-meta block allowed, found {ed.meta_count}")
        return None
    try:
        meta = json.loads(ed.meta_raw)
    except ValueError as e:
        rep.block("B-META-PARSE", f"nb-meta JSON invalid: {e}")
        return None
    if not isinstance(meta, dict):
        rep.block("B-META-PARSE", "nb-meta JSON invalid: nb-meta must be a JSON object")
        return None
    meta_dict = {str(key): value for key, value in meta.items()}
    validate_meta_fields(meta_dict, rep)
    return meta_dict


def bind_template(
    meta: Mapping[str, object],
    registry: Mapping[str, object] | None,
    *,
    allowed_templates: Sequence[str],
    series: Mapping[str, object],
    rep: Report,
) -> tuple[str, dict[str, object]] | None:
    template_id = meta.get("template")
    treg = (registry or {}).get(template_id) if isinstance(template_id, str) else None
    if not isinstance(template_id, str) or not isinstance(treg, dict):
        rep.block(
            "B-META-MATCH",
            f"nb-meta template '{template_id}' is not a known template",
        )
        return None
    if template_id not in allowed_templates:
        rep.block(
            "B-META-MATCH",
            f"nb-meta template '{template_id}' is not one of the series' allowed templates {allowed_templates}",
        )
    treg_dict = {str(key): value for key, value in treg.items()}
    return template_id, apply_template_bands(treg_dict, series=series)


def check_meta_agreement(
    meta: Mapping[str, object],
    *,
    series: Mapping[str, object],
    series_id: str,
    template_id: str,
    slug_from_path: str,
    parent: str,
    dekline: str,
    rep: Report,
) -> None:
    if meta.get("slug") != slug_from_path:
        rep.block(
            "B-META-MATCH",
            f"path slug '{slug_from_path}' != nb-meta slug '{meta.get('slug')}'",
        )
    if parent and parent != series_id:
        rep.block("B-META-MATCH", f"file sits under '{parent}/' but series is '{series_id}'")
    if meta.get("series") != series_id:
        rep.block(
            "B-META-MATCH",
            f"nb-meta series '{meta.get('series')}' != declared series '{series_id}'",
        )
    if meta.get("mode") != series.get("mode"):
        rep.block(
            "B-META-MATCH",
            f"nb-meta mode '{meta.get('mode')}' != series mode '{series.get('mode')}'",
        )
    if meta.get("template") != template_id:
        rep.block(
            "B-META-MATCH",
            f"nb-meta template '{meta.get('template')}' is not the selected series template '{template_id}'",
        )
    # The index card and the RSS summary are built from nb-meta's dek, so an
    # article whose body was fixed and whose meta was not ships the abandoned dek
    # on the front page and the feed. Nothing to compare against is nothing to say.
    dek = collapse_space(str(meta.get("dek", "")))
    if dekline and dek != dekline:
        rep.block(
            "B-META-MATCH",
            f"nb-meta dek {dek!r} != the rendered dekline {dekline!r}",
            suggestion="the front page and the feed render nb-meta's dek, not "
            "the body's; carry every dek edit back into nb-meta",
        )
