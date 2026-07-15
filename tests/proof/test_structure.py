"""The page is the shape its template promised, and it cannot execute anything.

Two rules meet here. Structure: the sections a template declares are the
sections the article carries, no more and no fewer, and where the template
leaves the outline to the writer the band still holds. Sandbox: an article is
inert text. Nothing runs, nothing loads off a host the paper does not name.
"""

import pathlib
from collections.abc import Callable

import pytest
from findings import Findings
from press import LOREM, article, mut

FONT_LINK = "https://fonts.googleapis.com/css2?family=Newsreader&amp;display=swap"
PNG = (
    b"\x89PNG\r\n\x1a\n"
    + b"\0\0\0\rIHDR"
    + (640).to_bytes(4, "big")
    + (480).to_bytes(4, "big")
)


def source_figure(
    *, src: str = "micron/figure-1.png", alt: str = "Memory demand by year"
) -> str:
    return f'''<figure class="nb-figure">
  <img src="{src}" alt="{alt}" />
  <figcaption>Fig. 1 · Demand.<sup class="nb-cite"><a href="#s1">1</a></sup></figcaption>
</figure>'''


def test_a_cited_local_figure_passes(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        mut("</article>", f"{source_figure()}</article>"),
        "semiconductors",
        assets={"micron/figure-1.png": PNG},
    )

    assert "B-FIGURE" not in result.codes
    assert "B-SANDBOX" not in result.codes


@pytest.mark.parametrize(
    ("figure", "assets"),
    [
        pytest.param(
            source_figure(alt=""), {"micron/figure-1.png": PNG}, id="missing-alt"
        ),
        pytest.param(source_figure(src="other/figure-1.png"), {}, id="wrong-directory"),
        pytest.param(
            source_figure(src="https://example.org/figure.png"),
            {},
            id="external-source",
        ),
        pytest.param(source_figure(), {}, id="missing-file"),
    ],
)
def test_invalid_figures_block(
    run_local: Callable[..., Findings], *, figure: str, assets: dict[str, bytes]
) -> None:
    result = run_local(
        mut("</article>", f"{figure}</article>"), "semiconductors", assets=assets
    )

    assert "B-FIGURE" in result.blocks


def test_missing_required_section_blocks(run_local: Callable[..., Findings]) -> None:
    result = run_local(
        mut('data-nb-section="orientation"', 'data-nb-section="intro"'),
        "semiconductors",
    )

    assert "B-HTML" in result.blocks


def test_duplicated_section_blocks(run_local: Callable[..., Findings]) -> None:
    duplicated = article().replace(
        '<section data-nb-section="bull-versus-bear">',
        '<section data-nb-section="orientation">',
        1,
    )
    result = run_local(duplicated, "semiconductors")

    assert "B-HTML" in result.blocks


@pytest.mark.parametrize(
    "name,html",
    [
        (
            "executable script",
            mut("</article>", "<script>alert(1)</script></article>"),
        ),
        (
            "external script src",
            mut(
                "</article>",
                '<script type="application/json" data-nb-chart '
                'src="https://evil.example/x.js"></script></article>',
            ),
        ),
        (
            "iframe",
            mut("</article>", '<iframe src="https://x.example"></iframe></article>'),
        ),
        ("inline event handler", mut("<article>", '<article onclick="x()">')),
        (
            "javascript: url",
            mut('href="https://example.org/src3"', 'href="javascript:alert(1)"'),
        ),
        (
            "non-allowlisted stylesheet",
            mut(FONT_LINK, "https://cdn.evil.example/style.css"),
        ),
        (
            "font-host subdomain-suffix bypass",
            mut(FONT_LINK, "https://fonts.googleapis.com.evil.example/pwn.css"),
        ),
        (
            "font-host userinfo bypass",
            mut(FONT_LINK, "https://fonts.googleapis.com@evil.example/pwn.css"),
        ),
        (
            "font-host lookalike TLD suffix",
            mut(FONT_LINK, "https://fonts.googleapis.commmm/x.css"),
        ),
        ("malformed chart json", mut('"type":"bar"', '"type":"pie"')),
        (
            "stray json script block",
            mut(
                "</article>",
                '<script type="application/json">{"x":1}</script></article>',
            ),
        ),
        (
            "non-engine relative script",
            mut("</head>", '<script src="../../assets/other.js"></script></head>'),
        ),
        (
            "protocol-relative stylesheet",
            mut(FONT_LINK, "//cdn.evil.example/style.css"),
        ),
        (
            "backslash-obfuscated external ref",
            mut(FONT_LINK, "/\\cdn.evil.example/style.css"),
        ),
        (
            "meta-refresh redirect",
            mut(
                "</head>",
                '<meta http-equiv="refresh" content="0;url=//evil.example"></head>',
            ),
        ),
        (
            "form",
            mut("</article>", '<form action="//evil.example"></form></article>'),
        ),
    ],
)
def test_the_sandbox_blocks(
    run_local: Callable[..., Findings], name: str, html: str
) -> None:
    result = run_local(html, "semiconductors")

    assert "B-SANDBOX" in result.blocks


