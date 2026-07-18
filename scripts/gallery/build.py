#!/usr/bin/env python3
"""Build the furniture gallery: every catalog piece on one reviewable page.

The gallery is a dev tool, not a publishable page. It renders each furniture
piece from every catalog scope — the engine base, the press's shared catalog,
and each template's bespoke set — in isolation, with realistic sample content
from ``samples/``, so an owner can judge and fine-tune components without
writing an article. The page links the repo's CSS by relative path, so a
style edit is a browser refresh, and it carries its own light/dark/auto
toggle on the same ``data-mode`` mechanism the site runtime uses. Output goes
under ``press-check/`` (gitignored); the build fails loudly when a catalog
piece has no sample, and the test suite holds the two in lockstep.

Usage:
    uv run python scripts/gallery/build.py
    python3 -m http.server 8383 --bind 0.0.0.0   # then open /press-check/gallery/
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SAMPLES = Path(__file__).resolve().parent / "samples"
DEFAULT_OUT = REPO / "press-check" / "gallery" / "index.html"


@dataclass
class Piece:
    name: str
    slug: str
    scope: str
    blurb: str
    engine_owned: bool


def slugify(heading: str) -> str:
    bare = re.sub(r"\s*\(.*\)\s*$", "", heading).strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", bare).strip("-")


def parse_catalog(text: str, scope: str, *, engine_owned: bool) -> list[Piece]:
    pieces = []
    for match in re.finditer(r"^## (.+)$", text, re.MULTILINE):
        name = re.sub(r"\s*\(`[^`]*`\)\s*$", "", match.group(1)).strip()
        rest = text[match.end() :]
        paragraph = re.split(r"\n\s*\n", rest.strip(), maxsplit=1)[0]
        blurb = re.sub(r"`([^`]+)`", r"<code>\1</code>", " ".join(paragraph.split()))
        pieces.append(Piece(name, slugify(name), scope, blurb, engine_owned))
    return pieces


def discover_pieces(repo: Path) -> list[Piece]:
    catalogs: list[tuple[Path, str, bool]] = [
        (repo / "templates" / "FURNITURE.md", "engine base", True)
    ]
    press_catalog = repo / "press" / "furniture" / "catalog.md"
    if press_catalog.is_file():
        catalogs.append((press_catalog, "press shared", False))
    for root in (repo / "templates", repo / "press" / "templates"):
        engine_owned = root == repo / "templates"
        if not root.is_dir():
            continue
        for folder in sorted(root.iterdir()):
            catalog = folder / "furniture.md"
            if catalog.is_file():
                catalogs.append((catalog, f"template · {folder.name}", engine_owned))
    pieces = []
    for path, scope, engine_owned in catalogs:
        pieces.extend(
            parse_catalog(
                path.read_text(encoding="utf-8"), scope, engine_owned=engine_owned
            )
        )
    return pieces


def theme_path(repo: Path) -> Path:
    """The theme the press actually reads, defaulting to the shipped one.

    Mirrors the engine's resolution (site.yaml ``theme:`` over the default)
    without importing engine modules: the gallery only links stylesheets, and
    a wrong link is immediately visible on the page itself.
    """
    site_yaml = repo / "press" / "site.yaml"
    if site_yaml.is_file():
        match = re.search(
            r"^theme:\s*(\S+)", site_yaml.read_text(encoding="utf-8"), re.MULTILINE
        )
        if match:
            return repo / match.group(1).strip("\"'")
    return repo / "engine" / "assets" / "themes" / "newspaper.css"


def stylesheet_links(repo: Path, out: Path) -> str:
    sheets = [repo / "engine" / "assets" / "nb.css", theme_path(repo)]
    sheets.append(repo / "press" / "furniture" / "styles.css")
    for root in (repo / "templates", repo / "press" / "templates"):
        if root.is_dir():
            sheets += sorted(root.glob("*/furniture.css"))
    links = []
    for sheet in sheets:
        if sheet.is_file():
            rel = os.path.relpath(sheet, out.parent)
            links.append(f'<link rel="stylesheet" href="{rel}" />')
    return "\n    ".join(links)


def piece_card(piece: Piece, sample_html: str) -> str:
    return f"""
