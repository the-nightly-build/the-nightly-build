#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Validate an article against the protocol and series config: the proof.

Findings come in two tiers. BLOCK findings are integrity failures and CI
refuses to publish on any of them. WARN findings are quality calibration:
agents treat them as revision notes and they block only when a series sets
strict true. The same tool runs in the agent loop, in press checks, and in
CI, which keeps the publishing bar identical everywhere.

Invocations:

    Agent loop / press check:
        python3 engine/check.py library/<series>/<slug>.html --series <id> --repo . [--library DIR]
    CI (PR mode):
        python3 engine/check.py --pr --repo . --main <main checkout> \
            --base <ref> --head <ref> [--pr-body FILE] [--library DIR]

In PR mode --repo is the PR checkout, used for the diff and the article
file. Configs and templates load from --main because the orphan library
branch carries no engine.
"""

import argparse
import concurrent.futures
import datetime as _dt
import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Literal

import nb_meta

try:
    import yaml
except ImportError:
    sys.stderr.write("check.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

PROTOCOL_MAJOR = "1"
MAX_BYTES = 2 * 1024 * 1024
SLUG_RE = re.compile(r"^[a-z0-9-]{1,64}$")
SERIES_RE = re.compile(r"^[a-z0-9-]{1,32}$")
TAG_RE = re.compile(r"^[a-z0-9-]{1,32}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Off-origin references (link/img) may load only from Google Fonts over https.
# Matched by exact host after browser-style normalization, never by string
# prefix — "fonts.googleapis.com.evil.example" and userinfo tricks defeat prefix
# matching but not a real host comparison.
ALLOWED_EXTERNAL_HOSTS = frozenset({"fonts.googleapis.com", "fonts.gstatic.com"})
# The one executable script an article may load: the engine-owned runtime
# (§7.4 — contextual nav + chart renderer), by relative or root-absolute path.
ENGINE_SCRIPT_RE = re.compile(r"^(?:(?:\.\./)+|/)assets/nb\.js$")
DEFAULT_MIN_SOURCES = {"longread": 8, "shortread": 5}
DEFAULT_CITE_EXEMPT = ("sources",)  # a template extends this via registry cite_exempt
SELF_COUNT_TOLERANCE = 0.20


class Finding:
    def __init__(self, code, level, *, message, suggestion=None):
        self.code, self.level, self.message, self.suggestion = (
            code,
            level,
            message,
            suggestion,
        )

    def as_dict(self):
        d = {"code": self.code, "level": self.level, "message": self.message}
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


class Report:
    def __init__(self, strict=False):
        self.findings = []
        self.strict = strict
        self.notes = []

    def block(self, code, msg, *, suggestion=None):
        finding = Finding(code, "BLOCK", message=msg, suggestion=suggestion)
        self.findings.append(finding)

    def warn(self, code, msg, *, suggestion=None):
        level = "BLOCK" if self.strict else "WARN"
        finding = Finding(code, level, message=msg, suggestion=suggestion)
        self.findings.append(finding)

    @property
    def blocks(self):
        return [f for f in self.findings if f.level == "BLOCK"]

    @property
    def warns(self):
        return [f for f in self.findings if f.level == "WARN"]


# --------------------------------------------------------------------------- #
# HTML parsing
# --------------------------------------------------------------------------- #

VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class Article(HTMLParser):
    """Single-pass structural parse of one article file.

    Collects everything the checks need in one HTMLParser walk:
    sections, script tags, sandbox violations, citations, source
    entries, and word counts. html.parser is tolerant by
    design, so malformed markup degrades into text instead of raising;
    the structural checks downstream catch what matters.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []  # list of dicts per open element
        self.meta_raw = None
        self.meta_count = 0  # number of #nb-meta blocks; >1 is a violation
        self.chart_raw = []  # raw JSON strings of data-nb-chart blocks
        self.script_tags = []  # (attrs_dict) for every <script>
        self.sections = []  # data-nb-section values in order
        self.section_cites = {}  # section -> inline cite count
        self.items = []  # per data-nb-item: {"cites": int, "why": bool}
        self.ids = set()
        self.source_container_ids = set()
        self.source_ids = []  # source entry ids in declaration order
        self.sources = []  # {"href":, "required":}
        self.cite_hrefs = []  # hrefs of anchors inside sup.nb-cite
        self.bad_event_attrs = []
        self.bad_js_urls = []
        self.forbidden_tags = []
        self.external_refs = []  # (tag, url) for script src / link href / img src
        self._capture = None  # ("meta"|"chart", buffer) while inside a JSON script
        self._text_parts = []
        self._suppress_text_depth = 0  # inside script/style

    # -- helpers -------------------------------------------------------------
    def _attrs(self, attrs):
        return {(k or "").lower(): (v if v is not None else "") for k, v in attrs}

    def _current(self, key):
        for el in reversed(self.stack):
            if el.get(key) is not None:
                return el
        return None

    # -- parser events --------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = self._attrs(attrs)
        el = {"tag": tag, "id": a.get("id")}

        if a.get("id"):
            self.ids.add(a["id"])

        for k in a:
            if k.startswith("on"):
                self.bad_event_attrs.append((tag, k))
        for urlkey in ("href", "src"):
            v = a.get(urlkey, "")
            if v.strip().lower().startswith("javascript:"):
                self.bad_js_urls.append((tag, v))

        if tag in ("iframe", "object", "embed", "form"):
            self.forbidden_tags.append(tag)
        if tag == "meta" and a.get("http-equiv", "").strip().lower() == "refresh":
            # a meta-refresh redirects the reader off-site the instant the page loads
            self.forbidden_tags.append("meta[http-equiv=refresh]")

        if tag == "script":
            self.script_tags.append(a)
            src = a.get("src")
            if src:
                self.external_refs.append(("script", src))
            if nb_meta.is_meta_script(a):
                self._capture = ("meta", [])
            elif (a.get("type") or "").strip().lower() == "application/json" and (
                "data-nb-chart" in a
            ):
                self._capture = ("chart", [])
        if tag == "link" and a.get("href"):
            self.external_refs.append(("link", a["href"]))
        if tag == "img" and a.get("src"):
            self.external_refs.append(("img", a["src"]))

        if "data-nb-section" in a:
            name = a["data-nb-section"]
            self.sections.append(name)
            self.section_cites.setdefault(name, 0)
            el["section"] = name
        if "data-nb-item" in a:
            self.items.append({"cites": 0, "why": False})
            el["item"] = len(self.items) - 1
        if "data-nb-why" in a:
            cur = self._current("item")
            if cur is not None:
                self.items[cur["item"]]["why"] = True

        if tag == "sup" and "nb-cite" in a.get("class", "").split():
            el["cite_sup"] = True

        if tag == "a":
            in_sup = any(e.get("cite_sup") for e in self.stack)
            href = a.get("href", "")
            if in_sup and href.startswith("#"):
                self.cite_hrefs.append(href[1:])
                sec = self._current("section")
                if sec is not None:
                    self.section_cites[sec["section"]] = (
                        self.section_cites.get(sec["section"], 0) + 1
                    )
                it = self._current("item")
                if it is not None:
                    self.items[it["item"]]["cites"] += 1
            if "data-nb-source" in a:
                self.sources.append(
                    {
                        "href": href,
                        "required": a.get("data-nb-required") or None,
                    }
                )
                for e in self.stack:
                    if e.get("id"):
                        self.source_container_ids.add(e["id"])
                for e in reversed(self.stack):
                    if e.get("id"):
                        if e["id"] not in self.source_ids:
                            self.source_ids.append(e["id"])
                        break

        if tag in ("script", "style"):
            self._suppress_text_depth += 1
        if tag not in VOID:
            self.stack.append(el)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._suppress_text_depth = max(0, self._suppress_text_depth - 1)
            if tag == "script" and self._capture:
                kind, buf = self._capture
                raw = "".join(buf)
                if kind == "meta":
                    self.meta_count += 1
                    if self.meta_raw is None:
                        # keep the FIRST block — the browser (getElementById) and
                        # build_site/duty (first regex match) all read the first
                        self.meta_raw = raw
                else:
                    self.chart_raw.append(raw)
                self._capture = None
        # pop to matching tag (tolerant of minor nesting slips)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self._capture:
            self._capture[1].append(data)
        elif self._suppress_text_depth == 0:
            self._text_parts.append(data)

    @property
    def word_count(self):
        text = " ".join(self._text_parts)
        return len(re.findall(r"\S+", text))


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #


