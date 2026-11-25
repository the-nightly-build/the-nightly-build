"""The WARN tier: length, cite density, source policy, banned terms, placeholders.

These checks deliberately advise rather than block: their role is to expose thin
or awkward articles to the editor while preserving the hard safety contract in
the other proof modules. Template defaults live here because they shape quality.
"""

from __future__ import annotations

import pathlib
import re
from typing import TYPE_CHECKING

from nb.article import Article
from nb.source_policy import minimum

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from nb.report import Report

__all__ = (
    "caps_runs",
    "check_warns",
    "placeholder_entries",
    "sentence_density",
)

DEFAULT_CITE_EXEMPT = ("sources",)  # a template extends this via registry cite_exempt
SELF_COUNT_TOLERANCE = 0.20
PLACEHOLDER_RUN_WORDS = 4  # a caps run this long warns even off-skeleton
MIN_RUN_WORDS = 2
MIN_SINGLE_WORD_LEN = 3
MAX_SHOWN_LEFTOVERS = 4
BAND_LEN = 2
SENTENCE_WORDS = re.compile(r"\b[\w]+(?:[\u2019'-][\w]+)*\b")
SENTENCE_END = re.compile(r"(?<=[.!?])[\"'”\u2019)\]]*(?=\s|$)")
CLAUSE_JOIN = re.compile(
    r"(?:,\s*(?:and|but|or|nor|yet|so|for|which|that|where|when)\b"
    r"|;\s*|:\s*|\b(?:although|because|while|whereas|unless)\b)",
    re.IGNORECASE,
)
PUNCTUATION_WEIGHTS = {
    ",": 1,
    ";": 2,
    ":": 2,
    "—": 2,
    "\u2013": 1,
    "(": 1,
    ")": 1,
    "[": 1,
    "]": 1,
    "{": 1,
    "}": 1,
}
MIN_SENTENCE_WORDS = 40
LONG_SENTENCE_WORDS = 55
MIN_CLAUSE_JOINS = 2
MAX_PUNCTUATION_SCORE = 6


def _caps_token(word: str) -> str | None:
    core = word.strip("\"'()[]{}.,:;!?§·")
    return core if re.fullmatch(r"[A-Z][A-Z0-9'&/-]+", core) else None


def caps_runs(text: str) -> list[list[str]]:
    runs: list[list[str]] = []
    current: list[str] = []
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


def placeholder_entries(
    skeleton_path: str | pathlib.Path | None,
) -> frozenset[str]:
    """Return the all-caps placeholder runs a template's skeleton carries.

    Skeletons write placeholder text in caps so it cannot pass as copy; any
    of these runs surviving into an article is an unfilled slot or a lifted
    instruction. Single caps words shorter than three characters are noise,
    not placeholders, and are skipped.
    """
    if not skeleton_path:
        return frozenset()
    ed = Article()
    ed.feed(pathlib.Path(skeleton_path).read_text(encoding="utf-8"))
    ed.close()
    entries: set[str] = set()
    for run in caps_runs(" ".join(ed.text_parts)):
        if len(run) >= MIN_RUN_WORDS:
            entries.add(" ".join(run))
        elif len(run[0]) >= MIN_SINGLE_WORD_LEN:
            entries.add(run[0])
    return frozenset(entries)


def sentence_density(text: str) -> list[tuple[str, int, int, int]]:
    """Return long, structurally dense sentences as text and counts.

    This is deliberately a conservative surface heuristic, not a grammar
    parser. It considers word count, clause joins, and weighted internal
    punctuation without proposing a semantic split point.
    """
    dense: list[tuple[str, int, int, int]] = []
    for block in text.splitlines():
        sentences = [part.strip() for part in SENTENCE_END.split(block) if part.strip()]
        for sentence in sentences:
            words = len(SENTENCE_WORDS.findall(sentence))
            if words < MIN_SENTENCE_WORDS:
                continue
            joins = len(CLAUSE_JOIN.findall(sentence))
            punctuation = sum(PUNCTUATION_WEIGHTS.get(mark, 0) for mark in sentence)
            if words >= LONG_SENTENCE_WORDS or joins >= MIN_CLAUSE_JOINS or punctuation >= MAX_PUNCTUATION_SCORE:
                dense.append((sentence, words, joins, punctuation))
    return dense