<section class="gallery-piece" id="{piece.slug}">
  <header class="gallery-piece-head">
    <h2>{piece.name}</h2>
    <span class="gallery-scope">{piece.scope}</span>
  </header>
  <p class="gallery-blurb">{piece.blurb}</p>
  <div class="gallery-render">
{sample_html}
  </div>
</section>"""


def build(repo: Path = REPO, out: Path = DEFAULT_OUT) -> Path:
    pieces = discover_pieces(repo)
    # The engine ships a sample for every piece it owns, and the suite holds
    # that. A press's own furniture renders a placeholder instead of failing:
    # the engine cannot ship samples for components it has never seen.
    missing = [
        p
        for p in pieces
        if p.engine_owned and not (SAMPLES / f"{p.slug}.html").is_file()
    ]
    if missing:
        names = ", ".join(f"{p.scope}: {p.name} ({p.slug}.html)" for p in missing)
        raise SystemExit(f"gallery samples missing for: {names}")

    def sample_of(piece: Piece) -> str:
        path = SAMPLES / f"{piece.slug}.html"
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return (
            '<p style="font-family: var(--mono); font-size: 12px; color: var(--faint)">'
            f"no gallery sample yet — add scripts/gallery/samples/{piece.slug}.html"
            "</p>"
        )

    cards = "\n".join(piece_card(p, sample_of(p)) for p in pieces)
    nb_js = os.path.relpath(repo / "engine" / "assets" / "nb.js", out.parent)
    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Furniture gallery</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400;1,6..72,600&family=Inter:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    />
    {stylesheet_links(repo, out)}
    <style>
      .gallery-main {{ max-width: 680px; margin: 0 auto; padding: 52px 16px 80px; }}
      .gallery-main > h1 {{ font-size: 26px; margin: 0 0 4px; }}
      .gallery-lede {{ color: var(--ink-soft); font-style: italic; margin: 0 0 8px; }}
      .gallery-piece {{ border-top: 2px solid var(--accent); margin-top: 40px; padding-top: 8px; }}
      .gallery-piece-head {{ display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }}
      .gallery-piece-head h2 {{ font-size: 21px; margin: 2px 0 6px; }}
      .gallery-scope {{ font-family: var(--mono); font-size: 11px; color: var(--faint); white-space: nowrap; }}
      .gallery-blurb {{ color: var(--ink-soft); font-size: 15px; margin: 0 0 16px; }}
      .gallery-toggle {{ position: fixed; top: 10px; right: 10px; z-index: 9; font-family: var(--mono);
        font-size: 12px; padding: 6px 10px; background: var(--panel); color: var(--ink);
        border: 1px solid var(--line); border-radius: var(--radius); cursor: pointer; }}
      .gallery-sources {{ margin-top: 48px; color: var(--faint); font-size: 13px; }}
    </style>
  </head>
  <body class="nb-article">
    <button class="gallery-toggle" id="gallery-toggle">mode: auto</button>
    <main class="gallery-main">
      <h1>Furniture gallery</h1>
      <p class="gallery-lede">
        Every catalog piece, isolated, with sample content. Toggle the mode;
        edit CSS and refresh.
      </p>
{cards}
      <div class="gallery-sources">
        Sample citations resolve here so the anchors behave:
        <ol>
          <li id="s1" data-nb-source data-nb-kind="primary">Sample primary source</li>
          <li id="s2" data-nb-source data-nb-kind="secondary">Sample secondary source</li>
          <li id="s3" data-nb-source data-nb-kind="primary">Another sample source</li>
        </ol>
      </div>
    </main>
    <script src="{nb_js}"></script>
    <script>
      (function () {{
        var modes = ["auto", "light", "dark"];
        var button = document.getElementById("gallery-toggle");
        var i = 0;
        button.addEventListener("click", function () {{
          i = (i + 1) % modes.length;
          if (modes[i] === "auto") {{
            document.documentElement.removeAttribute("data-mode");
          }} else {{
            document.documentElement.setAttribute("data-mode", modes[i]);
          }}
          button.textContent = "mode: " + modes[i];
        }});
      }})();
    </script>
  </body>
</html>
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build())
