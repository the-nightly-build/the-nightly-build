#!/usr/bin/env python3
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

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

import websocket

VIEWPORT = 390
CHROME_CANDIDATES = (
    os.environ.get("CHROME_BIN"),
    "google-chrome",
    "chromium-browser",
    "chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def find_chrome():
    for c in CHROME_CANDIDATES:
        if not c:
            continue
        found = shutil.which(c) or (c if os.path.isfile(c) else None)
        if found:
            return found
    return None


def wait_for_page_target(port):
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


def probe(chrome, page_path):
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
        if target is None:
            return None
        ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=30)
        msg_id = 0
        errors = []

        def send(method, params=None):
            nonlocal msg_id
            msg_id += 1
            ws.send(
                json.dumps({"id": msg_id, "method": method, "params": params or {}})
            )
            while True:
                resp = json.loads(ws.recv())
                if resp.get("method") == "Runtime.exceptionThrown":
                    detail = resp["params"]["exceptionDetails"]
                    errors.append(detail.get("text", "exception"))
                if resp.get("id") == msg_id:
                    return resp.get("result", {})

        send("Runtime.enable")
        send(
            "Emulation.setDeviceMetricsOverride",
            {"width": VIEWPORT, "height": 1200, "deviceScaleFactor": 1, "mobile": True},
        )
        send("Page.navigate", {"url": "file://" + os.path.abspath(page_path)})
        # Poll until the file: document (not the about:blank Chrome started
        # on) finishes loading; a static local page takes tens of ms, and the
        # 5s cap only defers to the fact checks below, which fail loudly.
        for _ in range(100):
            loaded = send(
                "Runtime.evaluate",
                {
                    "expression": (
                        "location.protocol === 'file:' "
                        "&& document.readyState === 'complete'"
                    )
                },
            )
            if loaded.get("result", {}).get("value"):
                break
            time.sleep(0.05)
        result = send(
            "Runtime.evaluate",
            {
                "expression": (
                    "JSON.stringify({"
                    "scrollWidth: document.documentElement.scrollWidth,"
                    "innerWidth: window.innerWidth,"
                    "bodyFont: getComputedStyle(document.body).fontFamily})"
                )
            },
        )
        facts = json.loads(result["result"]["value"])
        facts["exceptions"] = errors
        return facts
    finally:
        proc.terminate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="built site directory")
    ap.add_argument("--article", required=True, help="library/<series>/<slug>.html")
    args = ap.parse_args()

    page = os.path.join(args.site, args.article)
    if not os.path.isfile(page):
        print(f"render probe: no page at {page}; nothing to probe")
        return 0
    chrome = find_chrome()
    if chrome is None:
        print("render probe: no Chrome in this environment; skipped")
        return 0
    facts = probe(chrome, page)
    if facts is None:
        print("render probe: Chrome did not start; skipped")
        return 0

    failures = []
    # Mobile emulation grows the layout viewport to fit overflowing content,
    # so compare against the configured width, not window.innerWidth.
    if facts["scrollWidth"] > VIEWPORT + 2:
        failures.append(
            f"horizontal overflow: content is {facts['scrollWidth']}px wide "
            f"in a {VIEWPORT}px viewport"
        )
    if "times" in facts["bodyFont"].lower():
        failures.append(
            "stylesheet did not attach: body computed font is the browser "
            f"fallback ({facts['bodyFont']}); check the body class and asset links"
        )
    for e in facts["exceptions"]:
        failures.append(f"page error: {e}")

    if failures:
        for f in failures:
            print(f"render probe FAIL: {f}")
        return 1
    print(
        f"render probe ok: {VIEWPORT}px viewport, no overflow, "
        f"styles attached ({facts['bodyFont'].split(',')[0]}), no page errors"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
