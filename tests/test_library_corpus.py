"""The proof, pinned to every article the paper has published.

tests/corpus/ vendors the library of RyanSaxe/the-nightly-build — 36 articles,
verbatim — and the press configs they were published under. Every article runs
through check.py and every finding it raises, at its tier and with its message,
is recorded in corpus/findings.json. A change to the proof that moves a single
finding on a single real article fails here, by name.

The golden file is a record of CURRENT BEHAVIOR, not a claim that these articles
are good. Many of them raise blocks today: the engine has grown checks since they
shipped (source kinds, chrome), and the published HTML predates them. That is the
point. The file says what the proof says today, so that a refactor which changes
what the proof says cannot pass quietly.

Regenerate after an intended behavior change, and read the diff before you commit
it:

    PYTHONPATH=engine:tests uv run python tests/test_library_corpus.py
"""

import contextlib
import difflib
import functools
import io
import json
import os
import pathlib
import tempfile

import check
import pytest
from press import REPO

CORPUS = pathlib.Path(__file__).parent / "corpus"
GOLDEN = CORPUS / "findings.json"

# The day the corpus was vendored. Rolling series slug an article by its UTC date
# and the proof refuses a slug in the future, so an unpinned clock would make this
# suite's verdict depend on the day it runs.
CORPUS_TODAY = "2026-07-14"

# The press replaced its whole lineup on 2026-07-11 (fork commit 3fb7493). The five
# series it retired still have articles in the library, and a series with no config
# is unprovable — the proof can only say B-SERIES about it — so those articles are
# proofed against the press they actually shipped under.
RETIRED_SERIES = frozenset(
    {"docket", "positions", "the-brief", "the-divide", "transformers-from-scratch"}
)

# Only the engine reads the network, and only to check source links. Off, always:
# a golden file whose verdict depends on someone else's server is not a golden file.
CHECK_LINKS = ["--no-check-links"]


def articles() -> list[str]:
    """Every vendored article, as `series/slug`."""
    return sorted(
        f"{path.parent.name}/{path.stem}" for path in CORPUS.glob("library/*/*.html")
    )


@functools.cache
def mounted_repo(press: str) -> str:
    """A repo root the proof can read: this engine, that press.

    The engine and the press live in different repositories — the press is a fork's
    press/ tree — and check.py takes one root. Symlinks join them without copying.
    """
    root = pathlib.Path(tempfile.mkdtemp())
    for name in ("engine", "templates", "spec"):
        os.symlink(REPO / name, root / name)
    os.symlink(CORPUS / press, root / "press")
    return str(root)


@functools.cache
def library_without(article: str) -> str:
    """The published library as it stood the night this article was written.

    The proof reads the library to answer "has this slug already shipped?" and
    "is this sequence in order?", and it answers from file names alone. So the
    library is stubbed: every published slug but this one.
    """
    root = pathlib.Path(tempfile.mkdtemp())
    for other in articles():
        if other == article:
            continue
        path = root / "library" / f"{other}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    return str(root)


def proof(article: str) -> dict:
    """Run the proof over one article exactly as the CLI does, findings and status."""
    series, slug = article.split("/")
    press = "press-retired" if series in RETIRED_SERIES else "press"
    argv = [
        str(CORPUS / "library" / series / f"{slug}.html"),
        "--series",
        series,
        "--repo",
        mounted_repo(press),
        "--library",
        library_without(article),
        "--today",
        CORPUS_TODAY,
        *CHECK_LINKS,
        "--json",
    ]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        status = check.main(argv)
    report = json.loads(out.getvalue())
    return {
        "exit": status,
        "findings": report["findings"],
        "notes": report["notes"],
    }


def as_lines(verdict: dict) -> list[str]:
    """One finding per line, for a diff someone can read at 2am."""
    lines = [f"exit {verdict['exit']}"]
    lines += [
        f"{f['level']:<5} {f['code']:<18} {f['message']}" for f in verdict["findings"]
    ]
    lines += [f"note: {note}" for note in verdict["notes"]]
    return lines


def load_golden() -> dict:
    return json.loads(GOLDEN.read_text())


@pytest.mark.parametrize("article", articles())
def test_the_proof_says_what_it_said_about_a_published_article(article: str) -> None:
    expected = load_golden()[article]
    actual = proof(article)
    if actual == expected:
        return
    diff = difflib.unified_diff(
        as_lines(expected),
        as_lines(actual),
        fromfile=f"{article} (recorded)",
        tofile=f"{article} (now)",
        lineterm="",
    )
    pytest.fail(f"the proof changed on {article}:\n" + "\n".join(diff))


def test_the_golden_file_covers_the_whole_library() -> None:
    assert sorted(load_golden()) == articles()


def record() -> None:
    GOLDEN.write_text(
        json.dumps({article: proof(article) for article in articles()}, indent=2) + "\n"
    )


if __name__ == "__main__":
    record()
