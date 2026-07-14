"""What a series lets through: which slug, in which order, on which night.

Mode is the rule that says a collection publishes each item once, a rolling
series publishes tonight's date, a sequence publishes in order, and an open
series publishes whatever it likes until the owner commissions something.
Rhythm is the rule that says whether the series publishes at all tonight.
"""

import datetime as dt
import os
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Callable

import pytest
from findings import Findings
from press import OPEN_YAML, REPO, TODAY, article, brief, mut

VALID = article()
VALID_BRIEF = brief(TODAY)
SEQUENCE = mut('"mode": "collection", "order": null', '"mode": "sequence", "order": 1')
OPEN = (
    VALID.replace(
        '"series": "semiconductors", "slug": "micron",',
        '"series": "wildcard", "slug": "the-cuda-moat",',
    )
    .replace('"mode": "collection"', '"mode": "open"')
    .replace(' data-nb-required="mu-10k-2025"', "")
)
QUEUE_YAML = (
    OPEN_YAML + "items:\n  - {slug: commissioned-piece, title: On Commission}\n"
)


def test_unknown_series_blocks(run_local: Callable[..., Findings]) -> None:
    result = run_local(VALID, "nope")

    assert "B-SERIES" in result.blocks


def test_unconfigured_slug_blocks(run_local: Callable[..., Findings]) -> None:
    result = run_local(
        mut('"slug": "micron"', '"slug": "intel"'), "semiconductors", slug="intel"
    )

    assert "B-SLUG" in result.blocks


def test_collection_already_published_blocks(
    run_local: Callable[..., Findings], make_library: Callable[..., str]
) -> None:
    result = run_local(
        VALID, "semiconductors", library=make_library({"semiconductors": ["micron"]})
    )

    assert "B-MODE" in result.blocks


@pytest.mark.parametrize("slug", ["2027-01-01", "2026-13-99"])
def test_rolling_slug_must_be_a_real_date_not_in_the_future(
    run_local: Callable[..., Findings], slug: str
) -> None:
    result = run_local(VALID_BRIEF.replace(TODAY, slug), "ai-briefs", slug=slug)

    assert "B-SLUG" in result.blocks


def test_tonights_rolling_slug_passes_west_of_utc(testrepo: str) -> None:
    """The proof keeps duty's clock: UTC.

    It used to keep the machine's, so a night shift running west of UTC — after
    its own evening rollover, when the local date is still yesterday — read
    tonight's correct rolling slug as a date in the future and blocked it. TZ
    forces that machine, so the bug is reproducible rather than a thing that
    only bites after 8pm in New York.
    """
    utc_now = dt.datetime.now(dt.timezone.utc).date().isoformat()
    tonight = pathlib.Path(tempfile.mkdtemp()) / "library" / "ai-briefs"
    tonight.mkdir(parents=True)
    (tonight / f"{utc_now}.html").write_text(brief(utc_now))

    run = subprocess.run(
        [
            sys.executable,
            str(REPO / "engine" / "check.py"),
            str(tonight / f"{utc_now}.html"),
            "--series",
            "ai-briefs",
            "--repo",
            testrepo,
            "--no-check-links",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "TZ": "Pacific/Honolulu"},
    )

    assert "B-SLUG" not in run.stdout


def test_rolling_already_published_blocks(
    run_local: Callable[..., Findings], make_library: Callable[..., str]
) -> None:
    result = run_local(
        VALID_BRIEF,
        "ai-briefs",
        slug=TODAY,
        library=make_library({"ai-briefs": [TODAY]}),
    )

    assert "B-MODE" in result.blocks


def test_sequence_first_item_into_an_empty_library_is_block_clean(
    run_local: Callable[..., Findings],
    seq_repo: Callable[[], str],
    make_library: Callable[..., str],
) -> None:
    result = run_local(
        SEQUENCE,
        "semiconductors",
        repo=seq_repo(),
        library=make_library({"semiconductors": []}),
    )

    assert not result.blocks


def test_sequence_wrong_next_item_blocks(
    run_local: Callable[..., Findings],
    seq_repo: Callable[[], str],
    make_library: Callable[..., str],
) -> None:
    result = run_local(
        SEQUENCE,
        "semiconductors",
        repo=seq_repo(),
        library=make_library({"semiconductors": ["micron"]}),
    )

    assert "B-MODE" in result.blocks


