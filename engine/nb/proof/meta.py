"""nb-meta: reading it, typing it, and holding it to the series and the body."""

import json
import os
import re

import yaml

from nb import meta as nb_meta
from nb.article import collapse_space
from nb.config import load_registry, load_series

PROTOCOL_MAJOR = "1"
MAX_BYTES = 2 * 1024 * 1024
SLUG_RE = nb_meta.SLUG_RE
SERIES_RE = nb_meta.SERIES_RE
TAG_RE = re.compile(r"^[a-z0-9-]{1,32}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_META_TYPE_NAMES = {
    str: "a string",
    int: "an integer",
    list: "a list",
    bool: "true or false",
}


def validate_meta_fields(meta, rep):
    def need(field, typ, *, pattern=None, enum=None):
        v = meta.get(field)
        if v is None:
            rep.block("B-META-PARSE", f"nb-meta missing required field '{field}'")
            return None
        if typ and not isinstance(v, typ):
            rep.block(
                "B-META-PARSE",
                f"nb-meta field '{field}' must be {_META_TYPE_NAMES.get(typ, 'the right type')}",
            )
            return None
        if pattern and not re.match(pattern, str(v)):
            rep.block(
                "B-META-PARSE", f"nb-meta field '{field}' fails pattern {pattern}"
            )
        if enum and v not in enum:
            rep.block("B-META-PARSE", f"nb-meta field '{field}' must be one of {enum}")
        return v

    need("protocol", str)
    if (
        isinstance(meta.get("protocol"), str)
        and meta["protocol"].split(".")[0] != PROTOCOL_MAJOR
    ):
        rep.block(
            "B-META-PARSE",
            f"protocol major must be {PROTOCOL_MAJOR}, got {meta.get('protocol')}",
        )
    need("series", str, pattern=SERIES_RE.pattern)
    need("slug", str, pattern=SLUG_RE.pattern)
    # template membership is validated against the merged registry (B-SERIES /
    # B-META-MATCH) — user templates in press/templates/ are first-class
    need("template", str)
    need("title", str)
    need("mode", str, enum=list(nb_meta.MODES))
    need("date", str, pattern=DATE_RE.pattern)
    need("dek", str)
    need("sources", int)
    need("harness", str)
    need("model", str)
    order = meta.get("order")
    if order is not None and (not isinstance(order, int) or order < 1):
        rep.block("B-META-PARSE", "nb-meta 'order' must be a positive integer or null")
    tags = meta.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            rep.block("B-META-PARSE", "nb-meta field 'tags' must be a list")
        else:
            for tag in tags:
                if not isinstance(tag, str) or not TAG_RE.match(tag):
                    rep.block(
                        "B-META-PARSE",
                        f"nb-meta tag {tag!r} must match {TAG_RE.pattern} "
                        "(lowercase slug: a-z, 0-9, hyphen)",
                    )


def resolve_series_and_template(repo, series_id, rep):
    """B-SERIES: load the series config and resolve its template band.

    Returns (series, registry, mode_cfg, template_id, treg, allowed_templates),
    or None when a blocking failure means the check cannot continue. For an
    open series template_id/treg are placeholders bound from nb-meta later and
    allowed_templates is the per-article choice list; off open it is None.
    """
    series, spath = load_series(repo, series_id)
    if series is None:
        rep.block("B-SERIES", f"series '{series_id}' not found at {spath}")
        return None
    if series.get("paused"):
        rep.block(
            "B-SERIES",
            f"series '{series_id}' is paused — remove "
            f"'paused: true' from series.yaml to publish",
        )
    try:
        registry = load_registry(repo)
    except (OSError, yaml.YAMLError, TypeError, ValueError) as e:
        rep.block("B-SERIES", f"template manifests unreadable: {e}")
        return None

    mode_cfg = series.get("mode")
    if mode_cfg == "open":
        # open series pick a template per article; nb-meta names the choice,
        # resolved after the meta block parses
        allowed_templates = series.get("templates") or (
            [series["template"]] if series.get("template") else []
        )
        unknown = [t for t in allowed_templates if t not in (registry or {})]
        if not allowed_templates or unknown:
            rep.block(
                "B-SERIES",
                f"open series templates {unknown or 'missing'} are not known templates",
            )
            return None
        for t in allowed_templates:
            if "open" not in (registry[t].get("modes") or []):
                rep.block(
                    "B-SERIES",
                    f"mode 'open' not allowed for template '{t}' "
                    f"(allowed: {registry[t].get('modes')})",
                )
        # placeholder registry entry; the real one is bound from nb-meta
        # right after it parses (or the check returns early)
        return series, registry, mode_cfg, None, {}, allowed_templates

    template_id = series.get("template")
    treg = (registry or {}).get(template_id)
    if not treg:
        rep.block(
            "B-SERIES",
            f"series template '{template_id}' is not a known template",
        )
        return None
    if mode_cfg not in (treg.get("modes") or []):
        rep.block(
            "B-SERIES",
            f"series mode '{mode_cfg}' not allowed for template "
            f"'{template_id}' (allowed: {treg.get('modes')})",
        )
    return series, registry, mode_cfg, template_id, treg, None


