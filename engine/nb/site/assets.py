"""What the build copies into the site: the assets, and the article copies.

The shared stylesheet assembled from the modular engine CSS parts under
engine/assets/css/, the concatenated theme, and the content hash that stamps
them; and the article copies, which are the canonical library files with their
asset links stamped and the site chrome spliced in. The canonical files on the
library branch stay byte-exact.
"""

from __future__ import annotations

import hashlib
import html
import pathlib
import re
import shutil
import sys
import urllib.parse
from typing import TYPE_CHECKING

from nb.links import is_repo_relative_source
from nb.site.pages import chrome_footer, chrome_header

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

__all__ = (
    "NB_CSS_PARTS",
    "asset_stamp",
    "copy_articles",
    "copy_assets",
    "css_owners",
    "dress_article",
    "nb_css_sources",
    "rewrite_required_doc_links",
    "template_dirs",
    "write",
)

NB_CSS_PARTS = ("site.css", "article.css", "templates.css", "media.css")


def nb_css_sources(repo: str | pathlib.Path) -> list[str]:
    css_dir = pathlib.Path(repo) / "engine" / "assets" / "css"
    return [str(css_dir / name) for name in NB_CSS_PARTS]


def write(path: str | pathlib.Path, content: str) -> None:
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def asset_stamp(repo: str | pathlib.Path, css_paths: Iterable[str | pathlib.Path] = ()) -> str:
    """Return a short content hash of the shared assets for cache busting.

    Every generated page and article copy links assets with ?v=<stamp>,
    so a returning reader can never pair cached old assets with newer markup.
    The stamp folds in the site icons, nb.css, nb.js, and every CSS owner
    concatenated into assets/theme.css (the configured theme plus all
    furniture, shared and template-scoped). copy_assets rebuilds theme.css
    from those owners every build, so editing any of them busts the reader's
    cache and the new look actually reaches them.
    """
    h = hashlib.md5(usedforsecurity=False)
    base = pathlib.Path(repo) / "engine" / "assets"
    paths = [
        base / "apple-touch-icon.png",
        base / "favicon-32.png",
        base / "favicon-64.png",
        *(pathlib.Path(p) for p in nb_css_sources(repo)),
        base / "nb.js",
        *(pathlib.Path(p) for p in css_paths),
    ]
    for path in paths:
        if path.is_file():
            h.update(path.read_bytes())
    return h.hexdigest()[:10]


def template_dirs(repo: str | pathlib.Path) -> dict[str, str]:
    """Map each template id to its resolved folder, press shadowing shipped.

    A template is a folder holding a manifest.yaml (the folder name is the
    id); a press/templates/<id> package replaces a shipped one of the same
    id wholesale. A folder without a manifest.yaml is not a template and is
    skipped, so a stray asset left beside the packages is ignored.
    """
    repo_path = pathlib.Path(repo)
    dirs: dict[str, str] = {}
    for base in (
        repo_path / "templates",
        repo_path / "press" / "templates",  # press shadows shipped
    ):
        if not base.is_dir():
            continue
        for folder in sorted(base.iterdir(), key=lambda p: p.name):
            if (folder / "manifest.yaml").is_file():
                dirs[folder.name] = str(folder)
    return dirs


def css_owners(repo: str | pathlib.Path, site_cfg: Mapping[str, object]) -> list[str]:
    """Every CSS file concatenated into the published assets/theme.css.

    Deterministically ordered so the cascade is stable and a later owner
    can lean on tokens an earlier one defines: the site theme first, then
    the shared press furniture, then each template's bespoke furniture in
    id order. Missing optional files are filtered out.
    """
    repo_path = pathlib.Path(repo)
    owners = [
        repo_path / str(site_cfg["theme"]),
        repo_path / "press" / "furniture" / "styles.css",
    ]
    for _id, folder in sorted(template_dirs(repo).items()):
        owners.append(pathlib.Path(folder) / "furniture.css")
    return [str(path) for path in owners if path.is_file()]


def copy_assets(
    repo: str | pathlib.Path,
    site_cfg: Mapping[str, object],
    *,
    out: str | pathlib.Path,
) -> None:
    src = pathlib.Path(repo) / "engine" / "assets"
    dst = pathlib.Path(out) / "assets"
    if dst.is_dir():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("css"))
    nb_blocks = [
        path.read_text(encoding="utf-8").rstrip()
        for raw_path in nb_css_sources(repo)
        if (path := pathlib.Path(raw_path)).is_file()
    ]
    write(dst / "nb.css", "\n\n".join(nb_blocks) + "\n")
    # Every CSS owner is concatenated under the stable name assets/theme.css:
    # the configured theme plus all furniture (shared and template-scoped). The
    # output name never changes, so page links and article copies need no edit,
    # and a theme or furniture change restyles every already-published article.
    blocks = []
    for raw_path in css_owners(repo, site_cfg):
        path = pathlib.Path(raw_path)
        blocks.append(f"/* --- {path.name} --- */\n{path.read_text(encoding='utf-8').rstrip()}")
    write(dst / "theme.css", "\n\n".join(blocks) + "\n")


