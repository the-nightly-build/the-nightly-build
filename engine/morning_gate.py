#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Decide whether the morning mail sends, and with what body.

morning-mail.yml runs hourly and used to carry this whole decision as an
inline heredoc — the one place engine logic lived inside a workflow, which
no test could reach. It prints GitHub-outputs (send/why/body/subject) and
exits; the workflow's only jobs are checkouts and the SMTP send.

The gate declines, in order: no MAIL_TO secret, no configured send hour or
not that hour (workflow_dispatch forces past both), Pages not enabled, no
published catalog, no dated build. With a build fresh from last night it
sends the digest the press already rendered (email-latest.html). Otherwise
it asks duty.py whether anything was due: quiet by design stays silent, a
missed night sends a short notice for up to 14 days, then goes silent so a
dead press stops paging its owner.

"Latest build" uses build_site's own sort rule: a dateless article buckets
under the NO_DATE sentinel, which must never win latest — a plain max()
here once picked it and crashed the gate into permanent silence.

Usage (from a repo checkout, library checked out at _library):
    python3 engine/morning_gate.py >> "$GITHUB_OUTPUT"
Env: MAIL_TO (gate), FORCE ("true" from workflow_dispatch), GH_TOKEN and
GITHUB_REPOSITORY (Pages URL lookup).
"""

import datetime
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request
from typing import NoReturn

import build_site


def out(send, why, *, body="", subject="") -> NoReturn:
    print(f"send={'true' if send else 'false'}")
    print(f"why={why}")
    print(f"body={body}")
    print(f"subject={subject}")
    raise SystemExit(0)


def latest_build(builds):
    latest = max(builds, key=build_site.date_sort_key, default=None)
    return None if latest == build_site.NO_DATE else latest


def quiet_notice(title, *, missed, latest, age):
    return (
        f'<div style="font-family:Georgia,serif;max-width:560px;'
        f'margin:0 auto;padding:24px">'
        f'<h2 style="margin:0 0 12px">{title}: the press was quiet '
        f"last night</h2>"
        f'<p style="color:#444444;line-height:1.6">No new build was '
        f"published, but these series were due: <b>{missed}</b>. "
        f"The night shift may have been skipped or may have failed; "
        f"check your schedule and the repo&rsquo;s Actions tab. "
        f"Latest build: {latest} ({age} nights ago).</p></div>\n"
    )


def pages_base_url():
    got = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{os.environ['GITHUB_REPOSITORY']}/pages",
            "--jq",
            ".html_url",
        ],
        capture_output=True,
        text=True,
    ).stdout.strip()
    return got.rstrip("/") + "/" if got else None


def fetch(base, name):
    try:
        with urllib.request.urlopen(base + name, timeout=15) as resp:
            return resp.read().decode()
    except (OSError, ValueError):
        return None


def main():
    if not os.environ.get("MAIL_TO"):
        out(False, "MAIL_TO secret not set (Atom feed remains available)")
    force = os.environ.get("FORCE") == "true"
    site = build_site.load_site_config(".")
    title = site["title"]
    hour = (site.get("email") or {}).get("send_utc_hour")
    now = datetime.datetime.now(datetime.timezone.utc)
    if not force:
        if hour is None:
            out(False, "email.send_utc_hour not set in press/site.yaml")
        if int(hour) != now.hour:
            out(False, f"not the configured hour ({hour}:00 UTC)")

    base = pages_base_url()
    if base is None:
        out(False, "Pages not enabled yet")
    catalog_raw = fetch(base, "catalog.json")
    if catalog_raw is None:
        out(False, "no published site yet")
    try:
        catalog = json.loads(catalog_raw)
        builds = catalog["builds"]
    except (ValueError, TypeError, KeyError):
        out(False, "catalog unreadable")
    latest = latest_build(builds)
    if latest is None:
        out(False, "no dated build yet")
    try:
        age = (now.date() - datetime.date.fromisoformat(latest)).days
    except ValueError:
        out(False, f"latest build {latest!r} is not a date; staying quiet")

    if age <= 1 or force:
        digest_html = fetch(base, "email-latest.html")
        if digest_html is None:
            out(False, "no built digest yet")
        subject = (fetch(base, "email-latest-subject.txt") or "").strip()
        digest = pathlib.Path("_digest.html")
        digest.write_text(digest_html)
        out(True, f"delivering build {latest}", body=str(digest), subject=subject)

    # No fresh build. Quiet by design, or a missed night?
    yesterday = (now.date() - datetime.timedelta(days=1)).isoformat()
    try:
        duty = json.loads(
            subprocess.run(
                [
                    sys.executable,
                    "engine/duty.py",
                    "--repo",
                    ".",
                    "--library",
                    "_library",
                    "--date",
                    yesterday,
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        )
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError):
        out(False, "duty check failed; staying quiet")
    if not duty["due"]:
        out(
            False,
            f"nothing was due last night (latest build {latest}); quiet by design",
        )
    if age > 14:
        out(False, f"stale {age} days; alert window passed, going silent")
    missed = ", ".join(e["series"] for e in duty["due"])
    q = pathlib.Path("_quiet.html")
    q.write_text(quiet_notice(title, missed=missed, latest=latest, age=age))
    out(True, "quiet-night notice", body=str(q), subject=f"Quiet night at {title}")


if __name__ == "__main__":
    main()
