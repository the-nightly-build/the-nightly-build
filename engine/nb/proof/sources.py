"""The sources an article rests on: their form, and the mix a series asks for."""

import re

from nb.links import dead_source_links

SOURCE_KINDS = ("primary", "secondary")


def is_repo_relative_source(href):
    if not href or re.search(r"\s", href):
        return False
    normalized = href.replace("\\", "/")
    is_off_origin = "://" in normalized or normalized.startswith("//")
    return not is_off_origin and not normalized.startswith("/")


def check_sources(ed, rep, *, check_links):
    if not ed.sources:
        rep.block("B-SOURCES-FORM", "no source entries (a[data-nb-source]) found")
    well_formed = []
    for s in ed.sources:
        href = s["href"]
        if re.match(r"^https://[^\s]+$", href or ""):
            well_formed.append(href)
        elif s["required"] and is_repo_relative_source(href):
            continue  # local-file citation (V6a): no public URL to probe
        else:
            rep.block(
                "B-SOURCES-FORM", f"source href must be absolute https URL: {href!r}"
            )
    # B-SOURCE-DEAD: each cited URL must actually resolve (editor gate)
    if check_links:
        for href in dead_source_links(well_formed):
            rep.block(
                "B-SOURCE-DEAD",
                f"source link does not resolve (404 or no such domain): {href}",
            )


def band_text(band) -> str:
    lo, hi = band
    if hi is None:
        return f"at least {lo}"
    if lo == hi:
        return f"exactly {lo}"
    return f"{lo} to {hi}"


def is_count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def kind_bands(bands, *, key, rep) -> dict[str, tuple[int, int | None]]:
    """The series' [low, high] bands per kind, blocking on a malformed config.

    validate_config says all of this in daylight; a press that skipped it gets a
    finding here rather than a traceback.
    """
    if not isinstance(bands, dict):
        rep.block("B-SERIES", f"series '{key}' must be a mapping of kind to band")
        return {}
    resolved = {}
    for kind, band in bands.items():
        if not isinstance(band, list) or len(band) != 2:
            rep.block("B-SERIES", f"series {key}.{kind} must be [low, high]")
            continue
        lo, hi = band
        if not is_count(lo) or (hi is not None and (not is_count(hi) or hi < lo)):
            rep.block(
                "B-SERIES",
                f"series {key}.{kind} must be [low, high]: a count, then null "
                f"or a count no lower than it",
            )
            continue
        resolved[kind] = (lo, hi)
    return resolved


def check_item_kinds(cited, *, number, per_item, rep):
    for kind, band in per_item.items():
        count = sum(1 for s in cited if s["kind"] == kind)
        lo, hi = band
        if count < lo or (hi is not None and count > hi):
            rep.block(
                "B-SOURCE-KIND",
                f"item #{number} cites {count} {kind} source(s); this series "
                f"asks every item for {band_text(band)}",
            )


def check_source_kinds(ed, *, series, treg, rep):
    """B-SOURCE-KIND: source composition, per article and per item.

    min_sources counts. A series can also declare the mix it wants, and the mix
    blocks regardless of `strict`, because sourcing is not a matter of
    calibration. Whether a declared kind is the TRUE kind is judgment: the
    research log makes the call and the editor audits it. The engine counts the
    labels the writer declared, and says nothing about their honesty.
    """
    by_kind = series.get("sources_by_kind")
    per_item = series.get("per_item_sources")
    constrained = by_kind is not None or per_item is not None
    for s in ed.sources:
        if s["kind"] in SOURCE_KINDS:
            continue
        if s["kind"] is not None:
            rep.block(
                "B-SOURCE-KIND",
                f'source {s["href"]} declares data-nb-kind="{s["kind"]}"; '
                f"the kinds are {' and '.join(SOURCE_KINDS)}",
            )
        elif constrained:
            rep.block(
                "B-SOURCE-KIND",
                f"source {s['href']} declares no data-nb-kind; this series "
                f"constrains the source mix, which a source that will not say "
                f"what it is escapes",
            )

    # The mix is what the article rests on, so count what it cites: a listed
    # source no line calls on carries none of the piece.
    cited_ids = set(ed.cite_hrefs)
    cited = [s for s in ed.sources if s["id"] in cited_ids]
    for kind, band in kind_bands(by_kind or {}, key="sources_by_kind", rep=rep).items():
        count = sum(1 for s in cited if s["kind"] == kind)
        lo, hi = band
        if count < lo or (hi is not None and count > hi):
            rep.block(
                "B-SOURCE-KIND",
                f"{count} {kind} source(s) cited; this series asks for "
                f"{band_text(band)}",
            )

    if per_item is None:
        return
    bands = kind_bands(per_item, key="per_item_sources", rep=rep)
    if not bands or treg.get("cite_rule") != "per-item":
        return  # validate_config rejects a series that may cite per section
    by_id = {s["id"]: s for s in ed.sources if s["id"]}
    for number, it in enumerate(ed.items, 1):
        cited = [by_id[ref] for ref in dict.fromkeys(it["cites"]) if ref in by_id]
        check_item_kinds(cited, number=number, per_item=bands, rep=rep)