def _int_band(value: object) -> tuple[int, int] | None:
    if isinstance(value, list) and len(value) == BAND_LEN and isinstance(value[0], int) and isinstance(value[1], int):
        return value[0], value[1]
    return None


def _check_length_bands(
    ed: Article,
    *,
    treg: Mapping[str, object],
    template_id: str,
    rep: Report,
) -> None:
    raw_bands = treg.get("bands")
    if not isinstance(raw_bands, dict):
        return
    bands = {str(key): value for key, value in raw_bands.items()}
    word_band = _int_band(bands.get("words"))
    if word_band is not None:
        lo, hi = word_band
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
    item_band = _int_band(bands.get("items"))
    if item_band is not None:
        lo, hi = item_band
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


def _check_sentence_density(ed: Article, rep: Report) -> None:
    for _sentence, words, joins, punctuation in sentence_density(" ".join(ed.sentence_text_parts)):
        notes: list[str] = []
        if joins:
            label = "clause join" if joins == 1 else "clause joins"
            notes.append(f"{joins} {label}")
        if punctuation >= MAX_PUNCTUATION_SCORE:
            notes.append(f"punctuation score {punctuation}")
        density_note = f" with {', '.join(notes)}" if notes else ""
        rep.warn(
            "W-SENTENCE-DENSITY",
            f"sentence is {words} words{density_note}",
            suggestion="consider splitting it into multiple sentences",
            promote=False,
        )


def _check_cite_density(ed: Article, *, treg: Mapping[str, object], rep: Report) -> None:
    rule = treg.get("cite_rule")
    if rule == "per-section":
        raw_exempt = treg.get("cite_exempt")
        extra_exempt = [str(item) for item in raw_exempt] if isinstance(raw_exempt, list) else []
        exempt = set(DEFAULT_CITE_EXEMPT) | set(extra_exempt)
        for s in dict.fromkeys(ed.sections):
            if s in exempt:
                continue
            if ed.section_cites.get(s, 0) == 0:
                rep.warn("W-CITE-DENSITY", f"section '{s}' has no inline citations")
    elif rule == "per-item":
        for i, it in enumerate(ed.items, 1):
            if not it["cites"]:
                rep.warn("W-CITE-DENSITY", f"item #{i} has no inline citations")


def _check_cite_order(ed: Article, rep: Report) -> None:
    if not ed.source_ids:
        return
    decl = {sid: i for i, sid in enumerate(ed.source_ids)}
    seen: set[str] = set()
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
            return
        frontier += 1


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [{str(key): item for key, item in entry.items()} for entry in value if isinstance(entry, dict)]


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _check_source_policy(
    ed: Article,
    *,
    series: Mapping[str, object],
    item_cfg: Mapping[str, object] | None,
    rep: Report,
) -> None:
    # source policy: required docs must be read AND cited; consult prefixes
    # must be read first but citing them is optional (no check here); with
    # sources_exclusive, citations may come ONLY from the declared set.
    req_docs = _dict_list((item_cfg or {}).get("required_docs")) + _dict_list(series.get("required_docs"))
    declared_doc_ids = {doc.get("id") for doc in req_docs}
    got_required = {s["required"] for s in ed.sources if s["required"]}
    for doc in req_docs:
        if doc.get("id") not in got_required:
            rep.warn(
                "W-REQ-DOC",
                f"required doc '{doc.get('id')}' has no data-nb-required source entry",
            )
    consult = _str_list(series.get("consult")) + _str_list((item_cfg or {}).get("consult"))
    if not series.get("sources_exclusive"):
        return
    for s in ed.sources:
        if s["required"] and s["required"] in declared_doc_ids:
            continue
        if not any(s["href"].startswith(prefix) for prefix in consult):
            rep.block(
                "B-SOURCES-EXCLUSIVE",
                f"source outside the declared set: {s['href']}",
                suggestion="this series is sources_exclusive — cite only required_docs and consult sources",
            )


