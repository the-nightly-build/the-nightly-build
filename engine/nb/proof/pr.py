"""PR mode: the shape of the night's diff, and the record its body carries."""

import datetime as _dt
import os
import re
import subprocess

import yaml

from nb import meta as nb_meta
from nb.config import load_series
from nb.proof import check_article

PR_PATH_RE = nb_meta.PR_PATH_RE
RECORD_SECTIONS = ("Task", "Process", "Voice brief", "Research", "Also consulted")
VOICE_EXEMPLARS_MIN = 3
SOURCE_LINE_RE = re.compile(r"^\s*Source:\s*\S+", re.I | re.M)


def record_headings(body):
    """Return production-record headings that are outside Markdown code fences.

    The record embeds verbatim artifacts in four-backtick fences, and those
    artifacts can legitimately contain headings named like production-record
    sections. Only the outer headings delimit the record.
    """
    headings = []
    fence = None
    offset = 0
    names = {name.casefold(): name for name in RECORD_SECTIONS}
    for line in body.splitlines(keepends=True):
        marker = re.match(r"^\s*([`~]{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            offset += len(line)
            continue
        if fence is None:
            heading = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
            if heading:
                name = names.get(heading.group(1).casefold())
                if name is not None:
                    headings.append((name, offset, offset + len(line)))
        offset += len(line)
    return headings


def parse_pr_body(path) -> dict | None:
    with open(path, encoding="utf-8") as fh:
        body = fh.read()
    m = re.search(r"```nb-meta\s*\n(.*?)```", body, re.S)
    if not m:
        return None
    try:
        data = yaml.safe_load(m.group(1))
        if not isinstance(data, dict):
            return None
        # YAML reads bare dates (slug: 2026-07-05) as date objects; nb-meta
        # holds strings — normalize so honest PR bodies compare equal
        return {
            k: (v.isoformat() if isinstance(v, _dt.date) else v)
            for k, v in data.items()
        }
    except yaml.YAMLError:
        return None


def pr_changed_files(repo, *, base, head):
    out = subprocess.run(
        [
            "git",
            "-C",
            repo,
            "diff",
            "--name-status",
            "--no-renames",
            f"{base}...{head}",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    changes = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            changes.append((parts[0], parts[-1]))
    return changes


def section_text(body, name):
    """One record section's text, ending only at the next record heading.

    The artifacts carry their own markdown inside the collapsed block, and the
    voice brief's exemplars are themselves `##` headings, so cutting at any
    heading would slice the artifact in half and hide most of it.
    """
    headings = record_headings(body)
    for index, (heading, _start, end) in enumerate(headings):
        if heading != name:
            continue
        next_start = headings[index + 1][1] if index + 1 < len(headings) else len(body)
        return body[end:next_start]
    return ""


def check_pr_body_record(pr_body_path, rep):
    """WARN when the PR body's production record is missing or hollow.

    PROTOCOL step 8 makes the body the article's production record, and the
    artifacts are gitignored, so the body is the only place they survive.
    Presence is the quality bar, never the publishing bar, so a gap is a WARN.

    The voice section gets one structural check on top of presence. The coach
    must study at least three real writers and cite each piece it read, so a
    real brief carries `Source:` lines. On 2026-07-14 an orchestrator skipped
    the coach and wrote the brief itself: six lines naming two mastheads, no
    writers, no sources. It passed every gate. Counting the `Source:` lines is
    the cheapest thing that can tell a studied brief from an invented one. It
    reads structure, never quality: judging the prose is the editor's job.
    """
    with open(pr_body_path, encoding="utf-8") as fh:
        body = fh.read()
    present = {name for name, _start, _end in record_headings(body)}
    missing = [name for name in RECORD_SECTIONS if name not in present]
    if missing:
        rep.warn(
            "W-BODY-RECORD",
            f"PR body record missing section(s): {', '.join(missing)}",
            suggestion="the body is the article's production record; "
            "PROTOCOL step 8 lists the sections",
        )
    if "Voice brief" in missing:
        return
    exemplars = len(SOURCE_LINE_RE.findall(section_text(body, "Voice brief")))
    if exemplars < VOICE_EXEMPLARS_MIN:
        rep.warn(
            "W-VOICE-THIN",
            f"the voice brief cites {exemplars} exemplar(s); the coach studies "
            f"at least {VOICE_EXEMPLARS_MIN} real writers and cites each piece",
            suggestion="a brief naming outlets instead of writers, with no "
            "Source: lines, was not written by the coach. Run the coach",
        )


def resolve_pr_body(pr_body_path, rep) -> dict | None:
    """Parse a PR body file and flag a missing or unparseable nb-meta block.

    Shared by CI mode and the local preflight (`--pr-body` without `--pr`), so
    an author can verify the exact body they intend to post before opening the
    pull request. Returns the parsed metadata, or None when no path is given.
    """
    if not pr_body_path:
        return None
    meta = parse_pr_body(pr_body_path)
    if meta is None:
        rep.block("B-META-MATCH", "PR body lacks a parseable ```nb-meta``` yaml block")
    check_pr_body_record(pr_body_path, rep)
    return meta


def run_pr_mode(args, rep):
    try:
        changes = pr_changed_files(args.repo, base=args.base, head=args.head)
    except subprocess.CalledProcessError as e:
        rep.block("B-DIFF-SHAPE", f"git diff failed: {e.stderr or e}")
        return
    if (
        getattr(args, "deletions_by_owner", False)
        and changes
        and all(status == "D" for status, _ in changes)
    ):
        if nb_meta.article_bundle_path(changes, status="D") is None:
            rep.block(
                "B-DIFF-SHAPE",
                "an owner curation PR deletes one article and only its matching "
                f"local figure assets; found {changes}",
            )
        else:
            rep.notes.append(
                f"owner curation: retracts {len(changes)} published article(s); "
                "nothing to proof"
            )
        return
    path = nb_meta.article_bundle_path(changes)
    if path is None:
        rep.block(
            "B-DIFF-SHAPE",
            "PR must add one article and only matching local figure assets; found "
            f"{[(status, path) for status, path in changes]}",
        )
        return
    m = PR_PATH_RE.match(path)
    assert m is not None
    series_id = m.group(1)
    cfg_repo = getattr(args, "main", None) or args.repo
    series_cfg, _ = load_series(cfg_repo, series_id)
    rep.strict = bool(series_cfg and series_cfg.get("strict"))
    pr_body_meta = resolve_pr_body(args.pr_body, rep)
    fs_path = os.path.join(args.repo, path)
    check_article(
        fs_path,
        series_id,
        repo=cfg_repo,
        library_dir=args.library,
        rep=rep,
        pr_body_meta=pr_body_meta,
        today=args.today and _dt.date.fromisoformat(args.today),
        check_links=args.check_links,
    )
