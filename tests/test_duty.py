"""Tonight's work list: what publishes, what idles, and when duty refuses to answer.

duty.py decides whether a series publishes tonight. Every branch of that
decision is a night the paper either ships or stays quiet, so the work list is
asserted whole: the due entry, the idle reason, the candidates. Malformed
configuration idles one series and never takes down the run. A tree that is not
a press is not a quiet night — it exits 2 and prints nothing, because a run once
read an empty work list as permission to go find a configuration of its own.
"""

import json
import pathlib
import shutil
import subprocess
import tempfile
from collections.abc import Callable

import pytest
from press import OPEN_YAML, REPO, TODAY, article, git

QUEUE_YAML = (
    OPEN_YAML + "items:\n  - {slug: commissioned-piece, title: On Commission}\n"
)
COLLECTION_MISSING_SLUG = (
    "name: Test\nmode: collection\ntemplate: article\n"
    "items:\n  - {slug: alpha}\n  - {title: no-slug-here}\n  - {slug: beta}\n"
)


def duty_of(report: dict, series: str) -> dict:
    """The series' entry in tonight's work list, due or idle. Absence is a failure."""
    entries = report["due"] + report["idle"]
    matched = [entry for entry in entries if entry["series"] == series]
    assert matched, f"{series} is in neither due nor idle: {report}"
    return matched[0]


@pytest.fixture
def empty_lib(make_library: Callable[..., str]) -> str:
    return make_library({"semiconductors": [], "ai-briefs": []})


def test_rolling_series_is_due_tonight_with_tonights_slug(
    duty: Callable[..., dict], testrepo: str, empty_lib: str
) -> None:
    report = duty(testrepo, empty_lib)

    assert duty_of(report, "ai-briefs") in report["due"]
    assert duty_of(report, "ai-briefs")["slug"] == TODAY


def test_rolling_already_published_tonight_is_idle(
    duty: Callable[..., dict], testrepo: str, make_library: Callable[..., str]
) -> None:
    report = duty(testrepo, make_library({"ai-briefs": [TODAY]}))

    assert duty_of(report, "ai-briefs")["reason"] == "already published tonight"


def test_collection_in_order_offers_exactly_the_next_item(
    duty: Callable[..., dict], testrepo: str, make_library: Callable[..., str]
) -> None:
    report = duty(testrepo, make_library({"semiconductors": ["micron"]}))

    assert duty_of(report, "semiconductors")["candidates"] == ["tsmc"]


def test_collection_random_offers_every_unpublished_item(
    duty: Callable[..., dict],
    patched_repo: Callable[..., str],
    make_library: Callable[..., str],
) -> None:
    report = duty(
        patched_repo("selection: random\n"),
        make_library({"semiconductors": ["micron"]}),
    )

    assert sorted(duty_of(report, "semiconductors")["candidates"]) == [
        "asml",
        "nvidia",
        "sk-hynix",
        "tsmc",
    ]


def test_paused_series_is_idle(
    duty: Callable[..., dict], patched_repo: Callable[..., str], empty_lib: str
) -> None:
    report = duty(patched_repo("paused: true\n"), empty_lib)

    assert duty_of(report, "semiconductors")["reason"] == "paused"


def test_cadence_off_night_is_idle(
    duty: Callable[..., dict], patched_repo: Callable[..., str], empty_lib: str
) -> None:
    report = duty(patched_repo("cadence: [tue]\n", series="ai-briefs"), empty_lib)

    assert duty_of(report, "ai-briefs") in report["idle"]


def test_open_series_with_a_queue_lists_commissions(
    duty: Callable[..., dict],
    open_press: Callable[..., str],
    make_library: Callable[..., str],
) -> None:
    report = duty(open_press(QUEUE_YAML), make_library({"wildcard": []}))

    assert duty_of(report, "wildcard")["commissions"] == ["commissioned-piece"]


def test_an_article_published_tonight_idles_its_series(
    duty: Callable[..., dict], testrepo: str, make_library: Callable[..., str]
) -> None:
    library = make_library({"semiconductors": []})
    pathlib.Path(library, "library", "semiconductors", "micron.html").write_text(
        article()
    )  # nb-meta date == TODAY

    report = duty(testrepo, library)

    assert duty_of(report, "semiconductors")["reason"] == "already published tonight"