def load_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_registry(repo):
    """Load every template's manifest, press packages shadowing shipped.

    A template is a folder holding a manifest.yaml (the folder name is the
    id); the manifest carries the geometry the proof enforces. A
    press/templates/<id> package replaces a shipped one of the same id
    wholesale, which is both how a press adds templates and how it
    redefines a shipped template's band press-wide. A folder without a
    manifest.yaml is not a template and is skipped.
    """
    registry = {}
    for base in (
        os.path.join(repo, "templates"),
        os.path.join(repo, "press", "templates"),  # press shadows shipped
    ):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            manifest = os.path.join(base, name, "manifest.yaml")
            if os.path.isfile(manifest):
                registry[name] = load_yaml(manifest) or {}
    return registry


def find_template(repo, template_id):
    for base in (
        os.path.join(repo, "press", "templates"),  # press/ shadows shipped templates/
        os.path.join(repo, "templates"),
    ):
        path = os.path.join(base, template_id, "skeleton.html")
        if os.path.isfile(path):
            return path
    return None


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


DEAD_STATUSES = frozenset((404, 410))
LINK_TIMEOUT_S = 6
LINK_WORKERS = 8
LINK_UA = (
    "Mozilla/5.0 (compatible; NightlyBuild-proof/1.1; "
    "+https://github.com/RyanSaxe/the-nightly-build)"
)


