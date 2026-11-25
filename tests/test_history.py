"""Bounded history queries reuse published article parsing without raw access.

The fixtures contain tempting structural labels and markup to prove that query
results expose only clean prose excerpts and metadata. Search behavior stays
deliberately small: all supplied terms must match, limits are strict, and an
empty query is just a recency listing. `--structure` is the one deliberate
window onto ordered structure: an outline of headings and furniture names for
repetition checks, still never the markup itself.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

from nb.history import EXCERPT_LENGTH, HistoryEntry, excerpt, format_results, search
from press import REPO, git_executable

if TYPE_CHECKING:
    import pathlib


def test_search_requires_every_term_and_ranks_titles_first() -> None:
    entries = [
        HistoryEntry(
            series="the-wire",
            slug="older",
            title="Chip market",
            dek="Demand changed",
            date="2026-07-01",
            tags=("markets",),
            text="Capacity rose after a long shortage.",
        ),
        HistoryEntry(
            series="the-wire",
            slug="newer",
            title="Capacity changed",
            dek="The chip market adjusted",
            date="2026-07-02",
            tags=("markets",),
            text="Supply caught demand.",
        ),
        HistoryEntry(
            series="the-wire",
            slug="irrelevant",
            title="Chip design",
            dek="A different subject",
            date="2026-07-03",
            tags=("markets",),
            text="No discussion of output.",
        ),
    ]

    results = search(entries, ["chip", "capacity"])

    assert [result.reference for result in results] == [
        "the-wire/newer",
        "the-wire/older",
    ]


def test_search_is_bounded_and_series_scoped() -> None:
    entries = [
        HistoryEntry(
            series="other" if index == 3 else "the-wire",
            slug=str(index),
            title="Shared topic",
            dek="",
            date=f"2026-07-{index:02d}",
            tags=("markets",),
            text="Shared evidence.",
        )
        for index in range(1, 6)
    ]

    results = search(entries, ["shared"], series="the-wire", limit=2)

    assert [result.reference for result in results] == [
        "the-wire/5",
        "the-wire/4",
    ]


def test_output_contains_no_markup_or_ordered_structure() -> None:
    result = search(
        [
            HistoryEntry(
                series="the-wire",
                slug="verdict",
                title="A finding",
                dek="What changed",
                date="2026-07-01",
                tags=("markets",),
                text="Verdict The evidence marker appears here without markup.",
            )
        ],
        ["marker"],
    )[0]

    rendered = format_results([result])

    assert "<section" not in rendered
    assert "data-nb-section" not in rendered
    assert result.match is not None
    assert len(result.match) <= EXCERPT_LENGTH + 2


def test_excerpt_uses_the_tightest_relevant_passage() -> None:
    text = (
        "Capacity appears in an unrelated introduction. "
        + "filler " * 80
        + "The margin discussion connects capacity directly to pricing."
    )

    match = excerpt(text, ["capacity", "margin"])

    assert match is not None
    assert "margin discussion connects capacity" in match
    assert "unrelated introduction" not in match


def write_article(library: pathlib.Path, *, series: str, slug: str, title: str, text: str) -> None:
    target = library / "library" / series / f"{slug}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        '<script type="application/json" id="nb-meta">'
        + json.dumps(
            {
                "series": series,
                "slug": slug,
                "title": title,
                "dek": "A concise description",
                "date": "2026-07-28",
                "tags": ["test"],
            }
        )
        + f"</script><body><h2>Verdict</h2><p>{text}</p></body>"
    )


def test_nb_history_reads_the_library_without_returning_html(
    tmp_path: pathlib.Path,
) -> None:
    write_article(
        tmp_path,
        series="the-wire",
        slug="example",
        title="A searchable title",
        text="The unmistakable needle belongs to this article.",
    )

    result = subprocess.run(
        [
            str(REPO / "nb"),
            "history",
            "needle",
            "--library",
            str(tmp_path),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "the-wire/example" in result.stdout
    assert "The unmistakable needle belongs to this article." in result.stdout
    assert "<h2>" not in result.stdout


def test_nb_history_show_returns_readable_blocks_for_grep(
    tmp_path: pathlib.Path,
) -> None:
    write_article(
        tmp_path,
        series="the-wire",
        slug="example",
        title="A searchable title",
        text=(
            "First paragraph with a needle.</p><script>secret()</script>"
            '<section class="nb-note"><h2>Useful heading</h2><p>'
            "Second paragraph with margin evidence."
        ),
    )

    result = subprocess.run(
        [
            str(REPO / "nb"),
            "history",
            "--show",
            "the-wire/example",
            "--library",
            str(tmp_path),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "First paragraph with a needle." in result.stdout
    assert "Useful heading\nSecond paragraph with margin evidence." in result.stdout
    assert "secret" not in result.stdout
    assert "<section" not in result.stdout
    assert "nb-note" not in result.stdout


def test_nb_history_structure_outlines_headings_and_furniture(
    tmp_path: pathlib.Path,
) -> None:
    target = tmp_path / "library" / "the-wire" / "furnished.html"
    target.parent.mkdir(parents=True)
    meta = json.dumps(
        {
            "series": "the-wire",
            "slug": "furnished",
            "title": "The Wires Between the Chips",
            "dek": "How links move bits",
            "date": "2026-07-28",
            "tags": ["test"],
        }
    )
    target.write_text(
        f'<script type="application/json" id="nb-meta">{meta}</script>'
        '<body class="nb-article">'
        '<section data-nb-section="orientation">'
        '<h2>Why links matter<sup class="nb-cite"><a href="#s1">1</a></sup></h2>'
        '<p>Prose with a cite<sup class="nb-cite"><a href="#s1">1</a></sup>.</p>'
        '<figure class="nb-math"><code>E = mc^2</code></figure>'
        '<div class="nb-verdict-card">holds up</div></section>'
        '<section data-nb-section="sources"><h2>Sources</h2>'
        "<ol><li>one</li></ol></section>"
        "</body>"
    )

    result = subprocess.run(
        [
            str(REPO / "nb"),
            "history",
            "--structure",
            "the-wire/furnished",
            "--library",
            str(tmp_path),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "# The Wires Between the Chips" in result.stdout
    assert "How links move bits" in result.stdout
    assert "## Why links matter" in result.stdout
    assert "furniture: nb-math, nb-verdict-card" in result.stdout
    assert "## Sources" in result.stdout
    assert result.stdout.count("furniture:") == 1
    assert "<" not in result.stdout
    assert "nb-cite" not in result.stdout


def test_nb_history_structure_rejects_an_unknown_reference(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "library").mkdir()

    result = subprocess.run(
        [
            str(REPO / "nb"),
            "history",
            "--structure",
            "the-wire/missing",
            "--library",
            str(tmp_path),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "published article not found" in result.stderr


def test_nb_history_show_rejects_search_arguments(tmp_path: pathlib.Path) -> None:
    result = subprocess.run(
        [
            str(REPO / "nb"),
            "history",
            "needle",
            "--show",
            "the-wire/example",
            "--library",
            str(tmp_path),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--show cannot be combined with a query or --series" in result.stderr


def test_nb_history_keeps_its_own_library_checkout_by_default(
    tmp_path: pathlib.Path,
) -> None:
    # no --library and no NB_LIBRARY: the engine fetches origin/library itself
    git_bin = git_executable()
    seed = tmp_path / "seed"
    write_article(
        seed,
        series="the-wire",
        slug="example",
        title="A searchable title",
        text="The unmistakable needle belongs to this article.",
    )
    subprocess.run([git_bin, "init", "-q", "-b", "library"], cwd=seed, check=True)
    subprocess.run(
        [git_bin, "-c", "user.name=t", "-c", "user.email=t@example.com", "add", "-A"],
        cwd=seed,
        check=True,
    )
    subprocess.run(
        [
            git_bin,
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-qm",
            "seed",
        ],
        cwd=seed,
        check=True,
    )
    origin = tmp_path / "origin.git"
    subprocess.run([git_bin, "clone", "-q", "--bare", str(seed), str(origin)], check=True)
    root = tmp_path / "root"
    root.mkdir()
    subprocess.run([git_bin, "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run([git_bin, "remote", "add", "origin", str(origin)], cwd=root, check=True)
    environment = {key: value for key, value in os.environ.items() if key != "NB_LIBRARY"}
    environment.update({"NB_ROOT": str(root), "PYTHONPATH": str(REPO / "engine")})

    result = subprocess.run(
        [sys.executable, str(REPO / "engine" / "nb" / "history.py"), "needle"],
        cwd=root,
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "the-wire/example" in result.stdout
    assert (root / ".nb-work" / "library" / "library" / "the-wire").is_dir()
