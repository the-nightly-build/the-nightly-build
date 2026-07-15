"""What the build copies into the site: the assets, and the article copies.

The shared stylesheet, the concatenated theme, and the content hash that
stamps them; and the article copies, which are the canonical library files
with their asset links stamped and the site chrome spliced in. The canonical
files on the library branch stay byte-exact.
"""

import hashlib
import os
import re
import shutil

from nb.site.pages import chrome_footer, chrome_header


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def asset_stamp(repo, css_paths=()):
    """Return a short content hash of the shared assets for cache busting.

    Every generated page and article copy links assets with ?v=<stamp>,
    so a returning reader can never pair cached old CSS with newer markup.
    The stamp folds in nb.css, nb.js, and every CSS owner concatenated
    into assets/theme.css (the configured theme plus all furniture, shared
    and template-scoped). copy_assets rebuilds theme.css from those owners
    every build, so editing any of them busts the reader's cache and the
    new look actually reaches them.
    """
    h = hashlib.md5()
    base = os.path.join(repo, "engine", "assets")
    paths = [os.path.join(base, "nb.css"), os.path.join(base, "nb.js"), *css_paths]
    for path in paths:
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:10]


def template_dirs(repo):
    """Map each template id to its resolved folder, press shadowing shipped.

    A template is a folder holding a manifest.yaml (the folder name is the
    id); a press/templates/<id> package replaces a shipped one of the same
    id wholesale. A folder without a manifest.yaml is not a template and is
    skipped, so a stray asset left beside the packages is ignored.
    """
    dirs = {}
    for base in (
        os.path.join(repo, "templates"),
        os.path.join(repo, "press", "templates"),  # press shadows shipped
    ):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if os.path.isfile(os.path.join(folder, "manifest.yaml")):
                dirs[name] = folder
    return dirs


def css_owners(repo, site_cfg):
    """Every CSS file concatenated into the published assets/theme.css.

    Deterministically ordered so the cascade is stable and a later owner
    can lean on tokens an earlier one defines: the site theme first, then
    the shared press furniture, then each template's bespoke furniture in
    id order. Missing optional files are filtered out.
    """
    owners = [os.path.join(repo, site_cfg["theme"])]
    owners.append(os.path.join(repo, "press", "furniture", "styles.css"))
    for _id, folder in sorted(template_dirs(repo).items()):
        owners.append(os.path.join(folder, "furniture.css"))
    return [path for path in owners if os.path.isfile(path)]


def copy_assets(repo, site_cfg, *, out):
    src = os.path.join(repo, "engine", "assets")
    dst = os.path.join(out, "assets")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    # Every CSS owner is concatenated under the stable name assets/theme.css:
    # the configured theme plus all furniture (shared and template-scoped). The
    # output name never changes, so page links and article copies need no edit,
    # and a theme or furniture change restyles every already-published article.
    blocks = []
    for path in css_owners(repo, site_cfg):
        with open(path, encoding="utf-8") as fh:
            blocks.append(
                f"/* --- {os.path.basename(path)} --- */\n{fh.read().rstrip()}"
            )
    write(os.path.join(dst, "theme.css"), "\n\n".join(blocks) + "\n")


ARTICLE_ASSET_RE = re.compile(
    r'((?:href|src)="(?:\.\./)*assets/(?:nb\.css|nb\.js|theme\.css))(")'
)
BODY_OPEN_RE = re.compile(r"<body\b[^>]*>", re.IGNORECASE)

# Site copies of articles live at library/<series>/<slug>.html.
ARTICLE_DEPTH = 2


def dress_article(raw, site):
    """Return the article markup with the site chrome and press assets in place.

    An article is authored as a standalone page, so the bar and footer that
    generated pages get from page() are spliced in here, at copy time: the same
    Python builds both, and the whole back catalogue wears the current chrome on
    the next build. Idempotent, so an article that already carries a bar (an
    already-dressed copy handed back in) is left with exactly one.
    """
    if site["assets_html"]:
        raw = raw.replace("</head>", f"{site['assets_html']}\n</head>", 1)
    body_open = BODY_OPEN_RE.search(raw)
    if not body_open or 'class="nb-bar"' in raw:
        return raw
    header = chrome_header(site, depth=ARTICLE_DEPTH)
    at = body_open.end()
    raw = f"{raw[:at]}\n{header}{raw[at:]}"
    return raw.replace("</body>", f"{chrome_footer(site)}\n</body>", 1)


def copy_articles(articles, out, *, site):
    """Copy articles into the site, stamping their shared-asset links and
    dressing each copy in the site chrome.

    The canonical files on the library branch stay byte-exact; only the
    generated site copy gets ?v=<stamp> on nb.css, nb.js, and theme.css so
    cached assets can never mismatch the markup, the press assets so
    library-backed furniture (a highlighter, say) works in every article, and
    the reader chrome so an article is a page of this paper.
    """
    for ed in articles.values():
        dst = os.path.join(out, "library", ed["series"], f"{ed['slug']}.html")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(ed["file"], encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        if site["stamp"]:
            raw = ARTICLE_ASSET_RE.sub(rf"\1?v={site['stamp']}\2", raw)
        write(dst, dress_article(raw, site))
        source_assets = os.path.join(os.path.dirname(ed["file"]), ed["slug"])
        if os.path.isdir(source_assets):
            shutil.copytree(
                source_assets,
                os.path.join(os.path.dirname(dst), ed["slug"]),
                dirs_exist_ok=True,
            )