def classify_link(status, error) -> Literal["dead", "ok", "unverified"]:
    """Decide whether a source link is provably dead.

    Only a definitive 'this does not exist' counts: a 404/410 response, or a
    domain that does not resolve (DNS). Everything else — a 200, a bot-blocking
    403, a 5xx, a rate limit, a timeout, or no network at all — is 'unverified'
    and never blocks, so a real-but-restricted source can never fail a
    legitimate article.
    """
    if status in DEAD_STATUSES:
        return "dead"
    if status is not None:
        return "ok"  # got a response: the URL exists (or is merely restricted)
    if error == "dns":
        return "dead"  # the domain itself does not resolve
    return "unverified"  # timeout, refused, offline — cannot say


def _probe_link(href):
    req = urllib.request.Request(
        href, headers={"User-Agent": LINK_UA, "Range": "bytes=0-0"}
    )
    try:
        # A one-byte Range GET, not HEAD: some servers 404/405 a HEAD they would
        # serve, and a browser-like UA keeps casual bot filters from lying to us.
        with urllib.request.urlopen(req, timeout=LINK_TIMEOUT_S) as resp:
            return classify_link(resp.status, None)
    except urllib.error.HTTPError as e:
        return classify_link(e.code, None)
    except urllib.error.URLError as e:
        return classify_link(
            None, "dns" if isinstance(e.reason, socket.gaierror) else "net"
        )
    except (TimeoutError, ValueError, OSError):
        return classify_link(None, "net")


def dead_source_links(hrefs):
    if not hrefs:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=LINK_WORKERS) as pool:
        verdicts = list(pool.map(_probe_link, hrefs))
    return [
        href for href, verdict in zip(hrefs, verdicts, strict=True) if verdict == "dead"
    ]


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #


def chart_spec_error(raw):
    try:
        spec = json.loads(raw)
    except ValueError as e:
        return str(e)
    if not isinstance(spec, dict):
        return "spec must be a JSON object"
    if spec.get("type") not in ("line", "bar", "scatter"):
        return "bad chart type"
    if not isinstance(spec.get("labels"), list) or not spec["labels"]:
        return "labels required"
    series = spec.get("series")
    if not isinstance(series, list) or not series:
        return "series required"
    for s in series:
        if not isinstance(s, dict) or not isinstance(s.get("name"), str):
            return "series name required"
        if not isinstance(s.get("values"), list):
            return "series values required"
    return None


def external_ref_allowed(normalized_url):
    """True when an off-origin link/img reference may load.

    `normalized_url` is browser-normalized (whitespace stripped, backslashes
    folded to slashes). Requires an https scheme and a host in the font
    allowlist, comparing the parsed host — not a string prefix, so
    `fonts.googleapis.com.evil.example`, `fonts.googleapis.com@evil.example`,
    and protocol-relative `//host` refs are all rejected.
    """
    scheme = re.match(r"(https?)://", normalized_url, re.IGNORECASE)
    if not scheme or scheme.group(1).lower() != "https":
        return False
    authority = re.split(r"[/?#]", normalized_url.split("://", 1)[1], maxsplit=1)[0]
    host = authority.rsplit("@", 1)[-1].split(":", 1)[0]
    return host.lower() in ALLOWED_EXTERNAL_HOSTS


