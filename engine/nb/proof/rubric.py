"""Rubric rows: the scored criteria a review shows its work on.

A series pins rubric criteria in series.yaml (`rubric:`), and every article
in that series must score each of them; the writer extends with rows the
subject demands. The contract is attribute-driven — `data-nb-criterion`
names the row, `data-score` carries an integer 0-5, and the rendered
`nb-rubric-score` text must agree with the attribute — so it works on any
template, shipped or press-defined. Row integrity blocks regardless of
`strict`, like the source mix: a dropped pinned criterion or a meter that
disagrees with its label is not a calibration matter. Whether a score is
DESERVED is judgment: the cited one-line justification carries it, the
editor audits it, and the engine only counts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nb import meta as nb_meta
from nb.article import collapse_space

if TYPE_CHECKING:
    from collections.abc import Mapping

    from nb.article import Article, RubricRow
    from nb.report import Report

__all__ = ("check_rubric",)

SCORE_MAX = 5


def _pinned_criterion_ids(series: Mapping[str, object], rep: Report) -> list[str]:
    pinned = series.get("rubric")
    if pinned is None:
        return []
    if not (
        isinstance(pinned, list)
        and pinned
        and all(isinstance(c, dict) and isinstance(c.get("id"), str) for c in pinned)
    ):
        rep.block(
            "B-SERIES",
            "series 'rubric' must be a non-empty list of {id, name, note} criteria",
        )
        return []
    return [criterion_id for c in pinned if isinstance(c, dict) and isinstance(criterion_id := c.get("id"), str)]


def _check_rubric_row(row: RubricRow, rep: Report) -> None:
    slug = row["criterion"]
    if not nb_meta.SLUG_RE.match(slug or ""):
        rep.block(
            "B-RUBRIC",
            f"data-nb-criterion {slug!r} must be a slug (pattern {nb_meta.SLUG_RE.pattern})",
        )
        return
    score = row["score"]
    if score is None or not score.isdigit() or int(score) > SCORE_MAX:
        rep.block(
            "B-RUBRIC",
            f"criterion '{slug}' needs data-score, an integer 0-{SCORE_MAX} (got {score!r})",
        )
    else:
        rendered = collapse_space("".join(row["score_text_parts"]))
        expected = f"{int(score)}/{SCORE_MAX}"
        if rendered != expected:
            rep.block(
                "B-RUBRIC",
                f"criterion '{slug}' renders '{rendered}' but data-score "
                f"says {expected}; a meter that disagrees with its label "
                f"misleads the reader",
            )
    if not row["cites"]:
        rep.warn(
            "W-RUBRIC",
            f"criterion '{slug}' carries no inline citation",
            suggestion="cite the evidence its one-line justification stands on",
        )


def check_rubric(ed: Article, *, series: Mapping[str, object], rep: Report) -> None:
    pinned_ids = _pinned_criterion_ids(series, rep)
    rows = ed.rubric_rows
    if pinned_ids and not rows:
        rep.block(
            "B-RUBRIC",
            "this series pins rubric criteria; the article renders no rubric rows",
        )

    slugs = [r["criterion"] for r in rows]
    for dup in sorted({s for s in slugs if slugs.count(s) > 1}):
        rep.block("B-RUBRIC", f"criterion '{dup}' has two rows; one row per criterion")

    for row in rows:
        _check_rubric_row(row, rep)

    for missing in [p for p in pinned_ids if p not in slugs]:
        rep.block(
            "B-RUBRIC",
            f"series-pinned criterion '{missing}' has no rubric row; every review in this series scores it",
        )
