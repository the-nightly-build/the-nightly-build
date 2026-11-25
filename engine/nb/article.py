"""The structural parse of one article file, which every check reads.

One HTMLParser walk collects everything the proof needs — sections, items,
rubric rows, citations, source entries, sandbox violations, figures, word
counts — so no check re-parses the file or disagrees with another about
what it contains. html.parser is tolerant by design: malformed markup
degrades into text instead of raising, and the structural checks downstream
decide what matters. Nothing here judges; this module only observes.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import TYPE_CHECKING, TypedDict

from nb import meta as nb_meta

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = (
    "Article",
    "FigureEntry",
    "ImageEntry",
    "ItemEntry",
    "RubricRow",
    "SourceEntry",
    "collapse_space",
)


class FigureEntry(TypedDict):
    cites: list[str]


class ImageEntry(TypedDict):
    src: str
    alt: str
    figure: FigureEntry | None


class ItemEntry(TypedDict):
    cites: list[str]


class RubricRow(TypedDict):
    criterion: str
    score: str | None
    cites: list[str]
    score_text_parts: list[str]


class SourceEntry(TypedDict):
    href: str
    required: str | None
    kind: str | None
    id: str | None


class _StackFrame(TypedDict, total=False):
    tag: str
    id: str | None
    figure: FigureEntry
    section: str
    item: int
    rubric: int
    rubric_score: bool
    cite_sup: bool
    dekline: bool


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

SENTENCE_BREAK_TAGS = {
    "article",
    "aside",
    "body",
    "blockquote",
    "br",
    "dd",
    "div",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "head",
    "header",
    "html",
    "li",
    "main",
    "nav",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "title",
    "tr",
    "ul",
}

# These elements contain authored material the sentence-density heuristic
# cannot fairly judge: code, quotations, and machine-rendered payloads.
SENTENCE_SKIP_TAGS = {
    "blockquote",
    "code",
    "math",
    "noscript",
    "pre",
    "q",
    "script",
    "style",
    "svg",
}


def collapse_space(text: str) -> str:
    """Normalize authored HTML text to one space between non-whitespace tokens.

    The parser, metadata checks, and prose checks use this operation as shared
    vocabulary. Keeping it named prevents those consumers from drifting into
    subtly different whitespace rules while preserving empty-string behavior.
    """
    return " ".join(text.split())


class Article(HTMLParser):
    """Single-pass structural parse of one article file.

    Collects everything the checks need in one HTMLParser walk:
    sections, script tags, sandbox violations, citations, source
    entries, and word counts. html.parser is tolerant by
    design, so malformed markup degrades into text instead of raising;
    the structural checks downstream catch what matters.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[_StackFrame] = []  # list of dicts per open element
        self.meta_raw: str | None = None
        self.meta_count = 0  # number of #nb-meta blocks; >1 is a violation
        self.script_tags: list[dict[str, str]] = []  # (attrs_dict) for every <script>
        self.sections: list[str] = []  # data-nb-section values in order
        self.section_cites: dict[str, int] = {}  # section -> inline cite count
        # section -> class -> elements carrying that class. Template manifests
        # may require component furniture inside every flexible section.
        self.section_class_counts: dict[str, dict[str, int]] = {}
        self.items: list[ItemEntry] = []  # per data-nb-item: {"cites": [source entry id, ...]}
        # per data-nb-criterion row: criterion slug, data-score attribute,
        # cites inside the row, and the rendered text of its nb-rubric-score
        self.rubric_rows: list[RubricRow] = []
        self.ids: set[str] = set()
        self.source_container_ids: set[str] = set()
        self.source_ids: list[str] = []  # source entry ids in declaration order
        self.sources: list[SourceEntry] = []  # {"href":, "required":, "kind":, "id":}
        self.cite_hrefs: list[str] = []  # hrefs of anchors inside sup.nb-cite
        self.bad_event_attrs: list[tuple[str, str]] = []
        self.bad_js_urls: list[tuple[str, str]] = []
        self.forbidden_tags: list[str] = []
        self.external_refs: list[tuple[str, str]] = []  # (tag, url) for script src / link href / img src
        self.images: list[ImageEntry] = []  # {src, alt, figure}; local article-figure candidates
        self._capture: tuple[str, list[str]] | None = None  # ("meta", buffer) while inside the nb-meta script
        self._dek_parts: list[str] | None = None  # text of the first .nb-dekline; None until one opens
        self.text_parts: list[str] = []
        self.prose_text_parts: list[str] = []  # body prose only, excludes the sources section
        self.sentence_text_parts: list[str] = []  # prose eligible for sentence-quality checks
        self._suppress_text_depth = 0  # inside script/style
        self._sentence_skip_depth = 0

    # -- helpers -------------------------------------------------------------
    def _attrs(self, attrs: Sequence[tuple[str, str | None]]) -> dict[str, str]:
        return {(k or "").lower(): (v if v is not None else "") for k, v in attrs}

    def _current(self, key: str) -> _StackFrame | None:
        for el in reversed(self.stack):
            if el.get(key) is not None:
                return el
        return None

    def _record_sandbox_attrs(self, tag: str, a: dict[str, str]) -> None:
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

    def _record_media_and_scripts(self, tag: str, a: dict[str, str], *, el: _StackFrame) -> None:
        if tag == "figure" and "nb-figure" in a.get("class", "").split():
            el["figure"] = {"cites": []}
        if tag == "script":
            self.script_tags.append(a)
            src = a.get("src")
            if src:
                self.external_refs.append(("script", src))
            if nb_meta.is_meta_script(a):
                self._capture = ("meta", [])
        if tag == "link" and a.get("href"):
            self.external_refs.append(("link", a["href"]))
        if tag == "img" and a.get("src"):
            self.external_refs.append(("img", a["src"]))
            figure = self._current("figure")
            self.images.append(
                {
                    "src": a["src"],
                    "alt": a.get("alt", ""),
                    "figure": figure["figure"] if figure is not None else None,
                }
            )

    def _record_section_attrs(self, a: dict[str, str], *, el: _StackFrame) -> None:
        classes = set(a.get("class", "").split())
        if "data-nb-section" in a:
            name = a["data-nb-section"]
            self.sections.append(name)
            self.section_cites.setdefault(name, 0)
            self.section_class_counts.setdefault(name, {})
            el["section"] = name
            section_name: str | None = name
        else:
            section = self._current("section")
            section_name = section["section"] if section is not None else None
        if section_name is not None:
            counts = self.section_class_counts.setdefault(section_name, {})
            for class_name in classes:
                counts[class_name] = counts.get(class_name, 0) + 1

    def _record_structure_attrs(self, tag: str, a: dict[str, str], *, el: _StackFrame) -> None:
        self._record_section_attrs(a, el=el)
        if "data-nb-item" in a:
            self.items.append({"cites": []})
            el["item"] = len(self.items) - 1
        if "data-nb-criterion" in a:
            self.rubric_rows.append(
                {
                    "criterion": a["data-nb-criterion"],
                    "score": a.get("data-score"),
                    "cites": [],
                    "score_text_parts": [],
                }
            )
            el["rubric"] = len(self.rubric_rows) - 1
        class_tokens = a.get("class", "").split()
        if "nb-rubric-score" in class_tokens:
            el["rubric_score"] = True
        if tag == "sup" and "nb-cite" in class_tokens:
            el["cite_sup"] = True
        # the class is the whole contract: a press writes its own template and may
        # render the dek in any element, so the tag is not ours to require
        if self._dek_parts is None and "nb-dekline" in class_tokens:
            self._dek_parts = []
            el["dekline"] = True

    def _record_inline_cite(self, target: str) -> None:
        self.cite_hrefs.append(target)
        figure = self._current("figure")
        if figure is not None:
            figure["figure"]["cites"].append(target)
        sec = self._current("section")
        if sec is not None:
            self.section_cites[sec["section"]] = self.section_cites.get(sec["section"], 0) + 1
        it = self._current("item")
        if it is not None:
            self.items[it["item"]]["cites"].append(target)
        row = self._current("rubric")
        if row is not None:
            self.rubric_rows[row["rubric"]]["cites"].append(target)

    def _record_anchor(self, a: dict[str, str]) -> None:
        in_sup = any(e.get("cite_sup") for e in self.stack)
        href = a.get("href", "")
        if in_sup and href.startswith("#"):
            self._record_inline_cite(href[1:])
        if "data-nb-source" not in a:
            return
        nearest: str | None = None
        for e in reversed(self.stack):
            container_id = e.get("id")
            if container_id:
                self.source_container_ids.add(container_id)
                nearest = nearest or container_id
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

    # -- parser events --------------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = self._attrs(attrs)
        el: _StackFrame = {"tag": tag, "id": a.get("id")}

        if tag in SENTENCE_BREAK_TAGS:
            self.sentence_text_parts.append("\n")
        if tag in SENTENCE_SKIP_TAGS:
            self._sentence_skip_depth += 1
        if a.get("id"):
            self.ids.add(a["id"])

        self._record_sandbox_attrs(tag, a)
        self._record_media_and_scripts(tag, a, el=el)
        self._record_structure_attrs(tag, a, el=el)
        if tag == "a":
            self._record_anchor(a)

        if tag in ("script", "style"):
            self._suppress_text_depth += 1
        if tag not in VOID:
            self.stack.append(el)

    def handle_endtag(self, tag: str) -> None:
        if tag in SENTENCE_SKIP_TAGS:
            self._sentence_skip_depth = max(0, self._sentence_skip_depth - 1)
        if tag in SENTENCE_BREAK_TAGS:
            self.sentence_text_parts.append("\n")
        if tag in ("script", "style"):
            self._suppress_text_depth = max(0, self._suppress_text_depth - 1)
            if tag == "script" and self._capture:
                _, buf = self._capture
                self.meta_count += 1
                if self.meta_raw is None:
                    # keep the FIRST block — the browser (getElementById) and
                    # build_site/duty (first regex match) all read the first
                    self.meta_raw = "".join(buf)
                self._capture = None
        # pop to matching tag (tolerant of minor nesting slips)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].get("tag") == tag:
                del self.stack[i:]
                return

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._capture[1].append(data)
        elif self._suppress_text_depth == 0:
            self.text_parts.append(data)
            sec = self._current("section")
            if sec is None or sec.get("section") != "sources":
                self.prose_text_parts.append(data)
                if self._sentence_skip_depth == 0:
                    self.sentence_text_parts.append(collapse_space(data))
            if self._dek_parts is not None and self._current("dekline") is not None:
                self._dek_parts.append(data)
            if self._current("rubric_score") is not None:
                row = self._current("rubric")
                if row is not None:
                    self.rubric_rows[row["rubric"]]["score_text_parts"].append(data)

    @property
    def word_count(self) -> int:
        text = " ".join(self.text_parts)
        return len(re.findall(r"\S+", text))

    @property
    def dekline(self) -> str:
        """The rendered dek text, whitespace-normalized for comparison.

        Joins the captured fragments on a space so a tag boundary (a <br>,
        an <em>) never fuses two words, then collapses runs — the proof
        compares this against nb-meta's dek, which is plain text.
        """
        return collapse_space(" ".join(self._dek_parts or []))