def is_repo_relative_source(href):
    if not href or re.search(r"\s", href):
        return False
    normalized = href.replace("\\", "/")
    is_off_origin = "://" in normalized or normalized.startswith("//")
    return not is_off_origin and not normalized.startswith("/")


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
    need("mode", str, enum=["collection", "sequence", "rolling", "open"])
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
    meta, *, series, series_id, template_id, slug_from_path, parent, pr_body_meta, rep
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


def check_sequence_slug(meta, *, items, idx, slug, pub, rep):
    if pub is None:
        if meta.get("order") != idx + 1:
            rep.block(
                "B-MODE",
                f"sequence order must be item position {idx + 1}; "
                f"nb-meta says {meta.get('order')}",
            )
        rep.notes.append(
            "library state not provided (--library); next-expected check skipped"
        )
        return
    expected = next(
        (i for i, it in enumerate(items) if it.get("slug") not in pub), None
    )
    if expected is None:
        rep.block("B-MODE", "sequence is complete; nothing to publish")
    elif idx != expected:
        rep.block(
            "B-MODE",
            f"next expected sequence item is "
            f"'{items[expected].get('slug')}' (#{expected + 1}), not '{slug}'",
        )
    elif meta.get("order") != expected + 1:
        rep.block(
            "B-MODE",
            f"nb-meta order must be {expected + 1}, got {meta.get('order')}",
        )


def check_ordered_mode(meta, *, series_id, items, slug, pub, mode, rep):
    idx = next((i for i, it in enumerate(items) if it.get("slug") == slug), None)
    if idx is None:
        rep.block(
            "B-SLUG",
            f"slug '{slug}' is not a configured item of series '{series_id}'",
        )
        return None
    item_cfg = items[idx]
    if mode == "sequence":
        check_sequence_slug(meta, items=items, idx=idx, slug=slug, pub=pub, rep=rep)
    elif pub is not None and slug in pub:
        rep.block("B-MODE", f"'{slug}' is already published")
    return item_cfg


def check_rolling_mode(meta, *, slug, pub, today, rep):
    if not DATE_RE.match(slug):
        rep.block("B-SLUG", f"rolling slug must be YYYY-MM-DD, got '{slug}'")
    else:
        try:
            d = _dt.date.fromisoformat(slug)
            if d > today:
                rep.block("B-SLUG", f"rolling slug {slug} is in the future")
        except ValueError:
            rep.block("B-SLUG", f"rolling slug '{slug}' is not a real date")
        if meta.get("date") != slug:
            rep.block(
                "B-META-MATCH",
                f"rolling nb-meta date '{meta.get('date')}' must equal slug",
            )
        if pub is not None and slug in pub:
            rep.block("B-MODE", f"a brief for {slug} is already published")
    if pub is None:
        rep.notes.append(
            "library state not provided (--library); already-published check skipped"
        )


def check_open_slug(*, items, slug, pub, rep):
    item_cfg = next((it for it in items if it.get("slug") == slug), None)
    if pub is None:
        rep.notes.append(
            "library state not provided (--library); "
            "open-mode dedupe and commission checks skipped"
        )
        return item_cfg
    if slug in pub:
        rep.block("B-MODE", f"'{slug}' is already published")
    pending = sorted(it.get("slug") for it in items if it.get("slug") not in pub)
    if pending and slug not in pending:
        rep.block(
            "B-MODE",
            f"commissioned items pending: {pending} — publish a "
            f"commission before an open pick",
        )
    return item_cfg


def check_mode(meta, *, series, series_id, slug, pub, today, rep):
    mode = series.get("mode")
    items = series.get("items") or []
    if mode in ("collection", "sequence"):
        return check_ordered_mode(
            meta,
            series_id=series_id,
            items=items,
            slug=slug,
            pub=pub,
            mode=mode,
            rep=rep,
        )
    if mode == "rolling":
        check_rolling_mode(meta, slug=slug, pub=pub, today=today, rep=rep)
        return None
    if mode == "open":
        return check_open_slug(items=items, slug=slug, pub=pub, rep=rep)
    return None


