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

import pytest

import check
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

# preamble is cite-exempt, so it carries no citation; the exchange does.
INTERVIEW_SECTIONS = (
    f'<section data-nb-section="preamble"><p>{LOREM * 20}</p></section>'
    f'<section data-nb-section="exchange"><p>{LOREM * 20}'
    f'<sup class="nb-cite"><a href="#s1">1</a></sup></p></section>'
)

INTERVIEW = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>A Conversation</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "voices", "slug": "first-voice",
  "template": "interview", "title": "A Conversation",
  "mode": "collection", "order": null, "date": "2026-07-06", "tags": [],
  "sources": 5, "words": 1280, "reading_minutes": 6, "dek": "A talk.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body>{INTERVIEW_SECTIONS}
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
    "interview": (
        "class: longread\nwords: [1200, 3000]\n"
        "sections: [preamble, exchange, sources]\n"
        "cite_rule: per-section\ncite_exempt: [preamble]\nmodes: [collection]\n",
        ("preamble", "exchange", "sources"),
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
    "voices": "name: Voices\nmode: collection\ntemplate: interview\n"
    "items:\n  - {slug: first-voice, title: A Conversation}\n",
}


def skeleton_of(*sections: str) -> str:
    return (
        "<!DOCTYPE html><html><body>"
        + "".join(f'<section data-nb-section="{s}"></section>' for s in sections)
        + "</body></html>"
    )


@pytest.fixture
def user_repo(clone_testrepo: Callable[..., str]) -> str:
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
    repo = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(REPO / "templates", repo / "templates")
    series = repo / "press" / "series" / "histories"
    series.mkdir(parents=True)
    (series / "series.yaml").write_text(
        "name: histories\nmode: collection\ntemplate: article\n"
        "autopublish: true\nstrict: false\n"
        "items:\n  - {slug: unix, title: Unix}\n"
    )
    debates = repo / "press" / "series" / "debates"
    debates.mkdir(parents=True)
    (debates / "series.yaml").write_text(
        "name: Debates\nmode: collection\ntemplate: unbiased\n"
        "autopublish: true\nstrict: false\n"
        "items:\n  - {slug: carbon, title: Carbon}\n"
    )
    columns = repo / "press" / "series" / "columns"
    columns.mkdir(parents=True)
    (columns / "series.yaml").write_text(
        "name: Columns\nmode: collection\ntemplate: opinion\n"
        "autopublish: true\nstrict: false\n"
        "items:\n  - {slug: tariffs, title: Tariffs}\n"
    )
    return str(repo)


UNBIASED_SIDES = "".join(
    f'<section class="nb-side nb-side-{half}" data-nb-section="the-case-for-{half}" '
    f'id="the-case-for-{half}">'
    f'<h3 class="nb-side-camp">Camp {half}</h3>'
    f'<p class="nb-side-thesis">The {half} position in one sentence.</p>'
    f'<div class="nb-side-argument"><p>{LOREM * 7}'
    f'<sup class="nb-cite"><a href="#s{i + 1}">{i + 1}</a></sup></p></div>'
    f'<p class="nb-side-champion"><span class="nb-side-outlet">Outlet</span>, '
    f'standing here because reasons.<sup class="nb-cite"><a href="#s{i + 1}">'
    f"{i + 1}</a></sup></p></section>"
    for i, half in enumerate(("left", "right"))
)

UNBIASED = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Carbon</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "debates", "slug": "carbon",
  "template": "unbiased", "title": "Carbon", "mode": "collection",
  "order": null, "date": "2026-07-06", "tags": [], "sources": 5,
  "words": 1400, "reading_minutes": 6, "dek": "Contested.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body class="nb-article">
