"""Templates: the shipped skeletons, and the ones a press writes for itself.

A template is a manifest (the outline and the rules the proof enforces) plus a
skeleton the writer fills. The shipped skeletons must survive their own proof,
and a press that drops its own template into press/templates/ must get the same
enforcement — the rules are registry-driven, never hardcoded to a template name.
"""

import json
import pathlib
import shutil
import tempfile
from collections.abc import Callable

import check
import pytest
from findings import Findings
from press import LOREM, REPO, chronicle

REGISTRY = check.load_registry(str(REPO))

SOURCES = "".join(
    f'<li id="s{i}"><a data-nb-source href="https://example.org/u{i}">x</a></li>'
    for i in range(1, 6)
)

MEMO = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>First Memo</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "memos", "slug": "first", "template": "memo",
  "title": "First Memo", "mode": "collection", "order": null,
  "date": "2026-07-06", "tags": [], "sources": 5, "words": 230,
  "reading_minutes": 1, "dek": "A memo.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body>
<section data-nb-section="note"><p>{LOREM * 7}
<sup class="nb-cite"><a href="#s1">1</a></sup></p></section>
<section data-nb-section="sources"><ol>{SOURCES}</ol></section>
</body></html>"""

LESSON_SECTIONS = "".join(
    f'<section data-nb-section="{section}"><p>{LOREM * 7}'
    f'<sup class="nb-cite"><a href="#s{i + 1}">{i + 1}</a></sup></p></section>'
    for i, section in enumerate(("objectives", "recap", "teach", "check", "bridge"))
)

LESSON = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Hash Functions</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "crypto", "slug": "hashes",
  "template": "lesson", "title": "Hash Functions",
  "mode": "sequence", "order": 1, "date": "2026-07-06", "tags": [],
  "sources": 5, "words": 1560, "reading_minutes": 7, "dek": "Hashes.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body>{LESSON_SECTIONS}
<section data-nb-section="sources"><ol>{SOURCES}</ol></section>
</body></html>"""

USER_TEMPLATES = {
    "memo": (
        "class: shortread\nwords: [200, 3000]\n"
        "sections: [note, sources]\ncite_rule: per-section\nmodes: [collection]\n",
        ("note", "sources"),
    ),
    "fieldnotes": (
        "class: shortread\nwords: [200, 3000]\n"
        "sections: [sources]\nflex_sections: [2, 3]\n"
        "cite_rule: per-section\ncite_exempt: [context]\nmodes: [collection]\n",
        ("YOUR-LABEL", "sources"),
    ),
    # the exact manifest from the docs/customization.md walkthrough, so the
    # tutorial cannot drift from what the proof enforces
    "lesson": (
        "class: longread\nwords: [1500, 4000]\n"
        "sections: [objectives, recap, teach, check, bridge, sources]\n"
        "cite_rule: per-section\ncite_exempt: [objectives]\nmodes: [sequence]\n",
        ("objectives", "recap", "teach", "check", "bridge", "sources"),
    ),
    # a per-item template NOT named 'brief', to prove the per-item cite rule is
    # manifest-driven rather than hardcoded to the shipped brief template
    "digest": (
        "class: shortread\nitems: [2, 4]\n"
        "sections: [entries, sources]\ncite_rule: per-item\n"
        "modes: [collection]\n",
        ("entries", "sources"),
    ),
}

USER_SERIES = {
    "memos": "name: Memos\nmode: collection\ntemplate: memo\nautopublish: true\n"
    "strict: false\nitems:\n  - {slug: first, title: First Memo}\n",
    "notes": "name: Field Notes\nmode: collection\ntemplate: fieldnotes\n"
    "items:\n  - {slug: first-notes, title: First Notes}\n",
    "digests": "name: Digests\nmode: collection\ntemplate: digest\n"
    "items:\n  - {slug: first-digest, title: First Digest}\n",
    "crypto": "name: Cryptography\nmode: sequence\ntemplate: lesson\n"
    "items:\n  - {slug: hashes, title: Hash Functions}\n",
}


def skeleton_of(*sections: str) -> str:
    return (
        "<!DOCTYPE html><html><body>"
        + "".join(f'<section data-nb-section="{s}"></section>' for s in sections)
        + "</body></html>"
    )