def test_an_external_script_load_blocks_on_its_own_rule(
    run_local: Callable[..., Findings],
) -> None:
    # The script-src rule shares B-SANDBOX with the external-ref allowlist, which
    # fires on the same markup. Asserting the code alone passes even when this rule
    # is downgraded to a warn, so name the finding: a published article that loads a
    # script off the open web is the sandbox failing at the only job it has.
    loads_a_script = mut(
        "</article>",
        '<script type="application/json" data-nb-chart '
        'src="https://evil.example/x.js"></script></article>',
    )

    result = run_local(loads_a_script, "semiconductors")

    assert result.blocks.saying("articles may not load external scripts")


def test_google_fonts_is_allowed(run_local: Callable[..., Findings]) -> None:
    result = run_local(article(), "semiconductors")

    assert "B-SANDBOX" not in result.codes


def test_the_engine_runtime_script_is_allowed(
    run_local: Callable[..., Findings],
) -> None:
    result = run_local(
        mut("</head>", '<script defer src="../../assets/nb.js"></script></head>'),
        "semiconductors",
    )

    assert "B-SANDBOX" not in result.codes
    assert not result.blocks


def test_a_second_nb_meta_block_is_refused(run_local: Callable[..., Findings]) -> None:
    result = run_local(
        mut(
            "</head>",
            '<script type="application/json" id="nb-meta">{"x":1}</script></head>',
        ),
        "semiconductors",
    )

    assert "B-META-PARSE" in result.blocks


FIELDNOTES_MANIFEST = (
    "class: shortread\nwords: [200, 3000]\n"
    "sections: [sources]\nflex_sections: [2, 3]\n"
    "cite_rule: per-section\ncite_exempt: [context]\nmodes: [collection]\n"
)
# a per-item template NOT named 'brief', to prove the per-item cite rule is
# manifest-driven rather than hardcoded to the shipped brief template
DIGEST_MANIFEST = (
    "class: shortread\nitems: [2, 4]\n"
    "sections: [entries, sources]\ncite_rule: per-item\n"
    "modes: [collection]\n"
)


def skeleton_of(*sections: str) -> str:
    return (
        "<!DOCTYPE html><html><body>"
        + "".join(f'<section data-nb-section="{s}"></section>' for s in sections)
        + "</body></html>"
    )


@pytest.fixture
def overlay_repo(clone_testrepo: Callable[..., str]) -> str:
    """A press whose templates overlay adds a flex template and a per-item one."""
    repo = clone_testrepo("press", "templates", "engine")
    templates = pathlib.Path(repo) / "press" / "templates"
    for tid, manifest, skeleton in [
        ("fieldnotes", FIELDNOTES_MANIFEST, skeleton_of("YOUR-LABEL", "sources")),
        ("digest", DIGEST_MANIFEST, skeleton_of("entries", "sources")),
    ]:
        folder = templates / tid
        folder.mkdir(parents=True)
        (folder / "manifest.yaml").write_text(manifest)
        (folder / "skeleton.html").write_text(skeleton)
    series = pathlib.Path(repo) / "press" / "series"
    (series / "notes").mkdir()
    (series / "notes" / "series.yaml").write_text(
        "name: Field Notes\nmode: collection\ntemplate: fieldnotes\n"
        "items:\n  - {slug: first-notes, title: First Notes}\n"
    )
    (series / "digests").mkdir()
    (series / "digests" / "series.yaml").write_text(
        "name: Digests\nmode: collection\ntemplate: digest\n"
        "items:\n  - {slug: first-digest, title: First Digest}\n"
    )
    return repo


def cite(n: int) -> str:
    return f'<sup class="nb-cite"><a href="#s{n}">{n}</a></sup>'


def sources(n: int, prefix: str) -> str:
    return "".join(
        f'<li id="s{i}"><a data-nb-source '
        f'href="https://example.org/{prefix}{i}">x</a></li>'
        for i in range(1, n + 1)
    )


