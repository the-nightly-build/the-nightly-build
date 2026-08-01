"""Reading a built site back: the pages, the chrome, and the cache stamp.

The helpers give site tests one stable view of generated output. ``undress``
removes only build-time additions so a copied article can be compared byte for
byte with its canonical library source.
"""

import dataclasses
import pathlib
import re
import tempfile

import build_site
from press import NOW

# Strips the chrome the builder splices into an article copy. What remains must
# be the canonical article byte for byte, which is what the proof validates.
CHROME_RE = re.compile(
    r'\n<header class="nb-bar">.*?</header>|<footer class="nb-footer">.*?</footer>\n',
    re.S,
)
SITE_ICON_RE = re.compile(
    r'<link rel="(?:icon|apple-touch-icon)"[^>]* '
    r'href="\.\./\.\./assets/(?:favicon-(?:32|64)|apple-touch-icon)\.png'
    r'\?v=[0-9a-f]+">\n'
)
STAMP_RE = re.compile(r"nb\.css\?v=([0-9a-f]+)")


@dataclasses.dataclass(frozen=True)
class Site:
    catalog: dict
    out: str
    library: str

    def read(self, *parts: str) -> str:
        page = pathlib.Path(self.out, *parts)
        return page.read_text()

    def read_library(self, *parts: str) -> str:
        article = pathlib.Path(self.library, *parts)
        return article.read_text()

    def exists(self, *parts: str) -> bool:
        path = pathlib.Path(self.out, *parts)
        return path.is_file()

    @property
    def index(self) -> str:
        index_path = pathlib.Path(self.out, "index.html")
        return index_path.read_text()

    @property
    def stamp(self) -> str:
        index_html = self.index
        return asset_stamp_of(index_html)


def build_press(repo: str, library: str, **kwargs) -> Site:
    out = tempfile.mkdtemp()
    kwargs.setdefault("now", NOW)
    catalog = build_site.build(repo, library, out=out, **kwargs)
    return Site(catalog=catalog, out=out, library=library)


def asset_stamp_of(page_html: str) -> str:
    m = STAMP_RE.search(page_html)
    assert m is not None, "no asset stamp in page"
    return m.group(1)


def undress(article_html: str) -> str:
    without_chrome = CHROME_RE.sub("", article_html)
    return SITE_ICON_RE.sub("", without_chrome)