@pytest.fixture
def user_repo(clone_testrepo: Callable[..., str]) -> str:
    """A press that overlays its own templates on the shipped ones."""
    repo = clone_testrepo("press", "templates", "engine")
    for template_id, (manifest, sections) in USER_TEMPLATES.items():
        folder = pathlib.Path(repo) / "press" / "templates" / template_id
        folder.mkdir(parents=True)
        (folder / "manifest.yaml").write_text(manifest)
        (folder / "skeleton.html").write_text(skeleton_of(*sections))
    for series, series_yaml in USER_SERIES.items():
        folder = pathlib.Path(repo) / "press" / "series" / series
        folder.mkdir()
        (folder / "series.yaml").write_text(series_yaml)
    return repo


@pytest.fixture
def template_repo() -> str:
    """A press whose series exist only to proof the shipped sample articles."""
    repo = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(REPO / "templates", repo / "templates")
    series = repo / "press" / "series" / "histories"
    series.mkdir(parents=True)
    (series / "series.yaml").write_text(
        "name: histories\nmode: collection\ntemplate: article\n"
        "autopublish: true\nstrict: false\n"
        "items:\n  - {slug: unix, title: Unix}\n"
    )
    return str(repo)


def test_chronicle_shaped_article_is_block_clean_and_warn_free(
    run_local: Callable[..., Findings], template_repo: str
) -> None:
    result = run_local(chronicle(), "histories", slug="unix", repo=template_repo)
    assert not result.blocks
    for code in (
        "W-LENGTH-LOW",
        "W-LENGTH-HIGH",
        "W-SOURCES-MIN",
        "W-CITE-DENSITY",
        "W-SELF-COUNT",
    ):
        assert code not in result.codes


@pytest.mark.parametrize("template_id", sorted(REGISTRY))
def test_shipped_skeleton_is_structurally_sound(template_id: str) -> None:
    treg = REGISTRY[template_id]
    tpl_path = check.find_template(str(REPO), template_id)
    assert tpl_path is not None, "no skeleton.html in templates/ or press/templates/"

    tpl = check.Article()
    tpl.feed(pathlib.Path(tpl_path).read_text())
    tpl.close()

    assert all(tpl.sections.count(s) == 1 for s in treg.get("sections") or [])
    assert json.loads(tpl.meta_raw or "")
    assert all(
        (a.get("type") or "").strip().lower() == "application/json"
        or check.ENGINE_SCRIPT_RE.match(a.get("src", ""))
        for a in tpl.script_tags
    )
    assert not tpl.forbidden_tags
    assert not tpl.bad_event_attrs
    assert not tpl.bad_js_urls
    assert tpl.sources


def test_article_from_a_user_defined_template_passes(
    run_local: Callable[..., Findings], user_repo: str
) -> None:
    result = run_local(MEMO, "memos", slug="first", repo=user_repo)
    assert not result.blocks


def test_user_template_enforces_its_own_sections(
    run_local: Callable[..., Findings], user_repo: str
) -> None:
    result = run_local(
        MEMO.replace('data-nb-section="note"', 'data-nb-section="body"'),
        "memos",
        slug="first",
        repo=user_repo,
    )
    assert "B-HTML" in result.blocks


def test_docs_walkthrough_lesson_template_passes(
    run_local: Callable[..., Findings], user_repo: str
) -> None:
    result = run_local(LESSON, "crypto", slug="hashes", repo=user_repo)
    assert not result.blocks


def test_undeclared_extra_section_blocks_on_a_fixed_outline(
    run_local: Callable[..., Findings], user_repo: str
) -> None:
    rogue = LESSON.replace(
        '<section data-nb-section="sources">',
        '<section data-nb-section="rogue"><p>extra</p></section>'
        '<section data-nb-section="sources">',
    )
    result = run_local(rogue, "crypto", slug="hashes", repo=user_repo)
    assert "B-HTML" in result.blocks


def test_validate_config_accepts_the_overlay_registry(
    vc_rc: Callable[[str], int], user_repo: str
) -> None:
    assert vc_rc(user_repo) == 0


def test_the_merged_registry_keeps_shipped_and_adds_press_templates(
    user_repo: str,
) -> None:
    registry = check.load_registry(user_repo)

    assert "memo" in registry
    assert "article" in registry


def test_a_press_template_shadows_a_shipped_one_of_the_same_name(
    user_repo: str,
) -> None:
    memo = check.find_template(user_repo, "memo") or ""
    shipped = check.find_template(user_repo, "article") or ""

    assert memo.endswith("memo/skeleton.html")
    assert "press" in memo
    assert shipped.endswith("article/skeleton.html")
    assert "press" not in shipped
