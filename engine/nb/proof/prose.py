"""The WARN tier: length, cite density, source policy, banned terms, placeholders."""

import re

from nb.article import Article

DEFAULT_MIN_SOURCES = {"longread": 8, "shortread": 5}
DEFAULT_CITE_EXEMPT = ("sources",)  # a template extends this via registry cite_exempt
SELF_COUNT_TOLERANCE = 0.20
PLACEHOLDER_RUN_WORDS = 4  # a caps run this long warns even off-skeleton


def _caps_token(word):
    core = word.strip("\"'()[]{}.,:;!?§·")
    return core if re.fullmatch(r"[A-Z][A-Z0-9'&/-]+", core) else None


def caps_runs(text):
    runs, current = [], []
    for word in text.split():
        core = _caps_token(word)
        if core:
            current.append(core)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def placeholder_entries(skeleton_path):
    """The all-caps placeholder runs a template's skeleton carries.

    Skeletons write placeholder text in caps so it cannot pass as copy; any
    of these runs surviving into an article is an unfilled slot or a lifted
    instruction. Single caps words shorter than three characters are noise,
    not placeholders, and are skipped.
    """
    if not skeleton_path:
        return frozenset()
    with open(skeleton_path, encoding="utf-8") as fh:
        ed = Article()
        ed.feed(fh.read())
        ed.close()
    entries = set()
    for run in caps_runs(" ".join(ed._text_parts)):
        if len(run) >= 2:
            entries.add(" ".join(run))
        elif len(run[0]) >= 3:
            entries.add(run[0])
    return frozenset(entries)


