"""The shape of the page: its sections, its chrome, its classes, its sandbox.

These checks read the single Article parse and hold the page to its
mechanical contract: the template's declared sections and chrome survive,
every class resolves to a shipped stylesheet, figures are local, sized, and
cited (source assets under B-FIGURE, generated charts under B-CHART with
their committed script), citations resolve to source entries, and nothing
executable or off-origin gets in. The sandbox rules are the auto-merge
security boundary — an article PR merges untrusted, so anything an attacker
could smuggle through markup must be ruled out here, not reviewed later.
"""

__all__ = (
    "check_chrome",
    "check_cites",
    "check_classes",
    "check_deprecated",
    "check_figures",
    "check_required_sections",
    "check_sandbox",
    "css_class_names",
    "deprecated_classes",
    "external_ref_allowed",
    "image_dimensions",
)

import base64
import binascii
import hashlib
import hmac
import os
import re
import struct
import urllib.error
import urllib.request

import tinycss2
import tinycss2.ast

from nb.report import Report
from nb.site.assets import css_owners
from nb.site.library import load_site_config

# Off-origin stylesheet references may load only from Google Fonts over https.
# Matched by exact host after browser-style normalization, never by string
# prefix — "fonts.googleapis.com.evil.example" and userinfo tricks defeat prefix
# matching but not a real host comparison.
ALLOWED_EXTERNAL_HOSTS = frozenset({"fonts.googleapis.com", "fonts.gstatic.com"})
# The one executable script an article may load: the engine-owned runtime
# (§7.4 — contextual nav + chart renderer), by relative or root-absolute path.
ENGINE_SCRIPT_RE = re.compile(r"^(?:(?:\.\./)+|/)assets/nb\.js$")
# Classes styled by owner-declared external assets (docs/reference/site.md's
# syntax-highlighter recipe), so no shipped stylesheet defines them.
CLASS_ALLOW_PREFIXES = ("language-", "token")
# A retired component leaves its CSS in place so the frozen back-catalog keeps
# rendering, and marks itself here for the proof to block in new articles:
#   /* @deprecated nb-verdict -> nb-note: reason */   (replacement, or `none`)
# The marker lives beside the CSS it guards, so retirement declares itself in
# one place and the block can point the author at the live component.
DEPRECATED_RE = re.compile(r"@deprecated\s+([\w-]+)\s*->\s*([\w-]+|none)")
EXTERNAL_CSS_MAX_BYTES = 4 * 1024 * 1024
EXTERNAL_CSS_TIMEOUT = 10
NESTED_RULE_AT_RULES = frozenset(
    {"container", "document", "keyframes", "layer", "media", "scope", "supports"}
)
_EXTERNAL_CSS_CACHE: dict[tuple[str, str], tuple[frozenset[str], bool, str | None]] = {}


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


