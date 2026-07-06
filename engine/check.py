#!/usr/bin/env python3
"""
The Nightly Build — engine/check.py ("the proof")

One tool, two tiers:
  BLOCK — site/protocol integrity. CI refuses to publish on any BLOCK.
  WARN  — quality calibration. Never blocks (unless the series sets strict: true).

Invocations:
  Agent loop / press check:
    python3 engine/check.py library/<series>/<slug>.html --series <id> --repo . [--library DIR]
  CI:
    python3 engine/check.py --pr --repo . --main <main checkout> \
        --base <ref> --head <ref> [--pr-body FILE] [--library DIR]

  In PR mode --repo is the PR checkout (git diff + edition file); configs and
  the registry load from --main, because the library branch carries no engine
  or series files. --main defaults to --repo for repos that keep both together.

  --library DIR points at the PUBLISHED state (the library branch checkout, or its
  library/ folder) BEFORE this edition; used for sequence/rolling next-work checks.
  If omitted, those specific sub-checks are skipped with a note.

Exit code: 0 iff BLOCK count is 0. Machine output via --json.

Dependencies: Python stdlib + PyYAML.
"""

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("check.py requires PyYAML (pip install pyyaml)\n")
    sys.exit(2)

PROTOCOL_MAJOR = "1"
MAX_BYTES = 2 * 1024 * 1024
SLUG_RE = re.compile(r"^[a-z0-9-]{1,64}$")
SERIES_RE = re.compile(r"^[a-z0-9-]{1,32}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_EXTERNAL_PREFIXES = (
    "/assets/",
    "https://fonts.googleapis.com",
    "https://fonts.gstatic.com",
)
# The one executable script an edition may load: the engine-owned runtime
# (§7.4 — contextual nav + chart renderer), by relative or root-absolute path.
ENGINE_SCRIPT_RE = re.compile(r"^(?:(?:\.\./)+|/)assets/nb\.js$")
DEFAULT_MIN_SOURCES = {"longread": 8, "shortread": 5}
CITE_EXEMPT_SECTIONS = {"sources", "objectives", "slides", "items"}
DECK_CITE_EXEMPT_KINDS = {"title", "divider"}
SELF_COUNT_TOLERANCE = 0.20


class Finding:
    def __init__(self, code, level, message, suggestion=None):
        self.code, self.level, self.message, self.suggestion = code, level, message, suggestion

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

    def block(self, code, msg, suggestion=None):
        self.findings.append(Finding(code, "BLOCK", msg, suggestion))

    def warn(self, code, msg, suggestion=None):
        level = "BLOCK" if self.strict else "WARN"
        self.findings.append(Finding(code, level, msg, suggestion))

    def note(self, msg):
        self.notes.append(msg)

    @property
    def blocks(self):
        return [f for f in self.findings if f.level == "BLOCK"]

    @property
    def warns(self):
        return [f for f in self.findings if f.level == "WARN"]


# --------------------------------------------------------------------------- #
# HTML parsing
# --------------------------------------------------------------------------- #

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}


