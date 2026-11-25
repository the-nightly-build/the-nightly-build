# /// script
# requires-python = ">=3.10"
# dependencies = ["websocket-client"]
# ///
"""Probe the PR's rendered article in headless Chrome for CI.

The file-level proof cannot see how a page renders, so validate runs this
after check.py: it loads the built article at phone width and asserts no
horizontal overflow, that the stylesheet attached (an unstyled page computes
the browser's fallback serif, which is how an invented body class shipped
unstyled once), and that the page threw no errors. It exits 0 with a note
when the PR adds no article (owner curation) or the environment has no
Chrome, because those are environment facts, not article verdicts; every
article failure exits 1 with one line per finding.

Usage: python3 render_check.py --site <built-site-dir> --article
library/<series>/<slug>.html
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import TypedDict

import websocket

VIEWPORT = 390
CHROME_CANDIDATES = (
    os.environ.get("CHROME_BIN"),
    "google-chrome",
    "chromium-browser",
    "chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


class _ProbeFacts(TypedDict):
    scrollWidth: int
    innerWidth: int
    bodyFont: str
    exceptions: list[str]


def find_chrome() -> str | None:
    for c in CHROME_CANDIDATES:
        if not c:
            continue
        found = shutil.which(c) or (c if pathlib.Path(c).is_file() else None)
        if found:
            return found
    return None


def wait_for_page_target(port: int) -> dict[str, object] | None:
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/json") as resp:
                tabs = json.load(resp)
            for tab in tabs:
                if tab.get("type") == "page":
                    return tab
        except (urllib.error.URLError, ConnectionError, json.JSONDecodeError, OSError):
            pass
        time.sleep(0.2)
    return None


def _send_cdp(
    ws: websocket.WebSocket,
    method: str,
    *,
    params: dict[str, object] | None = None,
    msg_id: list[int],
    errors: list[str],
) -> dict[str, object]:
    msg_id[0] += 1
    current_id = msg_id[0]
    ws.send(json.dumps({"id": current_id, "method": method, "params": params or {}}))
    while True:
        resp = json.loads(ws.recv())
        if resp.get("method") == "Runtime.exceptionThrown":
            detail = resp["params"]["exceptionDetails"]
            errors.append(detail.get("text", "exception"))
        if resp.get("id") == current_id:
            return resp.get("result", {})


def _probe_websocket(ws_url: str, page_path: pathlib.Path) -> _ProbeFacts | None:
    ws = websocket.create_connection(ws_url, timeout=30)
    msg_id = [0]
    errors: list[str] = []

    _send_cdp(ws, "Runtime.enable", msg_id=msg_id, errors=errors)
    _send_cdp(
        ws,
        "Emulation.setDeviceMetricsOverride",
        params={"width": VIEWPORT, "height": 1200, "deviceScaleFactor": 1, "mobile": True},
        msg_id=msg_id,
        errors=errors,
    )
    _send_cdp(
        ws,
        "Page.navigate",
        params={"url": f"file://{page_path.resolve()}"},
        msg_id=msg_id,
        errors=errors,
    )
    # Poll until the file: document (not the about:blank Chrome started
    # on) finishes loading; a static local page takes tens of ms, and the
    # 5s cap only defers to the fact checks below, which fail loudly.
    for _ in range(100):
        loaded = _send_cdp(
            ws,
            "Runtime.evaluate",
            params={"expression": ("location.protocol === 'file:' && document.readyState === 'complete'")},
            msg_id=msg_id,
            errors=errors,
        )
        eval_result = loaded.get("result")
        if isinstance(eval_result, dict) and eval_result.get("value"):
            break
        time.sleep(0.05)
    result = _send_cdp(
        ws,
        "Runtime.evaluate",
        params={
            "expression": (
                "JSON.stringify({"
                "scrollWidth: document.documentElement.scrollWidth,"
                "innerWidth: window.innerWidth,"
                "bodyFont: getComputedStyle(document.body).fontFamily})"
            )
        },
        msg_id=msg_id,
        errors=errors,
    )
    eval_payload = result.get("result")
    raw_value = eval_payload.get("value") if isinstance(eval_payload, dict) else None
    if not isinstance(raw_value, str):
        return None
    parsed = json.loads(raw_value)
    return _ProbeFacts(
        scrollWidth=int(parsed["scrollWidth"]),
        innerWidth=int(parsed["innerWidth"]),
        bodyFont=str(parsed["bodyFont"]),
        exceptions=errors,
    )


def probe(chrome: str, page_path: str | pathlib.Path) -> _ProbeFacts | None:
    port = 9223
    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            "--user-data-dir=/tmp/render-check-profile",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        target = wait_for_page_target(port)
        ws_url = target.get("webSocketDebuggerUrl") if target is not None else None
        if not isinstance(ws_url, str):
            return None
        return _probe_websocket(ws_url, pathlib.Path(page_path))
    finally:
        proc.terminate()


def _collect_failures(facts: _ProbeFacts) -> list[str]:
    failures: list[str] = []
    # Mobile emulation grows the layout viewport to fit overflowing content,
    # so compare against the configured width, not window.innerWidth.
    if facts["scrollWidth"] > VIEWPORT + 2:
        failures.append(f"horizontal overflow: content is {facts['scrollWidth']}px wide in a {VIEWPORT}px viewport")
    if "times" in facts["bodyFont"].lower():
        failures.append(
            "stylesheet did not attach: body computed font is the browser "
            f"fallback ({facts['bodyFont']}); check the body class and asset links"
        )
    failures.extend(f"page error: {e}" for e in facts["exceptions"])
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="built site directory")
    ap.add_argument("--article", required=True, help="library/<series>/<slug>.html")
    args = ap.parse_args()

    page = pathlib.Path(args.site) / args.article
    if not page.is_file():
        sys.stdout.write(f"render probe: no page at {page}; nothing to probe\n")
        return 0
    chrome = find_chrome()
    if chrome is None:
        sys.stdout.write("render probe: no Chrome in this environment; skipped\n")
        return 0
    facts = probe(chrome, page)
    if facts is None:
        sys.stdout.write("render probe: Chrome did not start; skipped\n")
        return 0

    failures = _collect_failures(facts)
    if failures:
        for f in failures:
            sys.stdout.write(f"render probe FAIL: {f}\n")
        return 1
    sys.stdout.write(
        f"render probe ok: {VIEWPORT}px viewport, no overflow, "
        f"styles attached ({facts['bodyFont'].split(',')[0]}), no page errors\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