def check_required_sections(ed, treg, rep):
    required_sections = treg.get("sections") or []
    counts = {s: ed.sections.count(s) for s in required_sections}
    for s in required_sections:
        if counts[s] == 0:
            rep.block("B-HTML", f"required section '{s}' (data-nb-section) is missing")
        elif counts[s] > 1:
            rep.block(
                "B-HTML",
                f"section '{s}' appears {counts[s]} times; must be exactly once",
            )
    # Absent flex_sections means a fully fixed outline: no section beyond the
    # anchors is allowed (V6c). Present it as [0, 0] so extras BLOCK rather than
    # slip through unchecked.
    flex_band = treg.get("flex_sections") or [0, 0]
    extras = [s for s in ed.sections if s not in required_sections]
    dupes = sorted({s for s in extras if extras.count(s) > 1})
    if dupes:
        rep.block("B-HTML", f"duplicate section labels: {dupes}")
    low, high = flex_band
    if not (low <= len(extras) <= high):
        rep.block(
            "B-HTML",
            f"{len(extras)} sections beyond the anchors; this template "
            f"expects between {low} and {high}",
        )


def check_sandbox(ed, rep):
    for a in ed.script_tags:
        stype = (a.get("type") or "").strip().lower()
        src = a.get("src", "")
        if src and ENGINE_SCRIPT_RE.match(src) and stype in ("", "text/javascript"):
            continue  # the engine-owned runtime (assets/nb.js) is the one allowed load
        if stype != "application/json":
            rep.block(
                "B-SANDBOX",
                f"articles may not contain executable <script> (type={stype or 'none'})",
            )
        elif a.get("id") != "nb-meta" and "data-nb-chart" not in a:
            rep.block(
                "B-SANDBOX", "JSON <script> blocks must be #nb-meta or data-nb-chart"
            )
        if src:
            rep.block("B-SANDBOX", "articles may not load external scripts")
    if ed.forbidden_tags:
        rep.block(
            "B-SANDBOX", f"forbidden tags present: {sorted(set(ed.forbidden_tags))}"
        )
    for tag, attr in ed.bad_event_attrs:
        rep.block("B-SANDBOX", f"inline event handler {attr}= on <{tag}>")
    for tag, _url in ed.bad_js_urls:
        rep.block("B-SANDBOX", f"javascript: URL on <{tag}>")
    for kind, url in ed.external_refs:
        if kind == "script":
            continue  # already blocked above
        # Normalize the way a browser resolves a URL before matching the
        # allowlist: strip URL-spec whitespace (tab/newline/cr) and fold
        # backslashes to slashes, so "//host", "/\host", or "ht\ntps://host"
        # cannot slip an off-origin load past the check.
        u = re.sub(r"[\t\n\r]", "", (url or "").strip()).replace("\\", "/")
        is_external = "://" in u or u.startswith("//")
        if is_external and not external_ref_allowed(u):
            rep.block("B-SANDBOX", f"external {kind} reference not on allowlist: {url}")
    for i, raw_chart in enumerate(ed.chart_raw, 1):
        err = chart_spec_error(raw_chart)
        if err is not None:
            rep.block("B-SANDBOX", f"data-nb-chart block #{i} invalid: {err}")


def check_sources(ed, rep, *, check_links):
    if not ed.sources:
        rep.block("B-SOURCES-FORM", "no source entries (a[data-nb-source]) found")
    well_formed = []
    for s in ed.sources:
        href = s["href"]
        if re.match(r"^https://[^\s]+$", href or ""):
            well_formed.append(href)
        elif s["required"] and is_repo_relative_source(href):
            continue  # local-file citation (V6a): no public URL to probe
        else:
            rep.block(
                "B-SOURCES-FORM", f"source href must be absolute https URL: {href!r}"
            )
    # B-SOURCE-DEAD: each cited URL must actually resolve (editor gate)
    if check_links:
        for href in dead_source_links(well_formed):
            rep.block(
                "B-SOURCE-DEAD",
                f"source link does not resolve (404 or no such domain): {href}",
            )


def check_cites(ed, rep):
    for target in ed.cite_hrefs:
        if target not in ed.ids:
            rep.block(
                "B-CITES-RESOLVE", f"inline citation '#{target}' resolves to nothing"
            )
        elif target not in ed.source_container_ids:
            rep.block(
                "B-CITES-RESOLVE",
                f"inline citation '#{target}' does not point at a source entry",
            )


