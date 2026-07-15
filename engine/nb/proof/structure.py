"""The shape of the page: its sections, its chrome, its classes, its sandbox."""

import json
import os
import re
import struct

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
# Classes styled by owner-declared external assets (docs/customization.md's
# syntax-highlighter recipe), so no shipped stylesheet defines them.
CLASS_ALLOW_PREFIXES = ("language-", "token")


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
    seen = set()
    for image in ed.images:
        figure = image["figure"]
        if figure is None:
            rep.block("B-FIGURE", "images must sit inside figure.nb-figure")
            continue
        key = id(figure)
        if key not in seen:
            seen.add(key)
            if not any(cite in ed.source_container_ids for cite in figure["cites"]):
                rep.block(
                    "B-FIGURE", "each figure needs a caption citation to a source entry"
                )
        src = image["src"]
        if not expected.fullmatch(src):
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


def css_class_names(repo):
    sheets = [os.path.join(repo, "engine", "assets", "nb.css")]
    # The page loads exactly nb.css plus theme.css, and nb/site owns what
    # concatenates into theme.css; asking it keeps this list from drifting.
    sheets += css_owners(repo, load_site_config(repo))
    names = set()
    for path in sheets:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                names.update(re.findall(r"\.([A-Za-z_][\w-]*)", fh.read()))
    return names


def check_classes(raw, *, repo, rep):
    defined = css_class_names(repo)
    if not defined:
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


def check_chrome(raw, *, treg, rep):
    for piece in treg.get("chrome") or []:
        if piece not in raw:
            rep.block(
                "B-CHROME",
                f"fixed chrome missing or altered: {piece!r}. The skeleton's "
                "chrome belongs to the template; fill the placeholders and "
                "leave the chrome exactly as shipped.",
            )