def _check_self_counts(ed: Article, meta: Mapping[str, object], *, rep: Report) -> None:
    meta_sources = meta.get("sources")
    if isinstance(meta_sources, int) and ed.sources:
        actual = len(ed.sources)
        if abs(meta_sources - actual) > SELF_COUNT_TOLERANCE * max(actual, 1):
            rep.warn(
                "W-SELF-COUNT",
                f"nb-meta sources={meta_sources} vs counted {actual}",
                suggestion="run nb stamp to write the counted totals",
            )
    meta_words = meta.get("words")
    if isinstance(meta_words, int):
        actual = ed.word_count
        if actual and abs(meta_words - actual) > SELF_COUNT_TOLERANCE * actual:
            rep.warn(
                "W-SELF-COUNT",
                f"nb-meta words={meta_words} vs counted {actual}",
                suggestion="run nb stamp to write the counted totals",
            )


def _check_banned_terms(
    raw_prose: str,
    *,
    banned_terms: Sequence[Mapping[str, object]],
    rep: Report,
) -> None:
    prose = raw_prose.casefold()
    for entry in banned_terms:
        terms = entry.get("terms")
        if not isinstance(terms, list):
            continue
        count = sum(prose.count(str(term).casefold()) for term in terms)
        raw_limit = entry.get("max", 0)
        limit = raw_limit if isinstance(raw_limit, int) else 0
        if count > limit:
            suggestion = entry.get("suggestion")
            rep.warn(
                "W-BANNED-TERM",
                f"'{entry['id']}': {count} uses; the limit is {limit}",
                suggestion=suggestion if isinstance(suggestion, str) else None,
            )


def _check_placeholders(
    raw_prose: str,
    *,
    skeleton_placeholders: frozenset[str],
    rep: Report,
) -> None:
    leftovers: set[str] = set()
    for run in caps_runs(raw_prose):
        joined = " ".join(run)
        if len(run) >= PLACEHOLDER_RUN_WORDS or joined in skeleton_placeholders:
            leftovers.add(joined)
    if leftovers:
        shown = "', '".join(sorted(leftovers)[:MAX_SHOWN_LEFTOVERS])
        rep.warn(
            "W-PLACEHOLDER",
            f"all-caps placeholder text survives in the prose: '{shown}'",
            suggestion="replace every caps placeholder with the piece's own "
            "words; caps exist so an unfilled slot cannot pass as copy",
        )


def check_warns(
    ed: Article,
    meta: Mapping[str, object],
    *,
    series: Mapping[str, object],
    treg: Mapping[str, object],
    template_id: str,
    item_cfg: Mapping[str, object] | None,
    banned_terms: Sequence[Mapping[str, object]],
    skeleton_placeholders: frozenset[str],
    rep: Report,
) -> None:
    _check_length_bands(ed, treg=treg, template_id=template_id, rep=rep)
    _check_sentence_density(ed, rep)

    floor = minimum(series, treg)
    if len(ed.sources) < floor:
        rep.warn("W-SOURCES-MIN", f"{len(ed.sources)} sources; series floor is {floor}")

    _check_cite_density(ed, treg=treg, rep=rep)
    _check_cite_order(ed, rep)
    _check_source_policy(ed, series=series, item_cfg=item_cfg, rep=rep)
    _check_self_counts(ed, meta, rep=rep)

    # banned terms & placeholders cover rendered text minus the sources section,
    # so a heading counts and a cited title does not.
    raw_prose = " ".join(" ".join(ed.prose_text_parts).split())
    _check_banned_terms(raw_prose, banned_terms=banned_terms, rep=rep)
    _check_placeholders(raw_prose, skeleton_placeholders=skeleton_placeholders, rep=rep)