class Edition(HTMLParser):
    """Single-pass structural parse of an edition file."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []                # list of dicts per open element
        self.parse_ok = True
        self.meta_raw = None
        self.chart_raw = []            # raw JSON strings of data-nb-chart blocks
        self.script_tags = []          # (attrs_dict) for every <script>
        self.sections = []             # data-nb-section values in order
        self.section_cites = {}        # section -> inline cite count
        self.items = []                # per data-nb-item: {"cites": int, "why": bool}
        self.slides = []               # per data-nb-slide: {"kind": str, "cites": int}
        self.ids = set()
        self.source_container_ids = set()
        self.sources = []              # {"href":, "required":}
        self.cite_hrefs = []           # hrefs of anchors inside sup.nb-cite
        self.bad_event_attrs = []
        self.bad_js_urls = []
        self.forbidden_tags = []
        self.external_refs = []        # (tag, url) for script src / link href / img src
        self._capture = None           # ("meta"|"chart", buffer) while inside a JSON script
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

        if tag in ("iframe", "object", "embed"):
            self.forbidden_tags.append(tag)

        if tag == "script":
            self.script_tags.append(a)
            src = a.get("src")
            if src:
                self.external_refs.append(("script", src))
            stype = a.get("type", "").strip().lower()
            if stype == "application/json":
                if a.get("id") == "nb-meta":
                    self._capture = ("meta", [])
                elif "data-nb-chart" in a:
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
        if "data-nb-slide" in a:
            self.slides.append({"kind": a.get("data-kind", ""), "cites": 0})
            el["slide"] = len(self.slides) - 1
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
                    self.section_cites[sec["section"]] = \
                        self.section_cites.get(sec["section"], 0) + 1
                it = self._current("item")
                if it is not None:
                    self.items[it["item"]]["cites"] += 1
                sl = self._current("slide")
                if sl is not None:
                    self.slides[sl["slide"]]["cites"] += 1
            if "data-nb-source" in a:
                self.sources.append({
                    "href": href,
                    "required": a.get("data-nb-required") or None,
                })
                for e in self.stack:
                    if e.get("id"):
                        self.source_container_ids.add(e["id"])

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

    def error(self, message):  # pragma: no cover (py<3.10 compat)
        self.parse_ok = False

    @property
    def word_count(self):
        return len(re.findall(r"\S+", " ".join(self._text_parts)))


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_registry(repo):
    return load_yaml(os.path.join(repo, "templates", "registry.yaml"))


def load_series(repo, series_id):
    path = os.path.join(repo, "series", series_id, "series.yaml")
    if not os.path.isfile(path):
        return None, path
    return load_yaml(path), path


def published_slugs(library_dir, series_id):
    """Return set of published slugs for a series, or None if unknowable."""
    if not library_dir:
        return None
    for base in (os.path.join(library_dir, "library", series_id),
                 os.path.join(library_dir, series_id)):
        if os.path.isdir(base):
            return {f[:-5] for f in os.listdir(base) if f.endswith(".html")}
    return set()  # library exists but series dir doesn't => nothing published


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #

def validate_meta_fields(meta, rep):
    def need(field, typ, pattern=None, enum=None):
        v = meta.get(field)
        if v is None:
            rep.block("B-META-PARSE", f"nb-meta missing required field '{field}'")
            return None
        if typ and not isinstance(v, typ):
            rep.block("B-META-PARSE", f"nb-meta field '{field}' has wrong type")
            return None
        if pattern and not re.match(pattern, str(v)):
            rep.block("B-META-PARSE", f"nb-meta field '{field}' fails pattern {pattern}")
        if enum and v not in enum:
            rep.block("B-META-PARSE", f"nb-meta field '{field}' must be one of {enum}")
        return v

    need("protocol", str)
    if isinstance(meta.get("protocol"), str) and \
            meta["protocol"].split(".")[0] != PROTOCOL_MAJOR:
        rep.block("B-META-PARSE",
                  f"protocol major must be {PROTOCOL_MAJOR}, got {meta.get('protocol')}")
    need("series", str, pattern=SERIES_RE.pattern)
    need("slug", str, pattern=SLUG_RE.pattern)
    need("template", str,
         enum=["dossier", "lesson", "brief", "paper", "chronicle", "deck"])
    need("title", str)
    need("mode", str, enum=["collection", "sequence", "rolling"])
    need("date", str, pattern=DATE_RE.pattern)
    need("dek", str)
    need("sources", int)
    need("harness", str)
    need("model", str)
    order = meta.get("order")
    if order is not None and (not isinstance(order, int) or order < 1):
        rep.block("B-META-PARSE", "nb-meta 'order' must be a positive integer or null")


def check_edition(html_path, series_id, repo, library_dir, rep,
                  pr_body_meta=None, today=None):
    today = today or _dt.date.today()

    # --- B-SERIES ---
    series, spath = load_series(repo, series_id)
    if series is None:
        rep.block("B-SERIES", f"series '{series_id}' not found at {spath}")
        return None
    try:
        registry = load_registry(repo)
    except Exception as e:
        rep.block("B-SERIES", f"templates/registry.yaml unreadable: {e}")
        return None

    template_id = series.get("template")
    treg = (registry or {}).get(template_id)
    if not treg:
        rep.block("B-SERIES",
                  f"series template '{template_id}' not in templates/registry.yaml")
        return None
    if series.get("mode") not in (treg.get("modes") or []):
        rep.block("B-SERIES",
                  f"series mode '{series.get('mode')}' not allowed for template "
                  f"'{template_id}' (allowed: {treg.get('modes')})")

    # --- file existence / size ---
    if not os.path.isfile(html_path):
        rep.block("B-HTML", f"file not found: {html_path}")
        return None
    size = os.path.getsize(html_path)
    if size > MAX_BYTES:
        rep.block("B-HTML", f"file is {size} bytes; limit is {MAX_BYTES}")
    with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()

    ed = Edition()
    try:
        ed.feed(raw)
        ed.close()
    except Exception as e:
        rep.block("B-HTML", f"HTML failed to parse: {e}")
        return None

    # --- B-META-PARSE ---
    if not ed.meta_raw:
        rep.block("B-META-PARSE", "no <script type=\"application/json\" id=\"nb-meta\"> block")
        return None
    try:
        meta = json.loads(ed.meta_raw)
        if not isinstance(meta, dict):
            raise ValueError("nb-meta must be a JSON object")
    except Exception as e:
        rep.block("B-META-PARSE", f"nb-meta JSON invalid: {e}")
        return None
    validate_meta_fields(meta, rep)

    # --- path <-> meta agreement (B-META-MATCH) ---
    fname = os.path.basename(html_path)
    slug_from_path = fname[:-5] if fname.endswith(".html") else fname
    parent = os.path.basename(os.path.dirname(html_path))
    if meta.get("slug") != slug_from_path:
        rep.block("B-META-MATCH",
                  f"path slug '{slug_from_path}' != nb-meta slug '{meta.get('slug')}'")
    if parent and parent != series_id:
        rep.block("B-META-MATCH",
                  f"file sits under '{parent}/' but series is '{series_id}'")
    if meta.get("series") != series_id:
        rep.block("B-META-MATCH",
                  f"nb-meta series '{meta.get('series')}' != declared series '{series_id}'")
    if meta.get("mode") != series.get("mode"):
        rep.block("B-META-MATCH",
                  f"nb-meta mode '{meta.get('mode')}' != series mode '{series.get('mode')}'")
    if meta.get("template") != template_id:
        rep.block("B-META-MATCH",
                  f"nb-meta template '{meta.get('template')}' != series template '{template_id}'")
    if pr_body_meta is not None:
        for field in ("series", "slug", "mode", "template", "date", "title"):
            if field in pr_body_meta and pr_body_meta.get(field) != meta.get(field):
                rep.block("B-META-MATCH",
                          f"PR body '{field}'={pr_body_meta.get(field)!r} disagrees "
                          f"with embedded nb-meta {meta.get(field)!r}")
        b_order = pr_body_meta.get("order", meta.get("order"))
        if b_order != meta.get("order"):
            rep.block("B-META-MATCH", "PR body 'order' disagrees with embedded nb-meta")

    # --- B-SLUG / B-MODE ---
    mode = series.get("mode")
    slug = meta.get("slug") or slug_from_path
    items = series.get("items") or []
    item_cfg = None
    pub = published_slugs(library_dir, series_id)

    if mode in ("collection", "sequence"):
        idx = next((i for i, it in enumerate(items) if it.get("slug") == slug), None)
        if idx is None:
            rep.block("B-SLUG", f"slug '{slug}' is not a configured item of series "
                                f"'{series_id}'")
        else:
            item_cfg = items[idx]
            if mode == "sequence":
                if pub is None:
                    if meta.get("order") != idx + 1:
                        rep.block("B-MODE",
                                  f"sequence order must be item position {idx + 1}; "
                                  f"nb-meta says {meta.get('order')}")
                    rep.note("library state not provided (--library); "
                             "next-expected check skipped")
                else:
                    expected = next((i for i, it in enumerate(items)
                                     if it.get("slug") not in pub), None)
                    if expected is None:
                        rep.block("B-MODE", "sequence is complete; nothing to publish")
                    elif idx != expected:
                        rep.block("B-MODE",
                                  f"next expected sequence item is "
                                  f"'{items[expected].get('slug')}' (#{expected + 1}), "
                                  f"not '{slug}'")
                    elif meta.get("order") != expected + 1:
                        rep.block("B-MODE",
                                  f"nb-meta order must be {expected + 1}, "
                                  f"got {meta.get('order')}")
            else:
                if pub is not None and slug in pub:
                    rep.block("B-MODE", f"'{slug}' is already published")
    elif mode == "rolling":
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
                rep.block("B-META-MATCH",
                          f"rolling nb-meta date '{meta.get('date')}' must equal slug")
            if pub is not None and slug in pub:
                rep.block("B-MODE", f"a brief for {slug} is already published")
        if pub is None:
            rep.note("library state not provided (--library); "
                     "already-published check skipped")

    # --- B-HTML: required sections ---
    required_sections = treg.get("sections") or []
    counts = {s: ed.sections.count(s) for s in required_sections}
    for s in required_sections:
        if counts[s] == 0:
            rep.block("B-HTML", f"required section '{s}' (data-nb-section) is missing")
        elif counts[s] > 1:
            rep.block("B-HTML", f"section '{s}' appears {counts[s]} times; must be exactly once")

    # --- B-SANDBOX ---
    for a in ed.script_tags:
        stype = (a.get("type") or "").strip().lower()
        src = a.get("src", "")
        if src and ENGINE_SCRIPT_RE.match(src) and stype in ("", "text/javascript"):
            continue  # the engine-owned runtime (assets/nb.js) is the one allowed load
        if stype != "application/json":
            rep.block("B-SANDBOX",
                      f"editions may not contain executable <script> (type={stype or 'none'})")
        elif a.get("id") != "nb-meta" and "data-nb-chart" not in a:
            rep.block("B-SANDBOX",
                      "JSON <script> blocks must be #nb-meta or data-nb-chart")
        if src:
            rep.block("B-SANDBOX", "editions may not load external scripts")
    if ed.forbidden_tags:
        rep.block("B-SANDBOX", f"forbidden tags present: {sorted(set(ed.forbidden_tags))}")
    for tag, attr in ed.bad_event_attrs:
        rep.block("B-SANDBOX", f"inline event handler {attr}= on <{tag}>")
    for tag, url in ed.bad_js_urls:
        rep.block("B-SANDBOX", f"javascript: URL on <{tag}>")
    for kind, url in ed.external_refs:
        if kind == "script":
            continue  # already blocked above
        if not url.startswith(ALLOWED_EXTERNAL_PREFIXES) and "://" in url:
            rep.block("B-SANDBOX",
                      f"external {kind} reference not on allowlist: {url}")
    for i, raw_chart in enumerate(ed.chart_raw, 1):
        try:
            spec = json.loads(raw_chart)
            assert isinstance(spec, dict)
            assert spec.get("type") in ("line", "bar", "scatter"), "bad chart type"
            assert isinstance(spec.get("labels"), list) and spec["labels"], "labels required"
            assert isinstance(spec.get("series"), list) and spec["series"], "series required"
            for s in spec["series"]:
                assert isinstance(s.get("name"), str), "series name required"
                assert isinstance(s.get("values"), list), "series values required"
        except Exception as e:
            rep.block("B-SANDBOX", f"data-nb-chart block #{i} invalid: {e}")

    # --- B-SOURCES-FORM ---
    if not ed.sources:
        rep.block("B-SOURCES-FORM", "no source entries (a[data-nb-source]) found")
    for s in ed.sources:
        href = s["href"]
        if not re.match(r"^https://[^\s]+$", href or ""):
            rep.block("B-SOURCES-FORM",
                      f"source href must be absolute https URL: {href!r}")

    # --- B-CITES-RESOLVE ---
    for target in ed.cite_hrefs:
        if target not in ed.ids:
            rep.block("B-CITES-RESOLVE", f"inline citation '#{target}' resolves to nothing")
        elif target not in ed.source_container_ids:
            rep.block("B-CITES-RESOLVE",
                      f"inline citation '#{target}' does not point at a source entry")

    # ============================ WARN tier ============================ #

    # length band
    band = series.get("words") or treg.get("words")
    if band:
        lo, hi = band
        if series.get("words"):
            reg_lo = (treg.get("words") or [0])[0]
            lo = max(lo, reg_lo)  # series may tighten, never loosen below registry
        wc = ed.word_count
        if wc < lo:
            rep.warn("W-LENGTH-LOW",
                     f"{template_id} band is {lo}-{hi} words; found {wc}",
                     "consider deepening the thinnest section")
        elif wc > hi:
            rep.warn("W-LENGTH-HIGH",
                     f"{template_id} band is {lo}-{hi} words; found {wc}",
                     "consider trimming or splitting")
    if treg.get("items"):
        lo, hi = treg["items"]
        n = len(ed.items)
        if n < lo:
            rep.warn("W-LENGTH-LOW", f"brief expects {lo}-{hi} items; found {n}")
        elif n > hi:
            rep.warn("W-LENGTH-HIGH", f"brief expects {lo}-{hi} items; found {n}")
    if treg.get("slides"):
        lo, hi = treg["slides"]
        n = len(ed.slides)
        if n < lo:
            rep.warn("W-LENGTH-LOW", f"deck expects {lo}-{hi} slides; found {n}")
        elif n > hi:
            rep.warn("W-LENGTH-HIGH", f"deck expects {lo}-{hi} slides; found {n}")

    # source floor
    floor = series.get("min_sources") or \
        DEFAULT_MIN_SOURCES.get(treg.get("class", "longread"), 5)
    if len(ed.sources) < floor:
        rep.warn("W-SOURCES-MIN",
                 f"{len(ed.sources)} sources; series floor is {floor}")

    # cite density
    rule = treg.get("cite_rule")
    if rule == "per-section":
        for s in required_sections:
            if s in CITE_EXEMPT_SECTIONS:
                continue
            if ed.section_cites.get(s, 0) == 0:
                rep.warn("W-CITE-DENSITY", f"section '{s}' has no inline citations")
    elif rule == "per-item":
        for i, it in enumerate(ed.items, 1):
            if it["cites"] == 0:
                rep.warn("W-CITE-DENSITY", f"item #{i} has no inline citations")
    elif rule == "per-slide":
        for i, sl in enumerate(ed.slides, 1):
            if sl["kind"] in DECK_CITE_EXEMPT_KINDS:
                continue
            if sl["cites"] == 0:
                rep.warn("W-CITE-DENSITY", f"slide #{i} has no citations")

    # brief: why-it-matters
    if template_id == "brief":
        for i, it in enumerate(ed.items, 1):
            if not it["why"]:
                rep.warn("W-WHY-MISSING",
                         f"item #{i} lacks a 'why it matters' line (data-nb-why)")

    # required docs / urls
    req_docs = list((item_cfg or {}).get("required_docs") or []) + \
        list(series.get("required_docs") or [])
    got_required = {s["required"] for s in ed.sources if s["required"]}
    for doc in req_docs:
        if doc.get("id") not in got_required:
            rep.warn("W-REQ-DOC",
                     f"required doc '{doc.get('id')}' has no data-nb-required source entry")
    req_urls = list(series.get("required_urls") or []) + \
        list((item_cfg or {}).get("required_urls") or [])
    hrefs = [s["href"] for s in ed.sources]
    for prefix in req_urls:
        if not any(h.startswith(prefix) for h in hrefs):
            rep.warn("W-REQ-URL", f"no source matching required prefix {prefix}",
                     "add a citation from that source")

    # self-counts
    if isinstance(meta.get("sources"), int) and ed.sources:
        actual = len(ed.sources)
        if abs(meta["sources"] - actual) > SELF_COUNT_TOLERANCE * max(actual, 1):
            rep.warn("W-SELF-COUNT",
                     f"nb-meta sources={meta['sources']} vs counted {actual}")
    if isinstance(meta.get("words"), int):
        actual = ed.word_count
        if actual and abs(meta["words"] - actual) > SELF_COUNT_TOLERANCE * actual:
            rep.warn("W-SELF-COUNT",
                     f"nb-meta words={meta['words']} vs counted {actual}")

    return meta


# --------------------------------------------------------------------------- #
# PR mode
# --------------------------------------------------------------------------- #

PR_PATH_RE = re.compile(r"^library/([a-z0-9-]{1,32})/([a-z0-9-]{1,64})\.html$")


def parse_pr_body(path):
    with open(path, "r", encoding="utf-8") as fh:
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
        return {k: (v.isoformat() if isinstance(v, _dt.date) else v)
                for k, v in data.items()}
    except Exception:
        return None


def pr_changed_files(repo, base, head):
    out = subprocess.run(
        ["git", "-C", repo, "diff", "--name-status", "--no-renames",
         f"{base}...{head}"],
        capture_output=True, text=True, check=True).stdout
    changes = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            changes.append((parts[0], parts[-1]))
    return changes


def run_pr_mode(args, rep):
    try:
        changes = pr_changed_files(args.repo, args.base, args.head)
    except subprocess.CalledProcessError as e:
        rep.block("B-DIFF-SHAPE", f"git diff failed: {e.stderr or e}")
        return
    if len(changes) != 1:
        rep.block("B-DIFF-SHAPE",
                  f"PR must change exactly one file; found {len(changes)}: "
                  f"{[p for _, p in changes]}")
        return
    status, path = changes[0]
    if status != "A":
        rep.block("B-DIFF-SHAPE", f"the one change must be an addition; got status '{status}'")
        return
    m = PR_PATH_RE.match(path)
    if not m:
        rep.block("B-DIFF-SHAPE",
                  f"added file must be library/<series>/<slug>.html; got '{path}'")
        return
    series_id = m.group(1)
    cfg_repo = getattr(args, "main", None) or args.repo
    series_cfg, _ = load_series(cfg_repo, series_id)
    rep.strict = bool(series_cfg and series_cfg.get("strict"))
    pr_body_meta = None
    if args.pr_body:
        pr_body_meta = parse_pr_body(args.pr_body)
        if pr_body_meta is None:
            rep.block("B-META-MATCH", "PR body lacks a parseable ```nb-meta``` yaml block")
    fs_path = os.path.join(args.repo, path)
    check_edition(fs_path, series_id, cfg_repo, args.library, rep,
                  pr_body_meta=pr_body_meta,
                  today=args.today and _dt.date.fromisoformat(args.today))


# --------------------------------------------------------------------------- #
# Output / CLI
# --------------------------------------------------------------------------- #

def emit(rep, as_json):
    blocks, warns = rep.blocks, rep.warns
    if as_json:
        print(json.dumps({
            "block_count": len(blocks),
            "warn_count": len(warns),
            "findings": [f.as_dict() for f in rep.findings],
            "notes": rep.notes,
        }, indent=2))
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
    p.add_argument("file", nargs="?", help="edition HTML file (local mode)")
    p.add_argument("--series", help="series id (local mode)")
    p.add_argument("--repo", default=".",
                   help="repo root (local mode: main checkout; PR mode: PR checkout)")
    p.add_argument("--main",
                   help="main checkout for configs/registry (PR mode; "
                        "defaults to --repo)")
    p.add_argument("--library", help="published library state (branch checkout dir)")
    p.add_argument("--pr", action="store_true", help="CI mode")
    p.add_argument("--base", help="PR base ref (pr mode)")
    p.add_argument("--head", default="HEAD", help="PR head ref (pr mode)")
    p.add_argument("--pr-body", help="file containing the PR body (pr mode)")
    p.add_argument("--today", help="override today's date (tests)")
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
        check_edition(args.file, args.series, args.repo, args.library, rep,
                      today=args.today and _dt.date.fromisoformat(args.today))

    # strict promotion for pr mode (series known only after path parse)
    return emit(rep, args.json)


if __name__ == "__main__":
    sys.exit(main())
