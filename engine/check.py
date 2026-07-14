#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Validate an article against the protocol and series config: the proof.

Findings come in two tiers. BLOCK findings are integrity failures and CI
refuses to publish on any of them. WARN findings are quality calibration:
agents treat them as revision notes and they block only when a series sets
strict true. The same tool runs in the agent loop, in press checks, and in
CI, which keeps the publishing bar identical everywhere.

Invocations:

    Agent loop / press check:
        python3 engine/check.py library/<series>/<slug>.html --series <id> --repo . [--library DIR]
    CI (PR mode):
        python3 engine/check.py --pr --repo . --main <main checkout> \
            --base <ref> --head <ref> [--pr-body FILE] [--library DIR]

In PR mode --repo is the PR checkout, used for the diff and the article
file. Configs and templates load from --main because the orphan library
branch carries no engine.

The checks themselves live in nb/proof/; this file is the door they open by.
"""

import argparse
import datetime as _dt
import sys

from nb.article import Article
from nb.config import find_template, load_registry, load_series
from nb.links import classify_link, dead_source_links
from nb.proof import check_article
from nb.proof.pr import resolve_pr_body, run_pr_mode
from nb.proof.sources import SOURCE_KINDS, is_count
from nb.proof.structure import ENGINE_SCRIPT_RE, check_chrome, check_classes
from nb.report import Finding, Report, emit

# `import check` is how the suite, validate_config.py, and any press tooling
# reach the proof. These names are that surface; the code behind them is in nb/.
__all__ = [
    "ENGINE_SCRIPT_RE",
    "SOURCE_KINDS",
    "Article",
    "Finding",
    "Report",
    "check_article",
    "check_chrome",
    "check_classes",
    "classify_link",
    "dead_source_links",
    "find_template",
    "is_count",
    "load_registry",
    "load_series",
    "main",
    "resolve_pr_body",
    "run_pr_mode",
]


def main(argv=None):
    p = argparse.ArgumentParser(description="The Nightly Build proof")
    p.add_argument("file", nargs="?", help="article HTML file (local mode)")
    p.add_argument("--series", help="series id (local mode)")
    p.add_argument(
        "--repo",
        default=".",
        help="repo root (local mode: main checkout; PR mode: PR checkout)",
    )
    p.add_argument(
        "--main",
        help="main checkout for configs/registry (PR mode; defaults to --repo)",
    )
    p.add_argument("--library", help="published library state (branch checkout dir)")
    p.add_argument("--pr", action="store_true", help="CI mode")
    p.add_argument(
        "--deletions-by-owner",
        action="store_true",
        help="accept a deletion-only diff as owner curation; CI passes this "
        "flag only when the PR author is the repository owner",
    )
    p.add_argument("--base", help="PR base ref (pr mode)")
    p.add_argument("--head", default="HEAD", help="PR head ref (pr mode)")
    p.add_argument(
        "--pr-body",
        help="PR body file; cross-checks its nb-meta against the article "
        "(CI mode, or a local preflight before opening the PR)",
    )
    p.add_argument("--today", help="override today's date (tests)")
    p.add_argument(
        "--check-links",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="verify each source URL resolves (on by default, needs network). "
        "Blocks only on a 404/410 or a domain that does not resolve; restricted, "
        "slow, or unreachable sources never block. Use --no-check-links offline.",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    # strict comes from the series config; resolve it lazily
    rep = Report(strict=False)

    if args.pr:
        if not args.base:
            p.error("--pr requires --base")
        run_pr_mode(args, rep)
    else:
        if not args.file or not args.series:
            p.error("local mode requires FILE and --series")
        series, _ = load_series(args.repo, args.series)
        rep.strict = bool(series and series.get("strict"))
        check_article(
            args.file,
            args.series,
            repo=args.repo,
            library_dir=args.library,
            rep=rep,
            pr_body_meta=resolve_pr_body(args.pr_body, rep),
            today=args.today and _dt.date.fromisoformat(args.today),
            check_links=args.check_links,
        )

    return emit(rep, args.json)


if __name__ == "__main__":
    sys.exit(main())
