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

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import itertools
import pathlib
import re
import struct
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING

import tinycss2
import tinycss2.ast

from nb.site.assets import css_owners, nb_css_sources
from nb.site.library import load_site_config

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from io import BufferedReader

    from nb.article import Article, ImageEntry
    from nb.report import Report

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
NESTED_RULE_AT_RULES = frozenset({"container", "document", "keyframes", "layer", "media", "scope", "supports"})
_EXTERNAL_CSS_CACHE: dict[tuple[str, str], tuple[frozenset[str], bool, str | None]] = {}

MAX_FIGURE_BYTES = 2 * 1024 * 1024
MAX_FIGURE_EDGE = 2400
PNG_MIN_HEADER = 24
WEBP_MIN_HEADER = 30
VP8L_MIN_HEADER = 25
VP8L_SIGNATURE = 0x2F
JPEG_MARKER_PREFIX = 0xFF
JPEG_MARKER_LEN = 2
JPEG_SOF_PREFIX_LEN = 3
JPEG_SOF_MARKERS = frozenset(
    (
        *range(0xC0, 0xC4),
        *range(0xC5, 0xC8),
        *range(0xC9, 0xCC),
        *range(0xCD, 0xD0),
    )
)
FLEX_BAND_LEN = 2


def external_ref_allowed(normalized_url: str) -> bool:
    """Return whether an off-origin link/img reference may load.

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


def _flex_band(treg: Mapping[str, object]) -> tuple[int, int]:
    raw_bands = treg.get("bands")
    if isinstance(raw_bands, dict):
        flex = raw_bands.get("flex_sections")
        if (
            isinstance(flex, list)
            and len(flex) == FLEX_BAND_LEN
            and isinstance(flex[0], int)
            and isinstance(flex[1], int)
        ):
            return flex[0], flex[1]
    return 0, 0


def _check_flex_components(
    ed: Article,
    *,
    extras: Sequence[str],
    treg: Mapping[str, object],
    rep: Report,
) -> None:
    raw_components = treg.get("flex_components")
    if not isinstance(raw_components, list):
        return
    components = [str(item) for item in raw_components]
    for section in extras:
        counts = ed.section_class_counts.get(section, {})
        for component in components:
            count = counts.get(component, 0)
            if count != 1:
                rep.block(
                    "B-FURNITURE",
                    f"flexible section '{section}' contains {count} elements with "
                    f"class '{component}'; it must contain exactly one",
                )


def check_required_sections(ed: Article, treg: Mapping[str, object], *, rep: Report) -> None:
    raw_sections = treg.get("sections")
    required_sections = [str(s) for s in raw_sections] if isinstance(raw_sections, list) else []
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
    low, high = _flex_band(treg)
    extras = [s for s in ed.sections if s not in required_sections]
    dupes = sorted({s for s in extras if extras.count(s) > 1})
    if dupes:
        rep.block("B-HTML", f"duplicate section labels: {dupes}")
    if not (low <= len(extras) <= high):
        rep.block(
            "B-HTML",
            f"{len(extras)} sections beyond the anchors; this template expects between {low} and {high}",
        )
    _check_flex_components(ed, extras=extras, treg=treg, rep=rep)


def _check_script_tag(attrs: Mapping[str, str], rep: Report) -> None:
    stype = (attrs.get("type") or "").strip().lower()
    src = attrs.get("src", "")
    if src and ENGINE_SCRIPT_RE.match(src) and stype in ("", "text/javascript"):
        return  # the engine-owned runtime (assets/nb.js) is the one allowed load
    if stype != "application/json":
        rep.block(
            "B-SANDBOX",
            f"articles may not contain executable <script> (type={stype or 'none'})",
        )
    elif "data-nb-chart" in attrs:
        rep.block(
            "B-SANDBOX",
            "declarative data-nb-chart charts are retired; render a PNG "
            "with engine/render_chart.py and embed it as a figure "
            "(spec/charts.md)",
        )
    elif attrs.get("id") != "nb-meta":
        rep.block("B-SANDBOX", "JSON <script> blocks must be #nb-meta")
    if src:
        rep.block("B-SANDBOX", "articles may not load external scripts")


def _check_external_refs(ed: Article, rep: Report) -> None:
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


def check_sandbox(ed: Article, rep: Report) -> None:
    for a in ed.script_tags:
        _check_script_tag(a, rep)
    if ed.forbidden_tags:
        rep.block("B-SANDBOX", f"forbidden tags present: {sorted(set(ed.forbidden_tags))}")
    for tag, attr in ed.bad_event_attrs:
        rep.block("B-SANDBOX", f"inline event handler {attr}= on <{tag}>")
    for tag, _url in ed.bad_js_urls:
        rep.block("B-SANDBOX", f"javascript: URL on <{tag}>")
    _check_external_refs(ed, rep)


def _webp_dimensions(raw: bytes) -> tuple[int, int] | None:
    kind = raw[12:16]
    if kind == b"VP8X" and len(raw) >= WEBP_MIN_HEADER:
        return (
            1 + int.from_bytes(raw[24:27], "little"),
            1 + int.from_bytes(raw[27:30], "little"),
        )
    if kind == b"VP8 " and len(raw) >= WEBP_MIN_HEADER:
        width, height = struct.unpack("<HH", raw[26:30])
        return width, height
    if kind == b"VP8L" and len(raw) >= VP8L_MIN_HEADER and raw[20] == VP8L_SIGNATURE:
        return (
            1 + (raw[21] | ((raw[22] & 0x3F) << 8)),
            1 + ((raw[23] << 2) | ((raw[22] & 0xC0) >> 6) | ((raw[24] & 0x0F) << 10)),
        )
    return None


def _next_jpeg_marker(fh: BufferedReader) -> int | None:
    marker = fh.read(JPEG_MARKER_LEN)
    if len(marker) != JPEG_MARKER_LEN or marker[0] != JPEG_MARKER_PREFIX:
        return None
    code = marker[1]
    while code == JPEG_MARKER_PREFIX:
        next_byte = fh.read(1)
        if not next_byte:
            return None
        code = next_byte[0]
    return code


def _jpeg_dimensions(fh: BufferedReader) -> tuple[int, int] | None:
    fh.seek(JPEG_MARKER_LEN)
    while (code := _next_jpeg_marker(fh)) is not None:
        if code in JPEG_SOF_MARKERS:
            if len(fh.read(JPEG_SOF_PREFIX_LEN)) != JPEG_SOF_PREFIX_LEN:
                return None
            height, width = struct.unpack(">HH", fh.read(4))
            return width, height
        length = fh.read(JPEG_MARKER_LEN)
        if len(length) != JPEG_MARKER_LEN:
            return None
        fh.seek(struct.unpack(">H", length)[0] - JPEG_MARKER_LEN, 1)
    return None


def image_dimensions(path: str | pathlib.Path) -> tuple[int, int] | None:
    with pathlib.Path(path).open("rb") as fh:
        raw = fh.read(32)
        if raw.startswith(b"\x89PNG\r\n\x1a\n") and len(raw) >= PNG_MIN_HEADER:
            width, height = struct.unpack(">II", raw[16:24])
            return width, height
        if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
            return _webp_dimensions(raw)
        if raw.startswith(b"\xff\xd8"):
            return _jpeg_dimensions(fh)
    return None


def _check_figure_src(
    src: str,
    *,
    is_chart: bool,
    slug: str,
    parent: pathlib.Path,
    expected: re.Pattern[str],
    chart_expected: re.Pattern[str],
    rep: Report,
) -> bool:
    if is_chart:
        chart_name = chart_expected.fullmatch(src)
        if not chart_name:
            rep.block(
                "B-CHART",
                f"a chart image must be '{slug}/chart-N.png': {src!r}",
            )
            return False
        sibling = parent / slug / f"{chart_name.group(1)}.py"
        if not sibling.is_file():
            rep.block(
                "B-CHART",
                f"chart {src!r} must ship its generating script '{slug}/{chart_name.group(1)}.py' in the bundle",
            )
        return True
    if not expected.fullmatch(src):
        rep.block("B-FIGURE", f"figure image must be local to '{slug}/': {src!r}")
        return False
    return True


def _check_figure_file(image: ImageEntry, *, parent: pathlib.Path, rep: Report) -> None:
    src = image["src"]
    if not image["alt"].strip():
        rep.block("B-FIGURE", f"figure image needs nonempty alt text: {src!r}")
    path = parent / src
    if not path.is_file():
        rep.block("B-FIGURE", f"figure asset is missing: {src!r}")
        return
    if path.stat().st_size > MAX_FIGURE_BYTES:
        rep.block(
            "B-FIGURE",
            f"figure asset exceeds {MAX_FIGURE_BYTES // 1024 // 1024} MiB: {src!r}",
        )
        return
    dimensions = image_dimensions(path)
    if dimensions is None:
        rep.block("B-FIGURE", f"figure asset has an unreadable image header: {src!r}")
    elif max(dimensions) > MAX_FIGURE_EDGE:
        rep.block(
            "B-FIGURE",
            f"figure asset exceeds {MAX_FIGURE_EDGE}px on one edge: {src!r}",
        )


def check_figures(ed: Article, *, html_path: str | pathlib.Path, rep: Report) -> None:
    article_path = pathlib.Path(html_path)
    slug = article_path.stem
    parent = article_path.parent
    expected = re.compile(rf"^{re.escape(slug)}/[a-z0-9][a-z0-9._-]*\.(?:png|jpe?g|webp)$")
    # One figure component; the filename carries the contract. chart-N.* is
    # the reserved name for a generated chart, which must ship its committed
    # script; any other name is a captured source asset.
    chart_expected = re.compile(rf"^{re.escape(slug)}/(chart-\d+)\.png$")
    chart_named = re.compile(rf"^{re.escape(slug)}/chart-")
    seen: set[int] = set()
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
        if not _check_figure_src(
            src,
            is_chart=is_chart,
            slug=slug,
            parent=parent,
            expected=expected,
            chart_expected=chart_expected,
            rep=rep,
        ):
            continue
        _check_figure_file(image, parent=parent, rep=rep)


def check_cites(ed: Article, rep: Report) -> None:
    for target in ed.cite_hrefs:
        if target not in ed.ids:
            rep.block("B-CITES-RESOLVE", f"inline citation '#{target}' resolves to nothing")
        elif target not in ed.source_container_ids:
            rep.block(
                "B-CITES-RESOLVE",
                f"inline citation '#{target}' does not point at a source entry",
            )


def _class_names_from_tokens(tokens: Sequence[object]) -> set[str]:
    names: set[str] = set()

    def visit(values: Sequence[object]) -> None:
        for previous, current in itertools.pairwise(values):
            if (
                getattr(previous, "type", None) == "literal"
                and getattr(previous, "value", None) == "."
                and getattr(current, "type", None) == "ident"
            ):
                ident = getattr(current, "value", None)
                if isinstance(ident, str):
                    names.add(ident)
        for value in values:
            content = getattr(value, "content", None)
            if content is None:
                content = getattr(value, "arguments", None)
            if isinstance(content, list):
                visit(content)

    visit(tokens)
    return names


def _parse_css_classes(raw: str) -> tuple[set[str], bool]:
    names: set[str] = set()
    complete = True

    def visit(rules: Sequence[object]) -> None:
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


def _integrity_matches(raw: bytes, integrity: str) -> bool:
    match = re.fullmatch(r"(sha256|sha384|sha512)-([A-Za-z0-9+/]+={0,2})", integrity)
    if not match:
        return False
    digest = hashlib.new(match.group(1), raw).digest()
    try:
        expected = base64.b64decode(match.group(2), validate=True)
    except binascii.Error:
        return False
    return hmac.compare_digest(digest, expected)


def _fetch_stylesheet_bytes(url: str) -> bytes:
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme == "file":
        with pathlib.Path(urllib.request.url2pathname(parsed.path)).open("rb") as fh:
            return fh.read(EXTERNAL_CSS_MAX_BYTES + 1)
    if scheme != "https":
        msg = "external stylesheet URL must use https"
        raise ValueError(msg)
    request = urllib.request.Request(url, headers={"User-Agent": "nightly-build-proof"})
    with urllib.request.urlopen(request, timeout=EXTERNAL_CSS_TIMEOUT) as response:
        return response.read(EXTERNAL_CSS_MAX_BYTES + 1)


def _external_css_classes(url: str, integrity: str) -> tuple[frozenset[str], bool, str | None]:
    key = (url, integrity)
    if key in _EXTERNAL_CSS_CACHE:
        return _EXTERNAL_CSS_CACHE[key]
    try:
        raw = _fetch_stylesheet_bytes(url)
        if len(raw) > EXTERNAL_CSS_MAX_BYTES:
            result: tuple[frozenset[str], bool, str | None] = (
                frozenset(),
                False,
                "stylesheet exceeds the proof size limit",
            )
        elif not _integrity_matches(raw, integrity):
            result = frozenset(), False, "SRI verification failed"
        else:
            names, complete = _parse_css_classes(raw.decode("utf-8"))
            result = (
                frozenset(names),
                complete,
                ("stylesheet contains an import or CSS parse error" if not complete else None),
            )
    except (OSError, UnicodeError, ValueError, urllib.error.URLError) as exc:
        result = frozenset(), False, f"could not fetch or parse stylesheet ({exc})"
    _EXTERNAL_CSS_CACHE[key] = result
    return result


def css_class_names(repo: str | pathlib.Path, *, rep: Report | None = None) -> tuple[set[str], bool]:
    """Return CSS class names and whether the inventory is complete.

    Local press stylesheets are parsed directly. Stylesheets in the site's
    SRI-pinned ``assets.styles`` list are fetched, verified, and parsed as
    styles only; scripts never participate in this inventory. A failed fetch,
    bad hash, import, or parse error marks the inventory incomplete so the
    caller can avoid claiming a class is dead when the evidence is partial.
    """
    repo_str = str(repo)
    sheets = list(nb_css_sources(repo_str))
    # The page loads exactly nb.css plus theme.css, and nb/site owns what
    # concatenates into theme.css; asking it keeps this list from drifting.
    sheets += css_owners(repo_str, load_site_config(repo_str))
    names: set[str] = set()
    complete = True
    for raw_path in sheets:
        path = pathlib.Path(raw_path)
        if path.is_file():
            local_names, local_complete = _parse_css_classes(path.read_text(encoding="utf-8"))
            names.update(local_names)
            complete = complete and local_complete
    site = load_site_config(repo_str)
    assets = site.get("assets") or {}
    if not isinstance(assets, dict):
        return names, False
    for item in assets.get("styles") or []:
        url = item.get("url") if isinstance(item, dict) else None
        integrity = item.get("integrity") if isinstance(item, dict) else None
        if not isinstance(url, str) or not isinstance(integrity, str):
            complete = False
            continue
        external_names, external_complete, problem = _external_css_classes(url, integrity)
        names.update(external_names)
        complete = complete and external_complete
        if problem and rep is not None:
            note = f"external stylesheet {url}: {problem}; W-DEAD-CLASS suppressed"
            if note not in rep.notes:
                rep.notes.append(note)
    return names, complete


def check_classes(raw: str, *, repo: str | pathlib.Path, rep: Report) -> None:
    defined, complete = css_class_names(repo, rep=rep)
    if not defined or not complete:
        return
    used: set[str] = set()
    for attr in re.findall(r'class="([^"]+)"', raw):
        used.update(attr.split())
    dead = sorted(c for c in used if c not in defined and not c.startswith(CLASS_ALLOW_PREFIXES))
    if dead:
        rep.warn(
            "W-DEAD-CLASS",
            f"classes matching no stylesheet rule: {dead}; a typo here renders the element unstyled",
        )


def deprecated_classes(repo: str | pathlib.Path) -> dict[str, str | None]:
    """Map each retired class root to its replacement (or None).

    Parsed from the @deprecated markers in the same sheets check_classes reads
    (nb.css plus every css_owner), so the retired set never drifts from the CSS
    that still ships.
    """
    repo_str = str(repo)
    sheets = list(nb_css_sources(repo_str))
    sheets += css_owners(repo_str, load_site_config(repo_str))
    marks: dict[str, str | None] = {}
    for raw_path in sheets:
        path = pathlib.Path(raw_path)
        if path.is_file():
            for root, repl in DEPRECATED_RE.findall(path.read_text(encoding="utf-8")):
                marks[root] = None if repl == "none" else repl
    return marks


def check_deprecated(raw: str, *, repo: str | pathlib.Path, rep: Report) -> None:
    """Block a new article from using a retired component.

    The component's CSS still renders the frozen back-catalog, but the proof
    runs only on the article being authored, never over published ones, so the
    block never breaks the shelf. A class is retired when it equals a marked
    root or is one of its sub-parts (nb-verdict-title under nb-verdict).
    """
    marks = deprecated_classes(repo)
    if not marks:
        return
    used: set[str] = set()
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


def check_chrome(raw: str, *, treg: Mapping[str, object], rep: Report) -> None:
    chrome = treg.get("chrome")
    if not isinstance(chrome, list):
        return
    for piece in chrome:
        if isinstance(piece, str) and piece not in raw:
            rep.block(
                "B-CHROME",
                f"fixed chrome missing or altered: {piece!r}. The skeleton's "
                "chrome belongs to the template; fill the placeholders and "
                "leave the chrome exactly as shipped.",
            )
