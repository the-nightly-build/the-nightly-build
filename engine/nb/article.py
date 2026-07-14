"""The structural parse of one article file, which every check reads."""

import re
from html.parser import HTMLParser

from nb import meta as nb_meta

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


def collapse_space(text: str) -> str:
    return " ".join(text.split())


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
        self.items = []  # per data-nb-item: {"cites": [source entry id, ...]}
        self.ids = set()
        self.source_container_ids = set()
        self.source_ids = []  # source entry ids in declaration order
        self.sources = []  # {"href":, "required":, "kind":, "id":}
        self.cite_hrefs = []  # hrefs of anchors inside sup.nb-cite
        self.bad_event_attrs = []
        self.bad_js_urls = []
        self.forbidden_tags = []
        self.external_refs = []  # (tag, url) for script src / link href / img src
        self._capture = None  # ("meta"|"chart", buffer) while inside a JSON script
        self._dek_parts = None  # text of the first .nb-dekline; None until one opens
        self._text_parts = []
        self._prose_text_parts = []  # body prose only, excludes the sources section
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
            self.items.append({"cites": []})
            el["item"] = len(self.items) - 1

        if tag == "sup" and "nb-cite" in a.get("class", "").split():
            el["cite_sup"] = True

        # the class is the whole contract: a press writes its own template and may
        # render the dek in any element, so the tag is not ours to require
        if self._dek_parts is None and "nb-dekline" in a.get("class", "").split():
            self._dek_parts = []
            el["dekline"] = True

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
                    self.items[it["item"]]["cites"].append(href[1:])
            if "data-nb-source" in a:
                nearest = None
                for e in reversed(self.stack):
                    if e.get("id"):
                        self.source_container_ids.add(e["id"])
                        nearest = nearest or e["id"]
                self.sources.append(
                    {
                        "href": href,
                        "required": a.get("data-nb-required") or None,
                        "kind": a.get("data-nb-kind") or None,
                        "id": nearest,
                    }
                )
                if nearest and nearest not in self.source_ids:
                    self.source_ids.append(nearest)

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
            sec = self._current("section")
            if sec is None or sec.get("section") != "sources":
                self._prose_text_parts.append(data)
            if self._dek_parts is not None and self._current("dekline") is not None:
                self._dek_parts.append(data)

    @property
    def word_count(self):
        text = " ".join(self._text_parts)
        return len(re.findall(r"\S+", text))

    @property
    def dekline(self) -> str:
        # the space keeps a tag boundary (a <br>, an <em>) from fusing two words
        return collapse_space(" ".join(self._dek_parts or []))
