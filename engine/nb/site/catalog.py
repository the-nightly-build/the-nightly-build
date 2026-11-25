"""Build ``catalog.json`` from the library's rendered article state.

The catalog is what every other reader of this press consumes — the search
page, the directory, another paper's tooling — so the series, the articles,
the nights, and the tags are all derived here, once, from the same article
dicts the pages render from. Tag safety is shared with article validation;
otherwise a valid nested tag could be omitted during generation or an unsafe
tag could reach the output-directory builder.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from nb import meta as nb_meta
from nb.site.library import date_sort_key, night_date

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Mapping

PROTOCOL = "1.3"
UPSTREAM_REPOSITORY = os.getenv("UPSTREAM_REPOSITORY", "the-nightly-build/the-nightly-build")
DIRECTORY_URL = os.getenv("DIRECTORY_URL", "https://the-nightly-build.github.io/")

__all__ = ("build_catalog", "derive_self_repository", "is_safe_tag")


def derive_self_repository(explicit: str | None, base_url: str | None) -> str | None:
    if explicit:
        return explicit
    # Parse a Pages project URL https://<owner>.github.io/<repo>/; a user or org
    # Pages site has no repo path, so this yields None and chrome omits the star link.
    match = re.match(r"https?://([^./]+)\.github\.io/([^/]+)", base_url or "")
    return f"{match.group(1)}/{match.group(2)}" if match else None


is_safe_tag = nb_meta.is_safe_tag


def _series_entries(series_cfgs: Mapping[str, dict], by_series: Mapping[str, list[dict]]) -> list[dict]:
    entries = []
    for sid, cfg in series_cfgs.items():
        items = cfg.get("items") or []
        entry = {
            "id": sid,
            "name": cfg.get("name", sid),
            "mode": cfg.get("mode"),
            "template": cfg.get("template"),
            "count": len(by_series.get(sid, [])),
            "total": len(items) if cfg.get("mode") in ("collection", "sequence") else None,
        }
        for key in ("templates", "cadence", "paused", "section"):
            if cfg.get(key):
                entry[key] = cfg[key]
        entries.append(entry)
    # articles published for series no longer configured still belong to the site
    for sid in sorted(set(by_series) - set(series_cfgs)):
        eds = by_series[sid]
        entries.append(
            {
                "id": sid,
                "name": sid,
                "mode": eds[0]["meta"].get("mode"),
                "template": eds[0]["meta"].get("template"),
                "count": len(eds),
                "total": None,
            }
        )
    return entries


def _article_entries(articles: Mapping[tuple[str, str], dict]) -> list[dict]:
    entries = []
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
        entries.append(entry)
    return entries


def _build_buckets(
    articles: Mapping[tuple[str, str], dict],
) -> dict[str, list[str]]:
    builds: dict[str, list[str]] = {}
    for ed in articles.values():
        d = night_date(ed["meta"])
        builds.setdefault(d, []).append(f"{ed['series']}/{ed['slug']}")
    return {d: sorted(v) for d, v in sorted(builds.items(), key=lambda kv: date_sort_key(kv[0]), reverse=True)}


def _tag_buckets(
    articles: Mapping[tuple[str, str], dict],
) -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    for ed in articles.values():
        for t in ed["meta"].get("tags") or []:
            if not is_safe_tag(t):
                continue
            tags.setdefault(t, []).append(f"{ed['series']}/{ed['slug']}")
    return {t: sorted(v) for t, v in sorted(tags.items())}


def _directory_entry(site_cfg: Mapping[str, object]) -> dict[str, object]:
    # Listing on the directory is opt-out: a paper is listed unless it sets
    # directory.publish: false. The block carries only that signal and an optional
    # description; the public URL is never in the catalog. The directory derives
    # each paper's URL from GitHub identity, so no catalog field can point a
    # reader off the paper's own site.
    directory = site_cfg.get("directory")
    if not isinstance(directory, dict):
        directory = {}
    if directory.get("publish") is False:
        return {"publish": False}
    description = directory.get("description")
    return {
        "publish": True,
        "description": description.strip() if isinstance(description, str) else "",
    }


def build_catalog(
    site_cfg: dict,
    series_cfgs: Mapping[str, dict],
    *,
    articles: Mapping[tuple[str, str], dict],
    by_series: Mapping[str, list[dict]],
    generated: dt.datetime,
    repository: str | None = None,
) -> dict:
    return {
        "generated": generated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": PROTOCOL,
        "site_title": site_cfg["title"],
        "footer": site_cfg.get("footer"),
        "repository": repository,
        "upstream": UPSTREAM_REPOSITORY,
        "directory_url": DIRECTORY_URL,
        "series": _series_entries(series_cfgs, by_series),
        "articles": _article_entries(articles),
        "builds": _build_buckets(articles),
        "tags": _tag_buckets(articles),
        "directory": _directory_entry(site_cfg),
    }
