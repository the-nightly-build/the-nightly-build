"""Reading a built site back: the pages, the chrome, and the cache stamp."""

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

STAMP_RE = re.compile(r"nb\.css\?v=([0-9a-f]+)")


@dataclasses.dataclass(frozen=True)
class Site:
    """A site the builder wrote, plus the catalog it returned."""

    catalog: dict
    out: str
    library: str

    def read(self, *parts: str) -> str:
        return pathlib.Path(self.out, *parts).read_text()

    def read_library(self, *parts: str) -> str:
        return pathlib.Path(self.library, *parts).read_text()

    def exists(self, *parts: str) -> bool:
        return pathlib.Path(self.out, *parts).is_file()

    @property
    def index(self) -> str:
        return self.read("index.html")

    @property
    def stamp(self) -> str:
        return asset_stamp_of(self.index)


def build_press(repo: str, library: str, **kwargs) -> Site:
    """Build a press into a fresh directory, on the fixture's night."""
    out = tempfile.mkdtemp()
    kwargs.setdefault("now", NOW)
    catalog = build_site.build(repo, library, out=out, **kwargs)
    return Site(catalog=catalog, out=out, library=library)


def asset_stamp_of(page_html: str) -> str:
    m = STAMP_RE.search(page_html)
    assert m is not None, "no asset stamp in page"
    return m.group(1)


def undress(article_html: str) -> str:
    """An article copy with the spliced chrome removed."""
    return CHROME_RE.sub("", article_html)