def check_required_sections(ed, treg, *, rep):
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
    # Absent bands.flex_sections means a fully fixed outline: no section beyond
    # the anchors is allowed (V6c). Present it as [0, 0] so extras BLOCK rather
    # than slip through unchecked.
    flex_band = (treg.get("bands") or {}).get("flex_sections") or [0, 0]
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
    for section in extras:
        counts = ed.section_class_counts.get(section, {})
        for component in treg.get("flex_components") or []:
            count = counts.get(component, 0)
            if count != 1:
                rep.block(
                    "B-FURNITURE",
                    f"flexible section '{section}' contains {count} elements with "
                    f"class '{component}'; it must contain exactly one",
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
        elif "data-nb-chart" in a:
            rep.block(
                "B-SANDBOX",
                "declarative data-nb-chart charts are retired; render a PNG "
                "with engine/render_chart.py and embed it as a figure "
                "(spec/charts.md)",
            )
        elif a.get("id") != "nb-meta":
            rep.block("B-SANDBOX", "JSON <script> blocks must be #nb-meta")
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


MAX_FIGURE_BYTES = 2 * 1024 * 1024
MAX_FIGURE_EDGE = 2400


def image_dimensions(path):
    with open(path, "rb") as fh:
        raw = fh.read(32)
        if raw.startswith(b"\x89PNG\r\n\x1a\n") and len(raw) >= 24:
            return struct.unpack(">II", raw[16:24])
        if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP" and len(raw) >= 30:
            kind = raw[12:16]
            if kind == b"VP8X":
                return (
                    1 + int.from_bytes(raw[24:27], "little"),
                    1 + int.from_bytes(raw[27:30], "little"),
                )
            if kind == b"VP8 " and len(raw) >= 30:
                return struct.unpack("<HH", raw[26:30])
            if kind == b"VP8L" and len(raw) >= 25 and raw[20] == 0x2F:
                return (
                    1 + (raw[21] | ((raw[22] & 0x3F) << 8)),
                    1
                    + (
                        (raw[23] << 2)
                        | ((raw[22] & 0xC0) >> 6)
                        | ((raw[24] & 0x0F) << 10)
                    ),
                )
        if raw.startswith(b"\xff\xd8"):
            fh.seek(2)
            while marker := fh.read(2):
                if len(marker) != 2 or marker[0] != 0xFF:
                    return None
                while marker[1] == 0xFF:
                    next_byte = fh.read(1)
                    if not next_byte:
                        return None
                    marker = marker[:1] + next_byte
                if (
                    marker[1] in range(0xC0, 0xC4)
                    or marker[1] in range(0xC5, 0xC8)
                    or marker[1] in range(0xC9, 0xCC)
                    or marker[1] in range(0xCD, 0xD0)
                ):
                    length = fh.read(3)
                    if len(length) != 3:
                        return None
                    height, width = struct.unpack(">HH", fh.read(4))
                    return width, height
                length = fh.read(2)
                if len(length) != 2:
                    return None
                fh.seek(struct.unpack(">H", length)[0] - 2, 1)
    return None


def check_figures(ed, *, html_path, rep):
    slug = os.path.splitext(os.path.basename(html_path))[0]
    parent = os.path.dirname(html_path)
    expected = re.compile(
        rf"^{re.escape(slug)}/[a-z0-9][a-z0-9._-]*\.(?:png|jpe?g|webp)$"
    )
    # One figure component; the filename carries the contract. chart-N.* is
    # the reserved name for a generated chart, which must ship its committed
    # script; any other name is a captured source asset.
    chart_expected = re.compile(rf"^{re.escape(slug)}/(chart-\d+)\.png$")
    chart_named = re.compile(rf"^{re.escape(slug)}/chart-")
    seen = set()
    for image in ed.images:
        figure = image["figure"]
        if figure is None:
            rep.block("B-FIGURE", "images must sit inside figure.nb-figure")
            continue
        src = image["src"]
        is_chart = bool(chart_named.match(src))
        key = id(figure)
        if key not in seen:
            seen.add(key)
            if not any(cite in ed.source_container_ids for cite in figure["cites"]):
                rep.block(
                    "B-CHART" if is_chart else "B-FIGURE",
                    "a chart caption must cite its data source"
                    if is_chart
                    else "each figure needs a caption citation to a source entry",
                )
        if is_chart:
            chart_name = chart_expected.fullmatch(src)
            if not chart_name:
                rep.block(
                    "B-CHART",
                    f"a chart image must be '{slug}/chart-N.png': {src!r}",
                )
                continue
            sibling = os.path.join(parent, slug, f"{chart_name.group(1)}.py")
            if not os.path.isfile(sibling):
                rep.block(
                    "B-CHART",
                    f"chart {src!r} must ship its generating script "
                    f"'{slug}/{chart_name.group(1)}.py' in the bundle",
                )
        elif not expected.fullmatch(src):
            rep.block("B-FIGURE", f"figure image must be local to '{slug}/': {src!r}")
            continue
        if not image["alt"].strip():
            rep.block("B-FIGURE", f"figure image needs nonempty alt text: {src!r}")
        path = os.path.join(parent, src)
        if not os.path.isfile(path):
            rep.block("B-FIGURE", f"figure asset is missing: {src!r}")
            continue
        if os.path.getsize(path) > MAX_FIGURE_BYTES:
            rep.block(
                "B-FIGURE",
                f"figure asset exceeds {MAX_FIGURE_BYTES // 1024 // 1024} MiB: {src!r}",
            )
            continue
        dimensions = image_dimensions(path)
        if dimensions is None:
            rep.block(
                "B-FIGURE", f"figure asset has an unreadable image header: {src!r}"
            )
        elif max(dimensions) > MAX_FIGURE_EDGE:
            rep.block(
                "B-FIGURE",
                f"figure asset exceeds {MAX_FIGURE_EDGE}px on one edge: {src!r}",
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


def _class_names_from_tokens(tokens):
    names = set()

    def visit(values):
        for previous, current in zip(values, values[1:], strict=False):
            if (
                getattr(previous, "type", None) == "literal"
                and getattr(previous, "value", None) == "."
                and getattr(current, "type", None) == "ident"
            ):
                names.add(current.value)
        for value in values:
            content = getattr(value, "content", None)
            if content is None:
                content = getattr(value, "arguments", None)
            if content is not None:
                visit(content)

    visit(tokens)
    return names


def _parse_css_classes(raw):
    names = set()
    complete = True

    def visit(rules):
        nonlocal complete
        for rule in rules:
            if isinstance(rule, tinycss2.ast.ParseError):
                complete = False
            elif isinstance(rule, tinycss2.ast.QualifiedRule):
                names.update(_class_names_from_tokens(rule.prelude))
            elif isinstance(rule, tinycss2.ast.AtRule):
                at_keyword = getattr(rule, "at_keyword", "").lower()
                if at_keyword == "import":
                    complete = False
                if rule.content is not None and at_keyword in NESTED_RULE_AT_RULES:
                    visit(tinycss2.parse_rule_list(rule.content, skip_whitespace=True))

    visit(tinycss2.parse_stylesheet(raw, skip_whitespace=True, skip_comments=True))
    return names, complete


def _integrity_matches(raw, integrity):
    match = re.fullmatch(r"(sha256|sha384|sha512)-([A-Za-z0-9+/]+={0,2})", integrity)
    if not match:
        return False
    digest = hashlib.new(match.group(1), raw).digest()
    try:
        expected = base64.b64decode(match.group(2), validate=True)
    except binascii.Error:
        return False
    return hmac.compare_digest(digest, expected)


def _external_css_classes(url, integrity):
    key = (url, integrity)
    if key in _EXTERNAL_CSS_CACHE:
        return _EXTERNAL_CSS_CACHE[key]
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "nightly-build-proof"}
        )
        with urllib.request.urlopen(request, timeout=EXTERNAL_CSS_TIMEOUT) as response:
            raw = response.read(EXTERNAL_CSS_MAX_BYTES + 1)
        if len(raw) > EXTERNAL_CSS_MAX_BYTES:
            result = frozenset(), False, "stylesheet exceeds the proof size limit"
        elif not _integrity_matches(raw, integrity):
            result = frozenset(), False, "SRI verification failed"
        else:
            names, complete = _parse_css_classes(raw.decode("utf-8"))
            result = (
                frozenset(names),
                complete,
                (
                    "stylesheet contains an import or CSS parse error"
                    if not complete
                    else None
                ),
            )
    except (OSError, UnicodeError, ValueError, urllib.error.URLError) as exc:
        result = frozenset(), False, f"could not fetch or parse stylesheet ({exc})"
    _EXTERNAL_CSS_CACHE[key] = result
    return result