def check_warns(ed, meta, *, series, treg, template_id, item_cfg, rep):
    band = series.get("words") or treg.get("words")
    if band:
        lo, hi = band
        if series.get("words"):
            reg_lo = (treg.get("words") or [0])[0]
            lo = max(lo, reg_lo)  # series may tighten, never loosen below registry
        wc = ed.word_count
        if wc < lo:
            rep.warn(
                "W-LENGTH-LOW",
                f"{template_id} band is {lo}-{hi} words; found {wc}",
                suggestion="consider deepening the thinnest section",
            )
        elif wc > hi:
            rep.warn(
                "W-LENGTH-HIGH",
                f"{template_id} band is {lo}-{hi} words; found {wc}",
                suggestion="consider trimming or splitting",
            )
    if treg.get("items"):
        lo, hi = treg["items"]
        n = len(ed.items)
        if n < lo:
            rep.warn(
                "W-LENGTH-LOW",
                f"{template_id} expects {lo}-{hi} items; found {n}",
                suggestion="add an item to reach the band",
            )
        elif n > hi:
            rep.warn(
                "W-LENGTH-HIGH",
                f"{template_id} expects {lo}-{hi} items; found {n}",
                suggestion="cut the weakest item to the band",
            )

    # source floor
    floor = series.get("min_sources") or DEFAULT_MIN_SOURCES.get(
        treg.get("class", "longread"), 5
    )
    if len(ed.sources) < floor:
        rep.warn("W-SOURCES-MIN", f"{len(ed.sources)} sources; series floor is {floor}")

    # cite density
    rule = treg.get("cite_rule")
    if rule == "per-section":
        exempt = set(DEFAULT_CITE_EXEMPT) | set(treg.get("cite_exempt") or ())
        for s in dict.fromkeys(ed.sections):
            if s in exempt:
                continue
            if ed.section_cites.get(s, 0) == 0:
                rep.warn("W-CITE-DENSITY", f"section '{s}' has no inline citations")
    elif rule == "per-item":
        for i, it in enumerate(ed.items, 1):
            if it["cites"] == 0:
                rep.warn("W-CITE-DENSITY", f"item #{i} has no inline citations")

    # citation order: sources should be numbered in order of first appearance
    if ed.source_ids:
        decl = {sid: i for i, sid in enumerate(ed.source_ids)}
        seen = set()
        frontier = 0
        for target in ed.cite_hrefs:
            if target in seen or target not in decl:
                continue
            seen.add(target)
            if decl[target] != frontier:
                rep.warn(
                    "W-CITE-ORDER",
                    f"citation '#{target}' (source {decl[target] + 1}) is first "
                    f"cited before source {frontier + 1}; number sources in order "
                    "of first appearance",
                )
                break
            frontier += 1

    # per-item "why it matters", when the template's registry entry requires it
    if treg.get("require_why"):
        for i, it in enumerate(ed.items, 1):
            if not it["why"]:
                rep.warn(
                    "W-WHY-MISSING",
                    f"item #{i} lacks a 'why it matters' line (data-nb-why)",
                )

    # source policy: required docs must be read AND cited; consult prefixes
    # must be read first but citing them is optional (no check here); with
    # sources_exclusive, citations may come ONLY from the declared set.
    req_docs = list((item_cfg or {}).get("required_docs") or []) + list(
        series.get("required_docs") or []
    )
    declared_doc_ids = {doc.get("id") for doc in req_docs}
    got_required = {s["required"] for s in ed.sources if s["required"]}
    for doc in req_docs:
        if doc.get("id") not in got_required:
            rep.warn(
                "W-REQ-DOC",
                f"required doc '{doc.get('id')}' has no data-nb-required source entry",
            )
    consult = list(series.get("consult") or []) + list(
        (item_cfg or {}).get("consult") or []
    )
    if series.get("sources_exclusive"):
        for s in ed.sources:
            if s["required"] and s["required"] in declared_doc_ids:
                continue
            if not any(s["href"].startswith(prefix) for prefix in consult):
                rep.block(
                    "B-SOURCES-EXCLUSIVE",
                    f"source outside the declared set: {s['href']}",
                    suggestion="this series is sources_exclusive — cite only "
                    "required_docs and consult sources",
                )

    # self-counts
    if isinstance(meta.get("sources"), int) and ed.sources:
        actual = len(ed.sources)
        if abs(meta["sources"] - actual) > SELF_COUNT_TOLERANCE * max(actual, 1):
            rep.warn(
                "W-SELF-COUNT",
                f"nb-meta sources={meta['sources']} vs counted {actual}",
                suggestion="update nb-meta sources to the counted total",
            )
    if isinstance(meta.get("words"), int):
        actual = ed.word_count
        if actual and abs(meta["words"] - actual) > SELF_COUNT_TOLERANCE * actual:
            rep.warn(
                "W-SELF-COUNT",
                f"nb-meta words={meta['words']} vs counted {actual}",
                suggestion="update nb-meta words to the counted total",
            )


