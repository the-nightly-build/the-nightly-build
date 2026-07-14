"""The proof: every check one article must pass, run in one pass."""

import datetime as _dt
import os

from nb.article import Article
from nb.config import find_template, load_banned_terms, published_slugs
from nb.proof.meta import (
    bind_open_template,
    check_meta_agreement,
    parse_meta,
    read_article_source,
    resolve_series_and_template,
)
from nb.proof.mode import check_mode
from nb.proof.prose import check_warns, placeholder_entries
from nb.proof.sources import check_source_kinds, check_sources
from nb.proof.structure import (
    check_chrome,
    check_cites,
    check_classes,
    check_required_sections,
    check_sandbox,
)


def check_article(
    html_path,
    series_id,
    *,
    repo,
    library_dir,
    rep,
    pr_body_meta=None,
    today=None,
    check_links=False,
) -> dict | None:
    """Run every check against one article and record the findings on rep.

    `today` defaults to the date in UTC, which is the clock duty.py keeps and
    the clock PROTOCOL's rolling-slug rule names. The local clock would fail a
    correct article: a night shift running west of UTC, after its own evening
    rollover, computes yesterday and then reads tonight's rolling slug as a
    date in the future.
    """
    today = today or _dt.datetime.now(_dt.timezone.utc).date()

    resolved = resolve_series_and_template(repo, series_id, rep)
    if resolved is None:
        return None
    series, registry, mode_cfg, template_id, treg, allowed_templates = resolved

    raw = read_article_source(html_path, rep)
    if raw is None:
        return None

    ed = Article()
    ed.feed(raw)
    ed.close()

    meta = parse_meta(ed, rep)
    if meta is None:
        return None

    if mode_cfg == "open":
        bound = bind_open_template(meta, registry, allowed_templates, rep)
        if bound is None:
            return None
        template_id, treg = bound

    fname = os.path.basename(html_path)
    slug_from_path = fname[:-5] if fname.endswith(".html") else fname
    parent = os.path.basename(os.path.dirname(html_path))
    check_meta_agreement(
        meta,
        series=series,
        series_id=series_id,
        template_id=template_id,
        slug_from_path=slug_from_path,
        parent=parent,
        dekline=ed.dekline,
        pr_body_meta=pr_body_meta,
        rep=rep,
    )

    slug = meta.get("slug") or slug_from_path
    pub = published_slugs(library_dir, series_id)
    item_cfg = check_mode(
        meta,
        series=series,
        series_id=series_id,
        slug=slug,
        pub=pub,
        today=today,
        rep=rep,
    )

    check_required_sections(ed, treg, rep)
    check_chrome(raw, treg=treg, rep=rep)
    check_classes(raw, repo=repo, rep=rep)
    check_sandbox(ed, rep)
    check_sources(ed, rep, check_links=check_links)
    check_cites(ed, rep)
    check_source_kinds(ed, series=series, treg=treg, rep=rep)
    check_warns(
        ed,
        meta,
        series=series,
        treg=treg,
        template_id=template_id,
        item_cfg=item_cfg,
        banned_terms=load_banned_terms(repo),
        skeleton_placeholders=placeholder_entries(find_template(repo, template_id)),
        rep=rep,
    )
    return meta