def test_complete_collection_is_idle(
    duty: Callable[..., dict], testrepo: str, make_library: Callable[..., str]
) -> None:
    everything = make_library(
        {"semiconductors": ["micron", "tsmc", "asml", "sk-hynix", "nvidia"]}
    )

    report = duty(testrepo, everything)

    assert duty_of(report, "semiconductors")["reason"] == "complete"


def test_a_dict_item_without_a_slug_is_dropped_not_crashed_on(
    duty: Callable[..., dict],
    overwrite_series: Callable[..., str],
    make_library: Callable[..., str],
) -> None:
    report = duty(
        overwrite_series(COLLECTION_MISSING_SLUG), make_library({"ai-briefs": []})
    )

    assert duty_of(report, "ai-briefs")["candidates"] == ["alpha"]


def test_a_non_mapping_series_yaml_idles_that_one_series_with_a_reason(
    duty: Callable[..., dict], overwrite_series: Callable[..., str], empty_lib: str
) -> None:
    report = duty(overwrite_series("just a bare string\n"), empty_lib)

    assert duty_of(report, "ai-briefs")["reason"] == "series.yaml is not a mapping"
    assert duty_of(report, "ai-briefs") in report["idle"]
    assert duty_of(report, "semiconductors")  # one bad series takes down no other


def test_unparseable_series_yaml_idles_rather_than_aborting_the_run(
    duty: Callable[..., dict], overwrite_series: Callable[..., str], empty_lib: str
) -> None:
    report = duty(overwrite_series("a: b: c\n"), empty_lib)

    assert duty_of(report, "ai-briefs")["reason"] == "series.yaml is not a mapping"


def test_a_non_mapping_nb_meta_payload_does_not_crash_published_state(
    duty: Callable[..., dict], testrepo: str, make_library: Callable[..., str]
) -> None:
    library = make_library({"semiconductors": []})
    pathlib.Path(library, "library", "semiconductors", "micron.html").write_text(
        '<script type="application/json" id="nb-meta">[1, 2, 3]</script>'
    )

    report = duty(testrepo, library)

    assert duty_of(report, "semiconductors")["candidates"] == ["tsmc"]


@pytest.mark.parametrize("cadence", ["[Mon]", "[Fortnight]"])
def test_list_cadence_matches_case_insensitively_and_fails_open(
    duty: Callable[..., dict],
    patched_repo: Callable[..., str],
    empty_lib: str,
    cadence: str,
) -> None:
    """2026-07-06 is a Monday. Mon is due; an unrecognized day name is due too."""
    report = duty(patched_repo(f"cadence: {cadence}\n"), empty_lib)

    assert duty_of(report, "semiconductors") in report["due"]


def test_sequence_progress_counts_syllabus_items_not_library_extras(
    duty: Callable[..., dict],
    seq_repo: Callable[[], str],
    make_library: Callable[..., str],
) -> None:
    library = make_library({"semiconductors": ["micron", "hand-extra"]})

    report = duty(seq_repo(), library)

    assert duty_of(report, "semiconductors")["reason"].startswith("1 of 5 published")


# The 2026-07-14 failure: pointed at a tree with no press, duty printed an empty
# work list and exited 0. The night shift read that as "nothing due", went
# looking for a configuration, and adopted the engine's examples/ folder. An
# empty answer is an invitation. A missing press must refuse, and it must not be
# confusable with a paper whose desks are simply all idle tonight.


@pytest.fixture
def no_press() -> str:
    tmp = tempfile.mkdtemp()
    pathlib.Path(tmp, "engine").mkdir()
    return tmp


def test_a_tree_with_no_press_refuses_instead_of_reporting_a_quiet_night(
    run_duty: Callable[..., subprocess.CompletedProcess[str]],
    no_press: str,
    empty_lib: str,
) -> None:
    run = run_duty("--repo", no_press, "--library", empty_lib)

    assert run.returncode == 2
    assert not run.stdout.strip()


def test_the_refusal_says_which_tree_and_that_examples_is_not_a_press(
    run_duty: Callable[..., subprocess.CompletedProcess[str]],
    no_press: str,
    empty_lib: str,
) -> None:
    run = run_duty("--repo", no_press, "--library", empty_lib)

    assert "no press at" in run.stderr
    assert "examples/ is documentation" in run.stderr