def check_article(
    html_path,
    series_id,
    *,
    repo,
    library_dir,
    rep,
    pr_body_meta=None,
    today=None,
    check_links=False,
) -> dict | None:
    today = today or _dt.date.today()

    resolved = resolve_series_and_template(repo, series_id, rep)
    if resolved is None:
        return None
    series, registry, mode_cfg, template_id, treg, allowed_templates = resolved

    raw = read_article_source(html_path, rep)
    if raw is None:
        return None

    ed = Article()
    ed.feed(raw)
    ed.close()

    meta = parse_meta(ed, rep)
    if meta is None:
        return None

    if mode_cfg == "open":
        bound = bind_open_template(meta, registry, allowed_templates, rep)
        if bound is None:
            return None
        template_id, treg = bound

    fname = os.path.basename(html_path)
    slug_from_path = fname[:-5] if fname.endswith(".html") else fname
    parent = os.path.basename(os.path.dirname(html_path))
    check_meta_agreement(
        meta,
        series=series,
        series_id=series_id,
        template_id=template_id,
        slug_from_path=slug_from_path,
        parent=parent,
        pr_body_meta=pr_body_meta,
        rep=rep,
    )

    slug = meta.get("slug") or slug_from_path
    pub = published_slugs(library_dir, series_id)
    item_cfg = check_mode(
        meta,
        series=series,
        series_id=series_id,
        slug=slug,
        pub=pub,
        today=today,
        rep=rep,
    )

    check_required_sections(ed, treg, rep)
    check_sandbox(ed, rep)
    check_sources(ed, rep, check_links=check_links)
    check_cites(ed, rep)
    check_warns(
        ed,
        meta,
        series=series,
        treg=treg,
        template_id=template_id,
        item_cfg=item_cfg,
        rep=rep,
    )
    return meta


# --------------------------------------------------------------------------- #
# PR mode
# --------------------------------------------------------------------------- #

PR_PATH_RE = re.compile(r"^library/([a-z0-9-]{1,32})/([a-z0-9-]{1,64})\.html$")


def parse_pr_body(path) -> dict | None:
    with open(path, encoding="utf-8") as fh:
        body = fh.read()
    m = re.search(r"```nb-meta\s*\n(.*?)```", body, re.S)
    if not m:
        return None
    try:
        data = yaml.safe_load(m.group(1))
        if not isinstance(data, dict):
            return None
        # YAML reads bare dates (slug: 2026-07-05) as date objects; nb-meta
        # holds strings — normalize so honest PR bodies compare equal
        return {
            k: (v.isoformat() if isinstance(v, _dt.date) else v)
            for k, v in data.items()
        }
    except yaml.YAMLError:
        return None