def css_class_names(repo: str, *, rep: Report | None = None) -> tuple[set[str], bool]:
    """Return CSS class names and whether the inventory is complete.

    Local press stylesheets are parsed directly. Stylesheets in the site's
    SRI-pinned ``assets.styles`` list are fetched, verified, and parsed as
    styles only; scripts never participate in this inventory. A failed fetch,
    bad hash, import, or parse error marks the inventory incomplete so the
    caller can avoid claiming a class is dead when the evidence is partial.
    """
    sheets = [os.path.join(repo, "engine", "assets", "nb.css")]
    # The page loads exactly nb.css plus theme.css, and nb/site owns what
    # concatenates into theme.css; asking it keeps this list from drifting.
    sheets += css_owners(repo, load_site_config(repo))
    names = set()
    complete = True
    for path in sheets:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                local_names, local_complete = _parse_css_classes(fh.read())
            names.update(local_names)
            complete = complete and local_complete
    site = load_site_config(repo)
    assets = site.get("assets") or {}
    if not isinstance(assets, dict):
        return names, False
    for item in assets.get("styles") or []:
        url = item.get("url") if isinstance(item, dict) else None
        integrity = item.get("integrity") if isinstance(item, dict) else None
        if not isinstance(url, str) or not isinstance(integrity, str):
            complete = False
            continue
        external_names, external_complete, problem = _external_css_classes(
            url, integrity
        )
        names.update(external_names)
        complete = complete and external_complete
        if problem and rep is not None:
            note = f"external stylesheet {url}: {problem}; W-DEAD-CLASS suppressed"
            if note not in rep.notes:
                rep.notes.append(note)
    return names, complete


