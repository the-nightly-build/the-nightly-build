"""catalog.json: the library's state, machine-readable.

The catalog is what every other reader of this press consumes — the search
page, the directory, another paper's tooling — so the series, the articles,
the nights, and the tags are all derived here, once, from the same article
dicts the pages render from.
"""

import os
import re

from nb.site.library import date_sort_key, night_date

PROTOCOL = "1.3"
UPSTREAM_REPOSITORY = os.getenv(
    "UPSTREAM_REPOSITORY", "the-nightly-build/the-nightly-build"
)
DIRECTORY_URL = os.getenv("DIRECTORY_URL", "https://the-nightly-build.github.io/")


def derive_self_repository(explicit, base_url) -> str | None:
    if explicit:
        return explicit
    # Parse a Pages project URL https://<owner>.github.io/<repo>/; a user or org
    # Pages site has no repo path, so this yields None and chrome omits the star link.
    match = re.match(r"https?://([^./]+)\.github\.io/([^/]+)", base_url or "")
    return f"{match.group(1)}/{match.group(2)}" if match else None


def is_safe_tag(tag):
    """Whether a tag can be turned into a tags/<tag>/index.html page safely.

    Tags are untrusted (they come from auto-merged night-shift content and
    check.py does not constrain them), and the builder writes each one as a
    directory under tags/. A tag whose segments escape that tree — `..`,
    `.`, an absolute path, a backslash, or an empty segment from a leading/
    trailing/double slash — is dropped from the catalog entirely, so no
    page, link, or os.makedirs is ever created outside --out. A plain
    nested tag like `a/b` is safe and renders at its true depth.
    """
    if not isinstance(tag, str) or not tag or tag != tag.strip():
        return False
    if "\\" in tag or tag.startswith("/"):
        return False
    return all(seg and seg not in (".", "..") for seg in tag.split("/"))


def build_catalog(
    site_cfg, series_cfgs, *, articles, by_series, generated, repository=None
):
    series_entries = []
    for sid, cfg in series_cfgs.items():
        items = cfg.get("items") or []
        entry = {
            "id": sid,
            "name": cfg.get("name", sid),
            "mode": cfg.get("mode"),
            "template": cfg.get("template"),
            "count": len(by_series.get(sid, [])),
            "total": len(items)
            if cfg.get("mode") in ("collection", "sequence")
            else None,
        }
        for key in ("templates", "cadence", "paused", "section"):
            if cfg.get(key):
                entry[key] = cfg[key]
        series_entries.append(entry)
    # articles published for series no longer configured still belong to the site
    for sid in sorted(set(by_series) - set(series_cfgs)):
        eds = by_series[sid]
        series_entries.append(
            {
                "id": sid,
                "name": sid,
                "mode": eds[0]["meta"].get("mode"),
                "template": eds[0]["meta"].get("template"),
                "count": len(eds),
                "total": None,
            }
        )

    article_entries = []
    for ed in sorted(
        articles.values(),
        key=lambda e: (e["meta"].get("date", ""), e["series"], e["slug"]),
        reverse=True,
    ):
        entry = dict(ed["meta"])
        entry["path"] = f"/library/{ed['series']}/{ed['slug']}.html"
        entry["position"] = ed["position"]
        entry["reading_minutes"] = ed["reading_minutes"]
        if ed["draft"]:
            entry["draft"] = True
        article_entries.append(entry)

    builds = {}
    for ed in articles.values():
        d = night_date(ed["meta"])
        builds.setdefault(d, []).append(f"{ed['series']}/{ed['slug']}")
    builds = {
        d: sorted(v)
        for d, v in sorted(
            builds.items(), key=lambda kv: date_sort_key(kv[0]), reverse=True
        )
    }

    tags = {}
    for ed in articles.values():
        for t in ed["meta"].get("tags") or []:
            if not is_safe_tag(t):
                continue
            tags.setdefault(t, []).append(f"{ed['series']}/{ed['slug']}")
    tags = {t: sorted(v) for t, v in sorted(tags.items())}

    catalog = {
        "generated": generated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": PROTOCOL,
        "site_title": site_cfg["title"],
        "footer": site_cfg.get("footer"),
        "repository": repository,
        "upstream": UPSTREAM_REPOSITORY,
        "directory_url": DIRECTORY_URL,
        "series": series_entries,
        "articles": article_entries,
        "builds": builds,
        "tags": tags,
    }
    # Listing on the directory is opt-out: a paper is listed unless it sets
    # directory.publish: false. The block carries only that signal and an optional
    # description; the public URL is never in the catalog. The directory derives
    # each paper's URL from GitHub identity, so no catalog field can point a
    # reader off the paper's own site.
    directory = site_cfg.get("directory") or {}
    if directory.get("publish") is False:
        catalog["directory"] = {"publish": False}
    else:
        catalog["directory"] = {
            "publish": True,
            "description": (directory.get("description") or "").strip(),
        }
    return catalog
