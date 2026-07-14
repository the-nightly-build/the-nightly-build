"""The Atom feeds: one for the paper, one per series.

The newest FEED_CONTENT_LIMIT entries carry the full article body, stripped
of scripts and styles and with its links absolutized, so a reader who
subscribes gets the piece and not a teaser.
"""

import html
import re

from nb.site.library import article_body_html

esc = html.escape

FEED_LIMIT = 50
FEED_CONTENT_LIMIT = 10  # newest N entries carry full content
FEED_CONTENT_MAX = 150_000  # per-entry cap after stripping, bytes

FEED_STRIP_RE = re.compile(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", re.I)
HREF_RE = re.compile(r'((?:href|src)=")([^"]+)(")', re.I)


def absolutize_url(base_url, path):
    return f"{base_url}{path}" if base_url else path


def feed_content_html(path, base_url):
    """Return the article body as a feed-safe HTML fragment.

    Scripts, styles, and comments are stripped so feed readers get
    content, not code. When a base URL is known, relative hrefs are
    absolutized; oversized bodies return empty so the entry falls back
    to its summary.
    """
    body = FEED_STRIP_RE.sub(" ", article_body_html(path))

    def absolutize(match):
        pre, url, post = match.groups()
        if base_url and url.startswith("../"):
            return f"{pre}{base_url}/{url.replace('../', '')}{post}"
        if base_url and url.startswith("/"):
            return f"{pre}{base_url}{url}{post}"
        return match.group(0)

    body = HREF_RE.sub(absolutize, body)
    return body if len(body) <= FEED_CONTENT_MAX else ""


def feed_tag_id(base_url, resource, *, year):
    """A globally-unique, stable Atom id for a feed or entry.

    When the paper has a base_url its id is an RFC 4151 tag: IRI whose
    authority is the paper's own domain and whose specific part is the
    resource path under it, so two independent papers — even two on the
    same host under different paths, or two publishing the same
    series/slug — never collide (the constant urn:nightly-build: ids they
    replace were byte-identical across papers). With no base_url (a local
    build) it falls back to that urn scheme, which is fine offline.
    """
    match = re.match(r"https?://([^/]+)(/.*)?$", base_url or "")
    if not match:
        return f"urn:nightly-build:{resource}"
    host = match.group(1)
    prefix = (match.group(2) or "").strip("/")
    specific = f"{prefix}/{resource}".strip("/")
    return f"tag:{host},{year}:{specific}"


def entry_year(meta, generated):
    date = meta.get("date")
    if isinstance(date, str) and len(date) >= 4 and date[:4].isdigit():
        return date[:4]
    return generated.strftime("%Y")


def atom_feed(base_url, feed_path, *, title, eds, generated, author=None):
    author = author or title

    def absolute(path):
        return absolutize_url(base_url, path)

    entries = []
    for i, ed in enumerate(eds[:FEED_LIMIT]):
        meta = ed["meta"]
        link = absolute(f"/library/{ed['series']}/{ed['slug']}.html")
        updated = f"{meta.get('date', generated.date().isoformat())}T00:00:00Z"
        entry_id = feed_tag_id(
            base_url,
            f"library/{ed['series']}/{ed['slug']}",
            year=entry_year(meta, generated),
        )
        content = ""
        if i < FEED_CONTENT_LIMIT:
            fragment = feed_content_html(ed["file"], base_url)
            if fragment:
                content = '\n    <content type="html">' + esc(fragment) + "</content>"
        entries.append(f"""  <entry>
    <title>{esc(str(meta.get("title", ed["slug"])))}</title>
    <link rel="alternate" type="text/html" href="{esc(link)}"/>
    <id>{esc(entry_id)}</id>
    <updated>{updated}</updated>
    <summary>{esc(str(meta.get("dek", "")))}</summary>{content}
    <category term="{esc(ed["series"])}"/>
  </entry>""")
    self_link = absolute(f"/{feed_path}")
    feed_id = feed_tag_id(base_url, feed_path, year=generated.strftime("%Y"))
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{esc(title)}</title>
  <link rel="self" type="application/atom+xml" href="{esc(self_link)}"/>
  <link rel="alternate" type="text/html" href="{esc(absolute("/") or "/")}"/>
  <id>{esc(feed_id)}</id>
  <author><name>{esc(author)}</name></author>
  <updated>{generated.strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>
{chr(10).join(entries)}
</feed>
"""