def flex_article(sections: list[tuple[str, str]]) -> str:
    body = "".join(
        f'<section data-nb-section="{name}"><p>{LOREM * 7}{cited}</p></section>'
        for name, cited in sections
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>First Notes</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "notes", "slug": "first-notes",
  "template": "fieldnotes", "title": "First Notes", "mode": "collection",
  "order": null, "date": "2026-07-06", "tags": [], "sources": 5,
  "words": 460, "reading_minutes": 2, "dek": "Notes.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body>{body}
<section data-nb-section="sources"><ol>{sources(5, "n")}</ol></section>
</body></html>"""


def run_notes(
    run_local: Callable[..., Findings], repo: str, sections: list[tuple[str, str]]
) -> Findings:
    return run_local(flex_article(sections), "notes", slug="first-notes", repo=repo)


def test_flex_template_passes_with_agent_named_sections_in_band(
    run_local: Callable[..., Findings], overlay_repo: str
) -> None:
    result = run_notes(
        run_local, overlay_repo, [("the-lab", cite(1)), ("the-bet", cite(2))]
    )

    assert not result.blocks


@pytest.mark.parametrize(
    "name,sections",
    [
        ("too few", [("only-one", cite(1))]),
        (
            "too many",
            [
                ("a1", cite(1)),
                ("a2", cite(2)),
                ("a3", cite(3)),
                ("a4", cite(1)),
            ],
        ),
        ("duplicate labels", [("twice", cite(1)), ("twice", cite(2))]),
    ],
)
def test_a_flex_outline_out_of_band_blocks(
    run_local: Callable[..., Findings],
    overlay_repo: str,
    name: str,
    sections: list[tuple[str, str]],
) -> None:
    result = run_notes(run_local, overlay_repo, sections)

    assert "B-HTML" in result.blocks


def test_uncited_flex_section_warns_on_cite_density(
    run_local: Callable[..., Findings], overlay_repo: str
) -> None:
    result = run_notes(run_local, overlay_repo, [("cited", cite(1)), ("uncited", "")])

    assert "W-CITE-DENSITY" in result.warns
    assert not result.blocks


def test_cite_exempt_exempts_a_registry_declared_section(
    run_local: Callable[..., Findings], overlay_repo: str
) -> None:
    result = run_notes(run_local, overlay_repo, [("context", ""), ("the-bet", cite(2))])

    assert "W-CITE-DENSITY" not in result.codes
    assert not result.blocks


def test_sources_cited_out_of_first_appearance_order_warns(
    run_local: Callable[..., Findings], overlay_repo: str
) -> None:
    result = run_notes(
        run_local, overlay_repo, [("the-lab", cite(2)), ("the-bet", cite(1))]
    )

    assert "W-CITE-ORDER" in result.warns
    assert not result.blocks


def test_in_order_citations_do_not_warn(
    run_local: Callable[..., Findings], overlay_repo: str
) -> None:
    result = run_notes(
        run_local, overlay_repo, [("the-lab", cite(1)), ("the-bet", cite(2))]
    )

    assert "W-CITE-ORDER" not in result.codes
    assert not result.blocks


def digest_article(*, withhold_cite: bool) -> str:
    items = "".join(
        f"<div data-nb-item><span>t{i}</span>"
        f"<h3>Item {i}"
        + ("" if (withhold_cite and i == 1) else cite(i))
        + f"</h3><p>{LOREM}</p></div>"
        for i in (1, 2)
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>First Digest</title>
<script type="application/json" id="nb-meta">
{{"protocol": "1.0", "series": "digests", "slug": "first-digest",
  "template": "digest", "title": "First Digest", "mode": "collection",
  "order": null, "date": "2026-07-06", "tags": [], "sources": 5, "words": 60,
  "reading_minutes": 1, "dek": "A digest.",
  "harness": "test-fixture", "model": "claude-fable-5"}}
</script>
</head><body>
<section data-nb-section="entries">{items}</section>
<section data-nb-section="sources"><ol>{sources(5, "d")}</ol></section>
</body></html>"""


def test_a_fully_cited_digest_passes(
    run_local: Callable[..., Findings], overlay_repo: str
) -> None:
    result = run_local(
        digest_article(withhold_cite=False),
        "digests",
        slug="first-digest",
        repo=overlay_repo,
    )

    assert not result.blocks
    assert "W-CITE-DENSITY" not in result.codes


def test_per_item_cite_density_warns_for_a_non_brief_template(
    run_local: Callable[..., Findings], overlay_repo: str
) -> None:
    result = run_local(
        digest_article(withhold_cite=True),
        "digests",
        slug="first-digest",
        repo=overlay_repo,
    )

    assert "W-CITE-DENSITY" in result.warns
