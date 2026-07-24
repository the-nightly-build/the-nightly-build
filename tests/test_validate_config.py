"""Configuration is checked before the night shift runs, not after it fails.

These tests exercise the author-facing validator against real copied press
trees. They focus on readable errors and on the contract's deliberately loose
template choice model, so malformed YAML never becomes an unattended traceback.
"""

import pathlib
import shutil
import subprocess
import tempfile
from collections.abc import Callable

import pytest

import validate_config
from press import REPO

REQ_DOCS_NOT_LIST = "name: X\nmode: rolling\ntemplate: brief\nrequired_docs: nope\n"
REQ_DOC_NOT_MAP = (
    "name: X\nmode: collection\ntemplate: article\n"
    "items:\n  - {slug: alpha, required_docs: [oops]}\n"
)
TWO_SLUGLESS = (
    "name: X\nmode: collection\ntemplate: article\n"
    "items:\n  - {title: one}\n  - {title: two}\n"
)
DUP_SLUG = (
    "name: X\nmode: collection\ntemplate: article\n"
    "items:\n  - {slug: alpha}\n  - {slug: alpha}\n"
)


def site_errors(yaml_text: str) -> list[str]:
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "press").mkdir()
    (d / "press" / "site.yaml").write_text(yaml_text)
    errors: list[str] = []
    validate_config.check_site(str(d), errors)
    return errors


def directory_errors(directory: dict) -> list[str]:
    errors: list[str] = []
    validate_config.check_site_directory(directory, errors=errors)
    return errors


def production_errors(policy: dict | None) -> list[str]:
    errors: list[str] = []
    validate_config.check_production_policy(
        policy, where="press/production.yaml", errors=errors
    )
    return errors


@pytest.fixture
def manifest_patched_repo(clone_testrepo: Callable[..., str]) -> Callable[..., str]:
    """Return a copied press whose selected manifest has ``patch`` appended.

    The helper deliberately uses a duplicate YAML key: PyYAML's last-value
    behavior lets each test replace one manifest field without maintaining a
    second full template package. The returned tree is isolated from the
    session fixture and is safe for a validator run to inspect.
    """

    def patch_manifest(patch: str, template: str = "article") -> str:
        tmp = clone_testrepo("press", "templates", "engine")
        m = pathlib.Path(tmp) / "templates" / template / "manifest.yaml"
        # A repeated key is fine here: yaml keeps the last one, the patch.
        m.write_text(m.read_text() + patch)
        return tmp

    return patch_manifest


def test_the_shipped_examples_validate_as_a_press(
    vc_rc: Callable[[str], int],
) -> None:
    repo = pathlib.Path(tempfile.mkdtemp()) / "repo"
    repo.mkdir()
    shutil.copytree(REPO / "templates", repo / "templates")
    shutil.copytree(REPO / "engine" / "assets", repo / "engine" / "assets")
    shutil.copytree(REPO / "examples", repo / "press")

    assert vc_rc(str(repo)) == 0


def test_a_template_choice_list_is_valid_for_every_scheduling_mode(
    clone_testrepo: Callable[..., str], vc_rc: Callable[[str], int]
) -> None:
    repo = clone_testrepo("press", "templates", "engine")
    y = pathlib.Path(repo) / "press" / "series" / "semiconductors" / "series.yaml"
    text = y.read_text().replace("mode: collection", "mode: rolling")
    text = text.replace("template: article", "templates: [article]")
    y.write_text(text[: text.index("items:")])

    assert vc_rc(repo) == 0


@pytest.mark.parametrize(
    ("site_yaml", "valid"),
    [
        pytest.param('title: "x"\nfooter: "Filed."\n', True, id="valid-imprint"),
        pytest.param(f'title: "x"\nfooter: "{"a" * 81}"\n', False, id="over-80-chars"),
        pytest.param('title: "x"\nfooter: ""\n', False, id="empty-string"),
    ],
)
def test_the_footer_imprint_is_a_short_line(site_yaml: str, valid: bool) -> None:
    assert (site_errors(site_yaml) == []) is valid


@pytest.mark.parametrize(
    ("directory", "valid"),
    [
        pytest.param({"publish": True, "description": "hi"}, True, id="opted-in"),
        pytest.param({"publish": False}, True, id="opted-out"),
        pytest.param({}, True, id="absent"),
        pytest.param({"publish": True}, True, id="listed-with-no-description"),
        pytest.param(
            {"publish": True, "description": "hi", "url": "x"},
            False,
            id="redundant-url-key",
        ),
        pytest.param(
            {"publish": "yes", "description": "hi"}, False, id="non-bool-publish"
        ),
        pytest.param(
            {"publish": True, "description": "a" * 281},
            False,
            id="description-over-280-chars",
        ),
    ],
)
def test_the_directory_block_states_a_choice_and_a_description(
    directory: dict, valid: bool
) -> None:
    assert (directory_errors(directory) == []) is valid


