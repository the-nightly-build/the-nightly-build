#!/usr/bin/env python3
"""Write the UTC publication date and computable nb-meta counts.

words, reading_minutes, and sources are properties of the article text, not
editorial decisions. This command computes them with the same parser the
proof uses, rewrites the numbers inside the nb-meta block, and writes the
reading time and date into the standard byline. --revision preserves the date.
The proof's W-SELF-COUNT then verifies instead of policing hand-kept numbers.

Run: python3 engine/stamp.py <article.html>. Exits 0 after writing (or when
already stamped), 2 when the file has no readable nb-meta block or lacks one
of the required date/count keys.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys

from nb import meta as nb_meta
from nb.article import Article
from nb.site.library import WORDS_PER_MINUTE

COUNT_KEY_RE = {
    key: re.compile(rf'("{key}"\s*:\s*)(-?\d+)') for key in ("words", "sources")
}
DATE_KEY_RE = re.compile(r'("date"\s*:\s*)"(?:\\.|[^"\\])*"')
READING_KEY_RE = re.compile(r'("reading_minutes"\s*:\s*)(-?\d+)')
BYLINE_READING_RE = re.compile(
    r'(<div class="nb-byline">\s*<span>)(?:N|\d+) min read(</span>)'
)
BYLINE_DATE_RE = re.compile(
    r'(<div class="nb-byline">\s*<span>[^<]*</span>\s*<span>)[^<]*(</span>)'
)


def computed_counts(source: str) -> dict[str, int]:
    ed = Article()
    ed.feed(source)
    words = ed.word_count
    minutes = max(1, round(words / WORDS_PER_MINUTE)) if words else 1
    return {"words": words, "reading_minutes": minutes, "sources": len(ed.sources)}


def stamp_source(source: str, *, revision: bool = False) -> tuple[str, dict[str, int]]:
    """Return the stamped article text and the counts written into it.

    Raises ValueError when the nb-meta block is absent/unreadable or a count
    key is missing, naming exactly what the writer must repair. Replacement
    preserves formatting and key order. Outside the metadata block, only the
    standard byline's date and reading-time spans can change. Revisions
    preserve the publication date; new articles receive today's UTC date.
    """
    m = nb_meta.META_RE.search(source)
    if m is None or nb_meta.parse_meta(source) is None:
        raise ValueError("no readable nb-meta block; add the template's block first")

    if not revision:
        date = dt.datetime.now(dt.timezone.utc).date().isoformat()
        block, n = DATE_KEY_RE.subn(rf'\g<1>"{date}"', m.group(1), count=1)
        if not n:
            raise ValueError("nb-meta lacks a string date key")
        source = source[: m.start(1)] + block + source[m.end(1) :]
        source = BYLINE_DATE_RE.sub(rf"\g<1>{date}\g<2>", source, count=1)
        m = nb_meta.META_RE.search(source)
        assert m is not None

    counts = computed_counts(source)
    block = source[m.start(1) : m.end(1)]
    missing = []
    for key, pattern in {**COUNT_KEY_RE, "reading_minutes": READING_KEY_RE}.items():
        block, n = pattern.subn(rf"\g<1>{counts[key]}", block, count=1)
        if n == 0:
            missing.append(key)
    if missing:
        raise ValueError(f"nb-meta lacks count keys: {', '.join(sorted(missing))}")
    stamped = source[: m.start(1)] + block + source[m.end(1) :]
    stamped = BYLINE_READING_RE.sub(
        rf"\g<1>{counts['reading_minutes']} min read\g<2>", stamped, count=1
    )
    return stamped, counts


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Write the UTC publication date, article counts, and reading time."
    )
    p.add_argument("file", help="article HTML file to stamp in place")
    p.add_argument(
        "--revision", action="store_true", help="preserve the original publication date"
    )
    args = p.parse_args(argv)

    with open(args.file, encoding="utf-8") as fh:
        source = fh.read()
    try:
        stamped, counts = stamp_source(source, revision=args.revision)
    except ValueError as err:
        sys.stderr.write(f"stamp: {err}\n")
        return 2

    if stamped != source:
        with open(args.file, "w", encoding="utf-8") as fh:
            fh.write(stamped)
    state = "stamped" if stamped != source else "already stamped"
    print(" ".join([state] + [f"{k}={v}" for k, v in counts.items()]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