def check_classes(raw, *, repo, rep):
    defined, complete = css_class_names(repo, rep=rep)
    if not defined:
        return
    if not complete:
        return
    used = set()
    for attr in re.findall(r'class="([^"]+)"', raw):
        used.update(attr.split())
    dead = sorted(
        c for c in used if c not in defined and not c.startswith(CLASS_ALLOW_PREFIXES)
    )
    if dead:
        rep.warn(
            "W-DEAD-CLASS",
            f"classes matching no stylesheet rule: {dead}; a typo here "
            "renders the element unstyled",
        )


def deprecated_classes(repo):
    """Map each retired class root to its replacement (or None).

    Parsed from the @deprecated markers in the same sheets check_classes reads
    (nb.css plus every css_owner), so the retired set never drifts from the CSS
    that still ships.
    """
    sheets = [os.path.join(repo, "engine", "assets", "nb.css")]
    sheets += css_owners(repo, load_site_config(repo))
    marks = {}
    for path in sheets:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                for root, repl in DEPRECATED_RE.findall(fh.read()):
                    marks[root] = None if repl == "none" else repl
    return marks


def check_deprecated(raw, *, repo, rep):
    """Block a new article from using a retired component.

    The component's CSS still renders the frozen back-catalog, but the proof
    runs only on the article being authored, never over published ones, so the
    block never breaks the shelf. A class is retired when it equals a marked
    root or is one of its sub-parts (nb-verdict-title under nb-verdict).
    """
    marks = deprecated_classes(repo)
    if not marks:
        return
    used = set()
    for attr in re.findall(r'class="([^"]+)"', raw):
        used.update(attr.split())
    for cls in sorted(used):
        root = next((r for r in marks if cls == r or cls.startswith(r + "-")), None)
        if root is None:
            continue
        replacement = marks[root]
        fix = f"use {replacement!r} instead" if replacement else "remove it"
        rep.block(
            "B-DEPRECATED",
            f"{cls!r} is a retired component; {fix}. Retired markup lingers in "
            "the published back-catalog but does not belong in a new article.",
        )


def check_chrome(raw, *, treg, rep):
    for piece in treg.get("chrome") or []:
        if piece not in raw:
            rep.block(
                "B-CHROME",
                f"fixed chrome missing or altered: {piece!r}. The skeleton's "
                "chrome belongs to the template; fill the placeholders and "
                "leave the chrome exactly as shipped.",
            )