def pr_changed_files(repo, *, base, head):
    out = subprocess.run(
        [
            "git",
            "-C",
            repo,
            "diff",
            "--name-status",
            "--no-renames",
            f"{base}...{head}",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    changes = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            changes.append((parts[0], parts[-1]))
    return changes


def resolve_pr_body(pr_body_path, rep) -> dict | None:
    """Parse a PR body file and flag a missing or unparseable nb-meta block.

    Shared by CI mode and the local preflight (`--pr-body` without `--pr`), so
    an author can verify the exact body they intend to post before opening the
    pull request. Returns the parsed metadata, or None when no path is given.
    """
    if not pr_body_path:
        return None
    meta = parse_pr_body(pr_body_path)
    if meta is None:
        rep.block("B-META-MATCH", "PR body lacks a parseable ```nb-meta``` yaml block")
    return meta


def run_pr_mode(args, rep):
    try:
        changes = pr_changed_files(args.repo, base=args.base, head=args.head)
    except subprocess.CalledProcessError as e:
        rep.block("B-DIFF-SHAPE", f"git diff failed: {e.stderr or e}")
        return
    if len(changes) != 1:
        rep.block(
            "B-DIFF-SHAPE",
            f"PR must change exactly one file; found {len(changes)}: "
            f"{[p for _, p in changes]}",
        )
        return
    status, path = changes[0]
    if status != "A":
        rep.block(
            "B-DIFF-SHAPE", f"the one change must be an addition; got status '{status}'"
        )
        return
    m = PR_PATH_RE.match(path)
    if not m:
        rep.block(
            "B-DIFF-SHAPE",
            f"added file must be library/<series>/<slug>.html; got '{path}'",
        )
        return
    series_id = m.group(1)
    cfg_repo = getattr(args, "main", None) or args.repo
    series_cfg, _ = load_series(cfg_repo, series_id)
    rep.strict = bool(series_cfg and series_cfg.get("strict"))
    pr_body_meta = resolve_pr_body(args.pr_body, rep)
    fs_path = os.path.join(args.repo, path)
    check_article(
        fs_path,
        series_id,
        repo=cfg_repo,
        library_dir=args.library,
        rep=rep,
        pr_body_meta=pr_body_meta,
        today=args.today and _dt.date.fromisoformat(args.today),
        check_links=args.check_links,
    )


# --------------------------------------------------------------------------- #
# Output / CLI
# --------------------------------------------------------------------------- #


def emit(rep, as_json):
    blocks, warns = rep.blocks, rep.warns
    if as_json:
        print(
            json.dumps(
                {
                    "block_count": len(blocks),
                    "warn_count": len(warns),
                    "findings": [f.as_dict() for f in rep.findings],
                    "notes": rep.notes,
                },
                indent=2,
            )
        )
    else:
        print(f"BLOCK: {len(blocks)}")
        for f in blocks:
            print(f"  {f.code:<18} {f.message}")
            if f.suggestion:
                print(f"  {'':<18} → {f.suggestion}")
        print(f"WARN:  {len(warns)}")
        for f in warns:
            print(f"  {f.code:<18} {f.message}")
            if f.suggestion:
                print(f"  {'':<18} → {f.suggestion}")
        for n in rep.notes:
            print(f"note: {n}")
        print("verdict:", "PUBLISHABLE" if not blocks else "BLOCKED")
    return 0 if not blocks else 1


def main(argv=None):
    p = argparse.ArgumentParser(description="The Nightly Build proof")
    p.add_argument("file", nargs="?", help="article HTML file (local mode)")
    p.add_argument("--series", help="series id (local mode)")
    p.add_argument(
        "--repo",
        default=".",
        help="repo root (local mode: main checkout; PR mode: PR checkout)",
    )
    p.add_argument(
        "--main",
        help="main checkout for configs/registry (PR mode; defaults to --repo)",
    )
    p.add_argument("--library", help="published library state (branch checkout dir)")
    p.add_argument("--pr", action="store_true", help="CI mode")
    p.add_argument("--base", help="PR base ref (pr mode)")
    p.add_argument("--head", default="HEAD", help="PR head ref (pr mode)")
    p.add_argument(
        "--pr-body",
        help="PR body file; cross-checks its nb-meta against the article "
        "(CI mode, or a local preflight before opening the PR)",
    )
    p.add_argument("--today", help="override today's date (tests)")
    p.add_argument(
        "--check-links",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="verify each source URL resolves (on by default, needs network). "
        "Blocks only on a 404/410 or a domain that does not resolve; restricted, "
        "slow, or unreachable sources never block. Use --no-check-links offline.",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    # strict comes from the series config; resolve it lazily
    rep = Report(strict=False)

    if args.pr:
        if not args.base:
            p.error("--pr requires --base")
        run_pr_mode(args, rep)
    else:
        if not args.file or not args.series:
            p.error("local mode requires FILE and --series")
        series, _ = load_series(args.repo, args.series)
        rep.strict = bool(series and series.get("strict"))
        check_article(
            args.file,
            args.series,
            repo=args.repo,
            library_dir=args.library,
            rep=rep,
            pr_body_meta=resolve_pr_body(args.pr_body, rep),
            today=args.today and _dt.date.fromisoformat(args.today),
            check_links=args.check_links,
        )

    return emit(rep, args.json)


if __name__ == "__main__":
    sys.exit(main())