def check_warns(
    ed,
    meta,
    *,
    series,
    treg,
    template_id,
    item_cfg,
    banned_terms,
    skeleton_placeholders,
    rep,
):
    band = series.get("words") or treg.get("words")
    if band:
        lo, hi = band
        if series.get("words"):
            reg_lo = (treg.get("words") or [0])[0]
            lo = max(lo, reg_lo)  # series may tighten, never loosen below registry
        wc = ed.word_count
        if wc < lo:
            rep.warn(
                "W-LENGTH-LOW",
                f"{template_id} band is {lo}-{hi} words; found {wc}",
                suggestion="consider deepening the thinnest section",
            )
        elif wc > hi:
            rep.warn(
                "W-LENGTH-HIGH",
                f"{template_id} band is {lo}-{hi} words; found {wc}",
                suggestion="consider trimming or splitting",
            )
    if treg.get("items"):
        lo, hi = treg["items"]
        n = len(ed.items)
        if n < lo:
            rep.warn(
                "W-LENGTH-LOW",
                f"{template_id} expects {lo}-{hi} items; found {n}",
                suggestion="add an item to reach the band",
            )
        elif n > hi:
            rep.warn(
                "W-LENGTH-HIGH",
                f"{template_id} expects {lo}-{hi} items; found {n}",
                suggestion="cut the weakest item to the band",
            )

    # source floor
    floor = series.get("min_sources") or DEFAULT_MIN_SOURCES.get(
        treg.get("class", "longread"), 5
    )
    if len(ed.sources) < floor:
        rep.warn("W-SOURCES-MIN", f"{len(ed.sources)} sources; series floor is {floor}")

    # cite density
    rule = treg.get("cite_rule")
    if rule == "per-section":
        exempt = set(DEFAULT_CITE_EXEMPT) | set(treg.get("cite_exempt") or ())
        for s in dict.fromkeys(ed.sections):
            if s in exempt:
                continue
            if ed.section_cites.get(s, 0) == 0:
                rep.warn("W-CITE-DENSITY", f"section '{s}' has no inline citations")
    elif rule == "per-item":
        for i, it in enumerate(ed.items, 1):
            if not it["cites"]:
                rep.warn("W-CITE-DENSITY", f"item #{i} has no inline citations")

    # citation order: sources should be numbered in order of first appearance
    if ed.source_ids:
        decl = {sid: i for i, sid in enumerate(ed.source_ids)}
        seen = set()
        frontier = 0
        for target in ed.cite_hrefs:
            if target in seen or target not in decl:
                continue
            seen.add(target)
            if decl[target] != frontier:
                rep.warn(
                    "W-CITE-ORDER",
                    f"citation '#{target}' (source {decl[target] + 1}) is first "
                    f"cited before source {frontier + 1}; number sources in order "
                    "of first appearance",
                )
                break
            frontier += 1

    # source policy: required docs must be read AND cited; consult prefixes
    # must be read first but citing them is optional (no check here); with
    # sources_exclusive, citations may come ONLY from the declared set.
    req_docs = list((item_cfg or {}).get("required_docs") or []) + list(
        series.get("required_docs") or []
    )
    declared_doc_ids = {doc.get("id") for doc in req_docs}
    got_required = {s["required"] for s in ed.sources if s["required"]}
    for doc in req_docs:
        if doc.get("id") not in got_required:
            rep.warn(
                "W-REQ-DOC",
                f"required doc '{doc.get('id')}' has no data-nb-required source entry",
            )
    consult = list(series.get("consult") or []) + list(
        (item_cfg or {}).get("consult") or []
    )
    if series.get("sources_exclusive"):
        for s in ed.sources:
            if s["required"] and s["required"] in declared_doc_ids:
                continue
            if not any(s["href"].startswith(prefix) for prefix in consult):
                rep.block(
                    "B-SOURCES-EXCLUSIVE",
                    f"source outside the declared set: {s['href']}",
                    suggestion="this series is sources_exclusive — cite only "
                    "required_docs and consult sources",
                )

    # self-counts
    if isinstance(meta.get("sources"), int) and ed.sources:
        actual = len(ed.sources)
        if abs(meta["sources"] - actual) > SELF_COUNT_TOLERANCE * max(actual, 1):
            rep.warn(
                "W-SELF-COUNT",
                f"nb-meta sources={meta['sources']} vs counted {actual}",
                suggestion="update nb-meta sources to the counted total",
            )
    if isinstance(meta.get("words"), int):
        actual = ed.word_count
        if actual and abs(meta["words"] - actual) > SELF_COUNT_TOLERANCE * actual:
            rep.warn(
                "W-SELF-COUNT",
                f"nb-meta words={meta['words']} vs counted {actual}",
                suggestion="update nb-meta words to the counted total",
            )

    # banned terms (soft): the lexical tells spec/banned-terms.yaml rules out,
    # extended by press/banned-terms.yaml. Counting covers the rendered text
    # minus the sources section, so a heading counts and a cited title does not.
    raw_prose = " ".join(" ".join(ed._prose_text_parts).split())
    prose = raw_prose.casefold()
    for entry in banned_terms:
        count = sum(prose.count(str(term).casefold()) for term in entry["terms"])
        limit = int(entry.get("max", 0))
        if count > limit:
            rep.warn(
                "W-BANNED-TERM",
                f"'{entry['id']}': {count} uses; the limit is {limit}",
                suggestion=entry.get("suggestion"),
            )

    # leftover placeholders (soft): skeletons write placeholder text in all
    # caps so it cannot pass as copy. A caps run surviving into the prose is
    # an unfilled slot or a lifted instruction; long runs warn even when the
    # skeleton does not carry them, catching lifts from the furniture docs.
    leftovers = set()
    for run in caps_runs(raw_prose):
        joined = " ".join(run)
        if len(run) >= PLACEHOLDER_RUN_WORDS or joined in skeleton_placeholders:
            leftovers.add(joined)
    if leftovers:
        shown = "', '".join(sorted(leftovers)[:4])
        rep.warn(
            "W-PLACEHOLDER",
            f"all-caps placeholder text survives in the prose: '{shown}'",
            suggestion="replace every caps placeholder with the piece's own "
            "words; caps exist so an unfilled slot cannot pass as copy",
        )