ARTICLE_ASSET_RE = re.compile(r'((?:href|src)="(?:\.\./)*assets/(?:nb\.css|nb\.js|theme\.css))(")')
BODY_OPEN_RE = re.compile(r"<body\b[^>]*>", re.IGNORECASE)
ANCHOR_RE = re.compile(r"<a\b[^>]*>", re.IGNORECASE)
REQUIRED_ATTR_RE = re.compile(r"\bdata-nb-required(?:\s*=|\s|>)", re.IGNORECASE)
HREF_ATTR_RE = re.compile(r"(\bhref\s*=\s*)(?:([\"'])(.*?)\2|([^\s>]+))", re.IGNORECASE | re.DOTALL)

# Site copies of articles live at library/<series>/<slug>.html.
ARTICLE_DEPTH = 2


def rewrite_required_doc_links(raw: str, repository: str | None) -> tuple[str, bool]:
    """Point local required-doc citations at the file on the fork's main branch.

    Canonical articles keep the repo-relative provenance the proof validates.
    Only the generated site copy gets a reader-facing GitHub URL. The boolean
    reports a local citation that could not be rewritten because a preview had
    no repository identity.
    """
    unresolved = False

    def rewrite_anchor(match: re.Match[str]) -> str:
        nonlocal unresolved
        tag = match.group(0)
        if REQUIRED_ATTR_RE.search(tag) is None:
            return tag
        href_match = HREF_ATTR_RE.search(tag)
        if href_match is None:
            return tag
        group = 3 if href_match.group(2) else 4
        href = html.unescape(href_match.group(group))
        if not is_repo_relative_source(href):
            return tag
        if repository is None:
            unresolved = True
            return tag
        path = urllib.parse.quote(href, safe="/%:@-._~")
        url = f"https://github.com/{repository}/blob/main/{path}"
        start, end = href_match.span(group)
        return f"{tag[:start]}{url}{tag[end:]}"

    return ANCHOR_RE.sub(rewrite_anchor, raw), unresolved


def dress_article(raw: str, site: dict) -> str:
    """Return the article markup with the site chrome and press assets in place.

    An article is authored as a standalone page, so the bar and footer that
    generated pages get from page() are spliced in here, at copy time: the same
    Python builds both, and the whole back catalogue wears the current chrome on
    the next build. Idempotent, so an article that already carries a bar (an
    already-dressed copy handed back in) is left with exactly one.
    """
    icons = "\n".join(
        (
            f'<link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png?v={site["stamp"]}">',
            f'<link rel="icon" type="image/png" sizes="64x64" href="../../assets/favicon-64.png?v={site["stamp"]}">',
            f'<link rel="apple-touch-icon" sizes="180x180" href="../../assets/apple-touch-icon.png?v={site["stamp"]}">',
        )
    )
    if "assets/favicon-32.png" not in raw:
        raw = raw.replace("</head>", f"{icons}\n</head>", 1)
    if site["assets_html"]:
        raw = raw.replace("</head>", f"{site['assets_html']}\n</head>", 1)
    body_open = BODY_OPEN_RE.search(raw)
    if not body_open or 'class="nb-bar"' in raw:
        return raw
    header = chrome_header(site, depth=ARTICLE_DEPTH)
    at = body_open.end()
    raw = f"{raw[:at]}\n{header}{raw[at:]}"
    return raw.replace("</body>", f"{chrome_footer(site)}\n</body>", 1)


def copy_articles(articles: dict, out: str | pathlib.Path, *, site: dict) -> None:
    """Copy articles into the site with stamped asset links and site chrome.

    The canonical files on the library branch stay byte-exact; only the
    generated site copy gets ?v=<stamp> on nb.css, nb.js, and theme.css so
    cached assets can never mismatch the markup, the press assets so
    library-backed furniture (a highlighter, say) works in every article, and
    the reader chrome so an article is a page of this paper.
    """
    out_path = pathlib.Path(out)
    for ed in articles.values():
        dst = out_path / "library" / ed["series"] / f"{ed['slug']}.html"
        dst.parent.mkdir(parents=True, exist_ok=True)
        src_file = pathlib.Path(ed["file"])
        raw = src_file.read_text(encoding="utf-8", errors="replace")
        if site["stamp"]:
            raw = ARTICLE_ASSET_RE.sub(rf"\1?v={site['stamp']}\2", raw)
        raw, unresolved = rewrite_required_doc_links(raw, site["repository"])
        if unresolved:
            sys.stderr.write(
                f"warning: required-doc link left relative because repository identity is unavailable: {ed['file']}\n"
            )
        write(dst, dress_article(raw, site))
        source_assets = src_file.parent / ed["slug"]
        if source_assets.is_dir():
            shutil.copytree(
                source_assets,
                dst.parent / ed["slug"],
                dirs_exist_ok=True,
            )