<section data-nb-section="orientation"><p>{LOREM * 7}
<sup class="nb-cite"><a href="#s3">3</a></sup></p></section>
<div class="nb-divide">{UNBIASED_SIDES}</div>
<section data-nb-section="crux"><p>{LOREM * 7}
<sup class="nb-cite"><a href="#s4">4</a></sup></p></section>
<section data-nb-section="sources"><h2>Sources</h2><ol>{SOURCES}</ol></section>
</body></html>"""


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


def test_series_flex_override_replaces_the_template_band(
    run_local: Callable[..., Findings], template_repo: str
) -> None:
    y = pathlib.Path(template_repo) / "press" / "series" / "histories" / "series.yaml"
    y.write_text(y.read_text() + "overrides:\n  flex_sections: [6, 6]\n")
    extra = "".join(
        f'<section data-nb-section="extra-{i}"><p>{LOREM * 3}'
        f'<sup class="nb-cite"><a href="#s1">1</a></sup></p></section>'
        for i in range(3)
    )
    expanded = chronicle().replace(
        '<section class="nb-sources" data-nb-section="sources">',
        extra + '<section class="nb-sources" data-nb-section="sources">',
    )
    result = run_local(expanded, "histories", slug="unix", repo=template_repo)
    assert not result.blocks


OPINION = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Tariffs</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "columns", "slug": "tariffs",
  "template": "opinion", "title": "Tariffs", "mode": "collection",
  "order": null, "date": "2026-07-06", "tags": [], "sources": 5,
  "words": 1100, "reading_minutes": 5, "dek": "Argued.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body class="nb-article">
<section data-nb-section="position"><div class="nb-position">
<div class="nb-position-top"><span class="nb-position-who">This paper's position</span>
<span class="nb-position-pill">Position</span></div>
<p class="nb-position-statement">Price new load at marginal cost.</p>
<p class="nb-position-summary">After the coalition's filings.<sup class="nb-cite"><a href="#s1">1</a></sup></p>
</div></section>
<section data-nb-section="the-arithmetic"><p>{LOREM * 7}
<sup class="nb-cite"><a href="#s2">2</a></sup></p></section>
<section data-nb-section="the-precedent"><p>{LOREM * 7}
<sup class="nb-cite"><a href="#s4">4</a></sup></p></section>
<section data-nb-section="counter"><p>{LOREM * 7}
<sup class="nb-cite"><a href="#s3">3</a></sup></p></section>
<section data-nb-section="sources"><h2>Sources</h2><ol>{SOURCES}</ol></section>
</body></html>"""


def test_opinion_position_and_answered_counter_pass(
    run_local: Callable[..., Findings], template_repo: str
) -> None:
    result = run_local(OPINION, "columns", slug="tariffs", repo=template_repo)
    assert not result.blocks


def test_opinion_blocks_without_the_counter(
    run_local: Callable[..., Findings], template_repo: str
) -> None:
    skipped = OPINION.replace(
        'data-nb-section="counter"', 'data-nb-section="more-argument"'
    )
    result = run_local(skipped, "columns", slug="tariffs", repo=template_repo)
    assert "B-HTML" in result.blocks


def test_opinion_blocks_when_the_position_card_is_reworded(
    run_local: Callable[..., Findings], template_repo: str
) -> None:
    reworded = OPINION.replace(
        '<span class="nb-position-pill">Position</span>',
        '<span class="nb-position-pill">Stance</span>',
    )
    result = run_local(reworded, "columns", slug="tariffs", repo=template_repo)
    assert "B-CHROME" in result.blocks


def test_unbiased_two_sides_and_a_crux_pass(
    run_local: Callable[..., Findings], template_repo: str
) -> None:
    result = run_local(UNBIASED, "debates", slug="carbon", repo=template_repo)
    assert not result.blocks


def test_unbiased_blocks_a_third_side(
    run_local: Callable[..., Findings], template_repo: str
) -> None:
    third = UNBIASED.replace(
        '<section data-nb-section="crux">',
        '<section data-nb-section="the-case-for-both"><p>extra</p></section>'
        '<section data-nb-section="crux">',
    )
    result = run_local(third, "debates", slug="carbon", repo=template_repo)
    assert "B-HTML" in result.blocks


def test_unbiased_blocks_when_the_divide_chrome_is_reworded(
    run_local: Callable[..., Findings], template_repo: str
) -> None:
    reworded = UNBIASED.replace('<div class="nb-divide">', '<div class="nb-split">')
    result = run_local(reworded, "debates", slug="carbon", repo=template_repo)
    assert "B-CHROME" in result.blocks


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


def test_docs_walkthrough_interview_template_passes(
    run_local: Callable[..., Findings], user_repo: str
) -> None:
    result = run_local(INTERVIEW, "voices", slug="first-voice", repo=user_repo)
    assert not result.blocks


def test_undeclared_extra_section_blocks_on_a_fixed_outline(
    run_local: Callable[..., Findings], user_repo: str
) -> None:
    rogue = INTERVIEW.replace(
        '<section data-nb-section="sources">',
        '<section data-nb-section="rogue"><p>extra</p></section>'
        '<section data-nb-section="sources">',
    )
    result = run_local(rogue, "voices", slug="first-voice", repo=user_repo)
    assert "B-HTML" in result.blocks


def test_validate_config_accepts_the_overlay_registry(
    vc_rc: Callable[[str], int], user_repo: str
) -> None:
    assert vc_rc(user_repo) == 0


def test_validate_config_accepts_series_template_overrides(
    vc_rc: Callable[[str], int], patched_repo: Callable[[str], str]
) -> None:
    assert (
        vc_rc(
            patched_repo("overrides:\n  words: [1000, 5000]\n  flex_sections: [1, 4]\n")
        )
        == 0
    )


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