@pytest.mark.parametrize(
    ("policy", "valid"),
    [
        pytest.param({"profile": "balanced"}, True, id="profile"),
        pytest.param(
            {
                "profile": "economy",
                "required": False,
                "stages": {
                    "writer": {
                        "model": "provider/exact-model",
                        "effort": "provider-specific",
                        "required": True,
                    }
                },
            },
            True,
            id="exact-stage-policy",
        ),
        pytest.param({"profile": "fastest"}, False, id="unknown-profile"),
        pytest.param({"required": "yes"}, False, id="required-string"),
        pytest.param({"stages": []}, False, id="stages-list"),
        pytest.param(
            {"stages": {"correspondent": {"model": "premium"}}},
            False,
            id="orchestrator-not-configurable",
        ),
        pytest.param(
            {"stages": {"writer": {"model": ""}}},
            False,
            id="empty-model",
        ),
        pytest.param(
            {"stages": {"writer": {"skip": True}}},
            False,
            id="stage-skipping-unknown",
        ),
    ],
)
def test_production_policy_has_a_small_portable_schema(
    policy: dict | None, valid: bool
) -> None:
    assert (production_errors(policy) == []) is valid


@pytest.mark.parametrize(
    ("patch", "rc"),
    [
        pytest.param("autopublish: 'false'\n", 1, id="autopublish-truthy-string"),
        pytest.param("strict: 'no'\n", 1, id="strict-truthy-string"),
        pytest.param("min_sources: lots\n", 1, id="min_sources-string"),
        pytest.param("min_sources: -1\n", 1, id="min_sources-negative"),
        pytest.param("min_sources: 12\n", 0, id="min_sources-well-typed"),
        pytest.param(
            "sources_by_kind:\n  primary: [oops, 2]\n",
            1,
            id="source-band-invalid-low",
        ),
    ],
)
def test_a_mistyped_series_key_is_a_validation_error(
    patched_repo: Callable[..., str], vc_rc: Callable[[str], int], patch: str, rc: int
) -> None:
    assert vc_rc(patched_repo(patch)) == rc


def test_unparseable_series_yaml_is_a_readable_error_not_a_traceback(
    overwrite_series: Callable[..., str],
    vc_output: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    out = vc_output(overwrite_series("a: b: c\n"))

    assert out.returncode == 1
    assert "not valid YAML" in out.stdout
    assert "Traceback" not in out.stderr


def test_a_non_dict_series_yaml_is_a_readable_error_not_a_traceback(
    overwrite_series: Callable[..., str],
    vc_output: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    out = vc_output(overwrite_series("just a bare string\n"))

    assert out.returncode == 1
    assert "must be a mapping" in out.stdout
    assert "Traceback" not in out.stderr


@pytest.mark.parametrize(
    ("series_yaml", "message"),
    [
        pytest.param(
            REQ_DOCS_NOT_LIST, "'required_docs' must be a list", id="required_docs-list"
        ),
        pytest.param(
            REQ_DOC_NOT_MAP,
            "required_docs entry must be a mapping",
            id="required_docs-entry-mapping",
        ),
        pytest.param(DUP_SLUG, "duplicate item slug 'alpha'", id="duplicate-slug"),
    ],
)
def test_a_malformed_series_reports_what_is_wrong(
    overwrite_series: Callable[..., str],
    vc_output: Callable[[str], subprocess.CompletedProcess[str]],
    series_yaml: str,
    message: str,
) -> None:
    assert message in vc_output(overwrite_series(series_yaml)).stdout


def test_two_slugless_items_never_report_a_false_duplicate(
    overwrite_series: Callable[..., str],
    vc_output: Callable[[str], subprocess.CompletedProcess[str]],
) -> None:
    assert "duplicate item slug" not in vc_output(overwrite_series(TWO_SLUGLESS)).stdout


@pytest.mark.parametrize(
    ("patch", "rc"),
    [
        pytest.param(
            "chrome: ['<body class=\"nb-article\">']\n",
            0,
            id="quotes-the-skeleton-verbatim",
        ),
        pytest.param(
            "chrome: ['<body class=\"nb-elsewhere\">']\n",
            1,
            id="not-in-the-skeleton",
        ),
        pytest.param('chrome: "<h2>Sources</h2>"\n', 1, id="scalar-never-vacuous"),
    ],
)
def test_declared_chrome_must_appear_in_the_template_skeleton(
    manifest_patched_repo: Callable[..., str],
    vc_rc: Callable[[str], int],
    patch: str,
    rc: int,
) -> None:
    assert vc_rc(manifest_patched_repo(patch)) == rc


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        pytest.param(
            "bands: {unknown: [1, 2]}\n",
            "bands has unknown keys",
            id="unknown-band",
        ),
        pytest.param(
            "bands: {words: [100]}\n",
            "bands.words must be [low, high]",
            id="malformed-band",
        ),
    ],
)
def test_invalid_series_bands_report_their_cause(
    patched_repo: Callable[[str], str],
    vc_output: Callable[[str], subprocess.CompletedProcess[str]],
    *,
    patch: str,
    message: str,
) -> None:
    assert message in vc_output(patched_repo(patch)).stdout
