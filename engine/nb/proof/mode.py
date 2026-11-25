"""Check what the series mode allows an article to publish.

The mode proof owns slug admission, ordering, configured commissions, and
published-state deduplication. Cadence normally belongs to the scheduler; the
manual-open exception is checked here because each manually commissioned slug
must be explicit configuration before CI accepts it.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from nb.proof.meta import DATE_RE

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from nb.report import Report

__all__ = (
    "check_mode",
    "check_open_slug",
    "check_ordered_mode",
    "check_rolling_mode",
    "check_sequence_slug",
)


def check_sequence_slug(
    meta: Mapping[str, object],
    *,
    items: Sequence[Mapping[str, object]],
    idx: int,
    slug: str,
    pub: set[str] | None,
    revision: bool,
    rep: Report,
) -> None:
    if revision:
        if meta.get("order") != idx + 1:
            rep.block(
                "B-MODE",
                f"sequence order must be item position {idx + 1}; nb-meta says {meta.get('order')}",
            )
        return
    if pub is None:
        if meta.get("order") != idx + 1:
            rep.block(
                "B-MODE",
                f"sequence order must be item position {idx + 1}; nb-meta says {meta.get('order')}",
            )
        rep.notes.append("library state not provided (--library); next-expected check skipped")
        return
    expected = next((i for i, it in enumerate(items) if it.get("slug") not in pub), None)
    if expected is None:
        rep.block("B-MODE", "sequence is complete; nothing to publish")
    elif idx != expected:
        rep.block(
            "B-MODE",
            f"next expected sequence item is '{items[expected].get('slug')}' (#{expected + 1}), not '{slug}'",
        )
    elif meta.get("order") != expected + 1:
        rep.block(
            "B-MODE",
            f"nb-meta order must be {expected + 1}, got {meta.get('order')}",
        )


def check_ordered_mode(
    meta: Mapping[str, object],
    *,
    series_id: str,
    items: Sequence[Mapping[str, object]],
    slug: str,
    pub: set[str] | None,
    mode: str,
    revision: bool,
    rep: Report,
) -> Mapping[str, object] | None:
    idx = next((i for i, it in enumerate(items) if it.get("slug") == slug), None)
    if idx is None:
        if revision:
            # published is a fact: revising never requires the item's config
            return None
        rep.block(
            "B-SLUG",
            f"slug '{slug}' is not a configured item of series '{series_id}'",
        )
        return None
    item_cfg = items[idx]
    if mode == "sequence":
        check_sequence_slug(
            meta,
            items=items,
            idx=idx,
            slug=slug,
            pub=pub,
            revision=revision,
            rep=rep,
        )
    elif not revision and pub is not None and slug in pub:
        rep.block("B-MODE", f"'{slug}' is already published")
    return item_cfg


def check_rolling_mode(
    meta: Mapping[str, object],
    *,
    slug: str,
    pub: set[str] | None,
    today: dt.date,
    revision: bool,
    rep: Report,
) -> None:
    if not DATE_RE.match(slug):
        rep.block("B-SLUG", f"rolling slug must be YYYY-MM-DD, got '{slug}'")
    else:
        try:
            d = dt.date.fromisoformat(slug)
            if d > today:
                rep.block("B-SLUG", f"rolling slug {slug} is in the future")
        except ValueError:
            rep.block("B-SLUG", f"rolling slug '{slug}' is not a real date")
        if meta.get("date") != slug:
            rep.block(
                "B-META-MATCH",
                f"rolling nb-meta date '{meta.get('date')}' must equal slug",
            )
        if not revision and pub is not None and slug in pub:
            rep.block("B-MODE", f"a brief for {slug} is already published")
    if pub is None:
        rep.notes.append("library state not provided (--library); already-published check skipped")


def check_open_slug(
    *,
    items: Sequence[Mapping[str, object]],
    slug: str,
    pub: set[str] | None,
    manual: bool,
    revision: bool,
    rep: Report,
) -> Mapping[str, object] | None:
    item_cfg = next((it for it in items if it.get("slug") == slug), None)
    if revision:
        # published is a fact: revising never requires the item's config
        return item_cfg
    if pub is None:
        rep.notes.append("library state not provided (--library); open-mode dedupe and commission checks skipped")
        return item_cfg
    if slug in pub:
        rep.block("B-MODE", f"'{slug}' is already published")
    if manual:
        # a manual series only ever publishes what a person asked for, so
        # its items are suggestions and never gate the slug
        return item_cfg
    pending = sorted(item_slug for it in items if isinstance(item_slug := it.get("slug"), str) and item_slug not in pub)
    if pending and slug not in pending:
        rep.block(
            "B-MODE",
            f"commissioned items pending: {pending} — publish a commission before an open pick",
        )
    return item_cfg


def check_mode(
    meta: Mapping[str, object],
    *,
    series: Mapping[str, object],
    series_id: str,
    slug: str,
    pub: set[str] | None,
    today: dt.date,
    revision: bool = False,
    rep: Report,
) -> Mapping[str, object] | None:
    mode = series.get("mode")
    raw_items = series.get("items")
    items: list[dict[str, object]] = (
        [{str(key): value for key, value in it.items()} for it in raw_items if isinstance(it, dict)]
        if isinstance(raw_items, list)
        else []
    )
    if mode in ("collection", "sequence"):
        return check_ordered_mode(
            meta,
            series_id=series_id,
            items=items,
            slug=slug,
            pub=pub,
            mode=str(mode),
            revision=revision,
            rep=rep,
        )
    if mode == "rolling":
        check_rolling_mode(
            meta,
            slug=slug,
            pub=pub,
            today=today,
            revision=revision,
            rep=rep,
        )
        return None
    if mode == "open":
        return check_open_slug(
            items=items,
            slug=slug,
            pub=pub,
            manual=series.get("cadence") == "manual",
            revision=revision,
            rep=rep,
        )
    return None
