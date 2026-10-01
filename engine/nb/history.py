"""Search published coverage without exposing the raw library.

The site builder already turns article HTML into metadata and clean prose. This
module reuses those readers to provide small, predictable history results for
agents that need continuity or repetition checks without inviting a repository
tour or returning an earlier article's markup. `--structure` is the one
deliberate window onto ordered structure: a bounded outline of headings and
furniture names for repetition checks, still never the markup itself.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser

from nb import meta as nb_meta
from nb.git_handoff import GitHandoffError
from nb.library_checkout import LibraryCheckoutError, ensure_library
from nb.site.library import article_body_html, article_text, read_meta, scan_library

__all__ = (
    "HistoryEntry",
    "HistoryResult",
    "excerpt",
    "format_results",
    "load_entries",
    "main",
    "parser",
    "readable_text",
    "search",
    "structure_outline",
)

DEFAULT_LIMIT = 8
MAX_LIMIT = 20
EXCERPT_LENGTH = 240
BLOCK_TAGS = frozenset(
    {
        "blockquote",
        "dd",
        "div",
        "dt",
        "figcaption",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tr",
        "ul",
    }
)
IGNORED_TAGS = frozenset({"script", "style"})
HEADING_TAGS = frozenset({"h2", "h3"})
# Furniture lives on block components; prose and inline chrome never count.
COMPONENT_TAGS = frozenset({"aside", "blockquote", "div", "dl", "figure", "table"})
CHROME_CLASSES = frozenset(
    {
        "nb-article",
        "nb-cite",
        "nb-dekline",
        "nb-meta",
        "nb-reading",
        "nb-sources",
        "nb-title",
    }
)


@dataclass(frozen=True)
class HistoryEntry:
    series: str
    slug: str
    title: str
    dek: str
    date: str
    tags: tuple[str, ...]
    text: str

    @property
    def reference(self) -> str:
        return f"{self.series}/{self.slug}"


@dataclass(frozen=True)
class HistoryResult:
    reference: str
    title: str
    dek: str
    date: str
    tags: tuple[str, ...]
    match: str | None


class _ReadableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def _line_break(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in IGNORED_TAGS:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag in BLOCK_TAGS:
            self._line_break()

    def handle_endtag(self, tag: str) -> None:
        if tag in IGNORED_TAGS:
            self.ignored_depth = max(0, self.ignored_depth - 1)
        elif not self.ignored_depth and tag in BLOCK_TAGS:
            self._line_break()

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)

    def text(self) -> str:
        lines = (
            re.sub(r"\s+", " ", line).strip()
            for line in "".join(self.parts).splitlines()
        )
        return "\n".join(line for line in lines if line)


@dataclass
class _Section:
    id: str
    heading: str = ""
    furniture: set[str] = field(default_factory=set)


class _StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[_Section] = []
        self._heading: list[str] | None = None
        self._sup_depth = 0

    def _current(self) -> _Section | None:
        return self.sections[-1] if self.sections else None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "section" and attributes.get("data-nb-section"):
            self.sections.append(_Section(id=attributes["data-nb-section"] or ""))
            return
        section = self._current()
        if section is None:
            return
        if tag == "sup":
            self._sup_depth += 1
        elif tag in HEADING_TAGS and not section.heading:
            self._heading = []
        elif tag in COMPONENT_TAGS:
            classes = (attributes.get("class") or "").split()
            section.furniture.update(
                name for name in classes if "-" in name and name not in CHROME_CLASSES
            )

    def handle_endtag(self, tag: str) -> None:
        if tag == "sup":
            self._sup_depth = max(0, self._sup_depth - 1)
        elif tag in HEADING_TAGS and self._heading is not None:
            section = self._current()
            if section is not None:
                section.heading = re.sub(r"\s+", " ", "".join(self._heading)).strip()
            self._heading = None

    def handle_data(self, data: str) -> None:
        if self._heading is not None and not self._sup_depth:
            self._heading.append(data)


def structure_outline(path: pathlib.Path) -> str:
    """Return an article's bounded outline: title, dek, headings, furniture.

    This is the repetition-check window onto structure. It names what the
    article's sections are called and which furniture components each uses,
    and returns none of the markup that carries them.
    """
    source = path.read_text(encoding="utf-8", errors="replace")
    meta = nb_meta.parse_meta(source) or {}
    walker = _StructureParser()
    walker.feed(source)
    lines = [f"# {_string(meta.get('title'))}", "", _string(meta.get("dek")), ""]
    for section in walker.sections:
        lines.append(f"## {section.heading or section.id}")
        if section.furniture:
            lines.append("furniture: " + ", ".join(sorted(section.furniture)))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _string(value: object, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def _tags(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(tag for tag in value if isinstance(tag, str))


def load_entries(library: pathlib.Path) -> list[HistoryEntry]:
    entries: list[HistoryEntry] = []
    for series, slug, path in scan_library(str(library)):
        metadata = read_meta(path)
        if metadata is None:
            continue
        entries.append(
            HistoryEntry(
                series=series,
                slug=slug,
                title=_string(metadata.get("title"), slug),
                dek=_string(metadata.get("dek")),
                date=_string(metadata.get("date")),
                tags=_tags(metadata.get("tags")),
                text=article_text(path),
            )
        )
    return entries


def readable_text(path: pathlib.Path) -> str:
    parser = _ReadableTextParser()
    parser.feed(article_body_html(str(path)))
    parser.close()
    return parser.text()


def _occurrences(text: str, terms: Sequence[str]) -> list[list[tuple[int, int]]]:
    return [
        [(match.start(), match.end()) for match in re.finditer(re.escape(term), text)]
        for term in terms
    ]


def _tightest_span(
    occurrences: Sequence[Sequence[tuple[int, int]]],
) -> tuple[int, int] | None:
    points = sorted(
        (start, end, term_index)
        for term_index, matches in enumerate(occurrences)
        for start, end in matches
    )
    if not points or any(not matches for matches in occurrences):
        return None

    counts = [0] * len(occurrences)
    covered = 0
    left = 0
    best: tuple[int, int] | None = None
    for right, (_, _, term_index) in enumerate(points):
        if counts[term_index] == 0:
            covered += 1
        counts[term_index] += 1
        while covered == len(occurrences):
            start = points[left][0]
            end = max(point[1] for point in points[left : right + 1])
            candidate = (start, end)
            if best is None or candidate[1] - candidate[0] < best[1] - best[0]:
                best = candidate
            left_term = points[left][2]
            counts[left_term] -= 1
            if counts[left_term] == 0:
                covered -= 1
            left += 1
    return best


def excerpt(text: str, terms: Sequence[str]) -> str | None:
    if not terms:
        return None
    folded = text.casefold()
    unique_terms = tuple(dict.fromkeys(term for term in terms if term))
    matches = _occurrences(folded, unique_terms)
    span = _tightest_span(matches)
    if span is None:
        return None

    span_start, span_end = span
    if span_end - span_start > EXCERPT_LENGTH:
        rarest = min(
            (values for values in matches if values), key=lambda values: len(values)
        )
        span_start, span_end = rarest[0]
    spare = max(0, EXCERPT_LENGTH - (span_end - span_start))
    start = max(0, span_start - spare // 3)
    end = min(len(text), start + EXCERPT_LENGTH)
    fragment = re.sub(r"\s+", " ", text[start:end]).strip()
    if start:
        fragment = f"…{fragment}"
    if end < len(text):
        fragment = f"{fragment}…"
    return fragment


def _matching_score(entry: HistoryEntry, terms: Sequence[str]) -> int | None:
    title = entry.title.casefold()
    dek = entry.dek.casefold()
    tags = " ".join(entry.tags).casefold()
    text = entry.text.casefold()
    reference = entry.reference.casefold()
    searchable = "\n".join((reference, title, dek, tags, text))
    if not all(term in searchable for term in terms):
        return None
    return sum(
        (12 if term in title else 0)
        + (7 if term in dek else 0)
        + (5 if term in tags else 0)
        + (3 if term in reference else 0)
        + min(text.count(term), 4)
        for term in terms
    )


def search(
    entries: Sequence[HistoryEntry],
    query: Sequence[str],
    *,
    series: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[HistoryResult]:
    terms = tuple(term.casefold().strip() for term in query if term.strip())
    scored: list[tuple[int, HistoryEntry]] = []
    for entry in entries:
        if series is not None and entry.series != series:
            continue
        score = _matching_score(entry, terms)
        if score is not None:
            scored.append((score, entry))
    scored.sort(
        key=lambda item: (item[0], item[1].date, item[1].reference),
        reverse=True,
    )
    return [
        HistoryResult(
            reference=entry.reference,
            title=entry.title,
            dek=entry.dek,
            date=entry.date,
            tags=entry.tags,
            match=excerpt(entry.text, terms),
        )
        for _score_value, entry in scored[:limit]
    ]


def format_results(results: Sequence[HistoryResult]) -> str:
    if not results:
        return "No matching published coverage."
    lines: list[str] = []
    for result in results:
        date = f" · {result.date}" if result.date else ""
        lines.append(f"{result.reference}{date} · {result.title}")
        if result.dek:
            lines.append(f"  {result.dek}")
        if result.tags:
            lines.append(f"  tags: {', '.join(result.tags)}")
        if result.match:
            lines.append(f"  match: {result.match}")
    return "\n".join(lines)


def _limit(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= MAX_LIMIT:
        raise argparse.ArgumentTypeError(f"limit must be between 1 and {MAX_LIMIT}")
    return parsed


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Search bounded, plain-text records of published coverage"
    )
    command.add_argument(
        "query",
        nargs="*",
        help="terms that must all occur; omit to list recent coverage",
    )
    command.add_argument(
        "--library",
        type=pathlib.Path,
        help="library checkout (defaults to $NB_LIBRARY, else one kept under "
        ".nb-work/ at origin/library)",
    )
    command.add_argument("--series", help="restrict results to one series")
    command.add_argument("--limit", type=_limit, default=DEFAULT_LIMIT)
    command.add_argument(
        "--show",
        metavar="SERIES/SLUG",
        help="print one selected article as clean, grep-friendly text",
    )
    command.add_argument(
        "--structure",
        metavar="SERIES/SLUG",
        help="print one article's outline: title, dek, headings, and the "
        "furniture each section uses",
    )
    return command


def _shown_article(library: pathlib.Path, reference: str) -> pathlib.Path | None:
    series, separator, slug = reference.partition("/")
    if (
        separator != "/"
        or "/" in slug
        or nb_meta.SERIES_RE.fullmatch(series) is None
        or nb_meta.SLUG_RE.fullmatch(slug) is None
    ):
        raise ValueError("expected SERIES/SLUG")
    directory = nb_meta.series_dir(str(library), series)
    if directory is None:
        return None
    article = pathlib.Path(directory) / f"{slug}.html"
    return article if article.is_file() else None


def main(arguments: list[str] | None = None) -> None:
    command = parser()
    options = command.parse_args(arguments)
    if options.library is None:
        configured = os.getenv("NB_LIBRARY")
        try:
            options.library = (
                pathlib.Path(configured) if configured else ensure_library()
            )
        except LibraryCheckoutError as error:
            raise SystemExit(f"nb history: {error}") from error
        except GitHandoffError as error:
            raise SystemExit(error.emit()) from error
    if options.structure:
        if options.query or options.series or options.show:
            command.error(
                "--structure cannot be combined with a query, --series, or --show"
            )
        try:
            article = _shown_article(options.library, options.structure)
        except ValueError as error:
            command.error(str(error))
        if article is None:
            raise SystemExit(f"published article not found: {options.structure}")
        print(structure_outline(article), end="")
        return
    if options.show:
        if options.query or options.series:
            command.error("--show cannot be combined with a query or --series")
        try:
            article = _shown_article(options.library, options.show)
        except ValueError as error:
            command.error(str(error))
        if article is None:
            raise SystemExit(f"published article not found: {options.show}")
        print(readable_text(article))
        return
    results = search(
        load_entries(options.library),
        options.query,
        series=options.series,
        limit=options.limit,
    )
    print(format_results(results))


if __name__ == "__main__":
    main()