def test_sequence_wrong_order_number_blocks(
    run_local: Callable[..., Findings],
    seq_repo: Callable[[], str],
    make_library: Callable[..., str],
) -> None:
    result = run_local(
        mut('"order": 1', '"order": 3', base=SEQUENCE),
        "semiconductors",
        repo=seq_repo(),
        library=make_library({"semiconductors": []}),
    )

    assert "B-MODE" in result.blocks


def test_paused_series_blocks_publication(
    run_local: Callable[..., Findings], patched_repo: Callable[..., str]
) -> None:
    result = run_local(VALID, "semiconductors", repo=patched_repo("paused: true\n"))

    assert "B-SERIES" in result.blocks


@pytest.mark.parametrize(
    ("patch", "series", "valid"),
    [
        ("cadence: weekdays\n", "semiconductors", True),
        ("cadence: [mon, thu]\n", "semiconductors", True),
        ("cadence: fortnightly\n", "semiconductors", False),
        ("selection: random\n", "semiconductors", True),
        ("selection: random\n", "ai-briefs", False),
        ("cadance: daily\n", "semiconductors", False),
    ],
)
def test_rhythm_configuration_validates(
    vc_rc: Callable[[str], int],
    patched_repo: Callable[..., str],
    patch: str,
    series: str,
    valid: bool,
) -> None:
    assert vc_rc(patched_repo(patch, series=series)) == (0 if valid else 1)


def test_open_freestyle_pick_is_block_clean(
    run_local: Callable[..., Findings],
    open_press: Callable[..., str],
    make_library: Callable[..., str],
) -> None:
    result = run_local(
        OPEN,
        "wildcard",
        slug="the-cuda-moat",
        repo=open_press(),
        library=make_library({"wildcard": []}),
    )

    assert not result.blocks


def test_open_duplicate_slug_blocks(
    run_local: Callable[..., Findings],
    open_press: Callable[..., str],
    make_library: Callable[..., str],
) -> None:
    result = run_local(
        OPEN,
        "wildcard",
        slug="the-cuda-moat",
        repo=open_press(),
        library=make_library({"wildcard": ["the-cuda-moat"]}),
    )

    assert "B-MODE" in result.blocks


def test_open_template_outside_the_choice_list_blocks(
    run_local: Callable[..., Findings],
    open_press: Callable[..., str],
    make_library: Callable[..., str],
) -> None:
    result = run_local(
        OPEN,
        "wildcard",
        slug="the-cuda-moat",
        repo=open_press(
            OPEN_YAML.replace("templates: [article, brief]", "templates: [brief]")
        ),
        library=make_library({"wildcard": []}),
    )

    assert "B-META-MATCH" in result.blocks


def test_pending_commission_blocks_a_freestyle_pick(
    run_local: Callable[..., Findings],
    open_press: Callable[..., str],
    make_library: Callable[..., str],
) -> None:
    result = run_local(
        OPEN,
        "wildcard",
        slug="the-cuda-moat",
        repo=open_press(QUEUE_YAML),
        library=make_library({"wildcard": []}),
    )

    assert "B-MODE" in result.blocks


def test_publishing_the_commissioned_item_is_block_clean(
    run_local: Callable[..., Findings],
    open_press: Callable[..., str],
    make_library: Callable[..., str],
) -> None:
    result = run_local(
        OPEN.replace("the-cuda-moat", "commissioned-piece"),
        "wildcard",
        slug="commissioned-piece",
        repo=open_press(QUEUE_YAML),
        library=make_library({"wildcard": []}),
    )

    assert not result.blocks


def test_open_series_with_a_templates_list_validates(
    vc_rc: Callable[[str], int], open_press: Callable[..., str]
) -> None:
    assert vc_rc(open_press()) == 0


def test_templates_on_a_non_open_series_is_rejected(
    vc_rc: Callable[[str], int], patched_repo: Callable[..., str]
) -> None:
    assert vc_rc(patched_repo("templates: [article]\n")) == 1


def test_open_mode_without_any_template_is_rejected(
    vc_rc: Callable[[str], int], open_press: Callable[..., str]
) -> None:
    repo = open_press(OPEN_YAML.replace("templates: [article, brief]\n", ""))

    assert vc_rc(repo) == 1