def test_examples_copied_into_press_is_a_real_press(
    run_duty: Callable[..., subprocess.CompletedProcess[str]], empty_lib: str
) -> None:
    """The trap is the path, not the folder: examples/ is a complete working paper."""
    tmp = tempfile.mkdtemp()
    shutil.copytree(REPO / "examples", pathlib.Path(tmp) / "press")

    run = run_duty("--repo", tmp, "--library", empty_lib)

    assert run.returncode == 0


def test_a_press_whose_desks_are_all_idle_is_a_quiet_night_not_a_refusal(
    run_duty: Callable[..., subprocess.CompletedProcess[str]],
    clone_testrepo: Callable[..., str],
    empty_lib: str,
) -> None:
    quiet = clone_testrepo("press", "templates")
    for series_yaml in pathlib.Path(quiet, "press", "series").glob("*/series.yaml"):
        series_yaml.write_text(series_yaml.read_text() + "paused: true\n")

    run = run_duty("--repo", quiet, "--library", empty_lib)

    assert run.returncode == 0
    assert json.loads(run.stdout)["due"] == []


@pytest.fixture
def night_clone(clone_testrepo: Callable[..., str]) -> tuple[str, str]:
    """The press as the night shift sees it: a checkout tracking an origin."""
    origin = tempfile.mkdtemp()
    git("init", "--bare", "-q", "-b", "main", cwd=origin)
    night = clone_testrepo("press", "templates")
    git("init", "-q", "-b", "main", cwd=night)
    git("config", "user.email", "t@t", cwd=night)
    git("config", "user.name", "t", cwd=night)
    git("remote", "add", "origin", origin, cwd=night)
    git("add", "-A", cwd=night)
    git("commit", "-qm", "the press as the night shift sees it", cwd=night)
    git("push", "-q", "origin", "main", cwd=night)
    return night, origin


@pytest.fixture
def stale_clone(night_clone: tuple[str, str]) -> str:
    """The owner retires a series on main; the night shift's clone never hears."""
    night, origin = night_clone
    owner = tempfile.mkdtemp()
    git("clone", "-q", origin, owner, cwd=tempfile.gettempdir())
    git("config", "user.email", "t@t", cwd=owner)
    git("config", "user.name", "t", cwd=owner)
    shutil.rmtree(pathlib.Path(owner) / "press" / "series" / "ai-briefs")
    git("add", "-A", cwd=owner)
    git("commit", "-qm", "retire the old press", cwd=owner)
    git("push", "-q", "origin", "main", cwd=owner)
    return night


def test_a_checkout_level_with_origin_main_computes_the_work_list(
    run_duty: Callable[..., subprocess.CompletedProcess[str]],
    night_clone: tuple[str, str],
    empty_lib: str,
) -> None:
    night, _ = night_clone

    assert run_duty("--repo", night, "--library", empty_lib).returncode == 0


def test_a_checkout_behind_origin_main_refuses_to_compute_a_work_list(
    run_duty: Callable[..., subprocess.CompletedProcess[str]],
    stale_clone: str,
    empty_lib: str,
) -> None:
    run = run_duty("--repo", stale_clone, "--library", empty_lib)

    assert run.returncode == 2
    assert not run.stdout.strip()


def test_the_stale_refusal_names_the_drift_and_the_command_that_fixes_it(
    run_duty: Callable[..., subprocess.CompletedProcess[str]],
    stale_clone: str,
    empty_lib: str,
) -> None:
    run = run_duty("--repo", stale_clone, "--library", empty_lib)

    assert "stale checkout" in run.stderr
    assert "1 commits behind" in run.stderr
    assert "reset --hard origin/main" in run.stderr


def test_allow_stale_is_the_offline_escape_hatch(
    run_duty: Callable[..., subprocess.CompletedProcess[str]],
    stale_clone: str,
    empty_lib: str,
) -> None:
    run = run_duty("--repo", stale_clone, "--library", empty_lib, "--allow-stale")

    assert run.returncode == 0
    assert json.loads(run.stdout)["due"]


def test_a_tree_with_no_git_is_never_called_stale(
    run_duty: Callable[..., subprocess.CompletedProcess[str]],
    testrepo: str,
    empty_lib: str,
) -> None:
    """A press check builds its fixture press in a temp dir, outside any repo."""
    assert run_duty("--repo", testrepo, "--library", empty_lib).returncode == 0