def read_article_source(html_path, rep):
    if not os.path.isfile(html_path):
        rep.block("B-HTML", f"file not found: {html_path}")
        return None
    size = os.path.getsize(html_path)
    if size > MAX_BYTES:
        rep.block("B-HTML", f"file is {size} bytes; limit is {MAX_BYTES}")
    with open(html_path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def parse_meta(ed, rep):
    if not ed.meta_raw:
        rep.block(
            "B-META-PARSE", 'no <script type="application/json" id="nb-meta"> block'
        )
        return None
    if ed.meta_count > 1:
        # The browser + build read the first #nb-meta; validating a second one
        # would let the proof approve metadata that never ships. One only.
        rep.block(
            "B-META-PARSE", f"exactly one #nb-meta block allowed, found {ed.meta_count}"
        )
        return None
    try:
        meta = json.loads(ed.meta_raw)
        if not isinstance(meta, dict):
            raise ValueError("nb-meta must be a JSON object")
    except ValueError as e:
        rep.block("B-META-PARSE", f"nb-meta JSON invalid: {e}")
        return None
    validate_meta_fields(meta, rep)
    return meta


def bind_open_template(meta, registry, allowed_templates, rep):
    template_id = meta.get("template")
    treg = (registry or {}).get(template_id)
    if treg is None:
        rep.block(
            "B-META-MATCH",
            f"nb-meta template '{template_id}' is not a known template",
        )
        return None
    if template_id not in allowed_templates:
        rep.block(
            "B-META-MATCH",
            f"nb-meta template '{template_id}' is not one of the "
            f"series' allowed templates {allowed_templates}",
        )
    return template_id, treg


def check_meta_agreement(
    meta,
    *,
    series,
    series_id,
    template_id,
    slug_from_path,
    parent,
    dekline,
    pr_body_meta,
    rep,
):
    if meta.get("slug") != slug_from_path:
        rep.block(
            "B-META-MATCH",
            f"path slug '{slug_from_path}' != nb-meta slug '{meta.get('slug')}'",
        )
    if parent and parent != series_id:
        rep.block(
            "B-META-MATCH", f"file sits under '{parent}/' but series is '{series_id}'"
        )
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
            f"nb-meta template '{meta.get('template')}' != series template '{template_id}'",
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
    if pr_body_meta is not None:
        for field in ("series", "slug", "mode", "template", "date", "title"):
            if field in pr_body_meta and pr_body_meta.get(field) != meta.get(field):
                rep.block(
                    "B-META-MATCH",
                    f"PR body '{field}'={pr_body_meta.get(field)!r} disagrees "
                    f"with embedded nb-meta {meta.get(field)!r}",
                )
        b_order = pr_body_meta.get("order", meta.get("order"))
        if b_order != meta.get("order"):
            rep.block("B-META-MATCH", "PR body 'order' disagrees with embedded nb-meta")
