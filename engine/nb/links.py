"""Probing cited source URLs: which of them are provably dead."""

import concurrent.futures
import socket
import urllib.error
import urllib.request
from typing import Literal

DEAD_STATUSES = frozenset((404, 410))
LINK_TIMEOUT_S = 6
LINK_WORKERS = 8
LINK_UA = (
    "Mozilla/5.0 (compatible; NightlyBuild-proof/1.1; "
    "+https://github.com/RyanSaxe/the-nightly-build)"
)


def classify_link(status, error) -> Literal["dead", "ok", "unverified"]:
    """Decide whether a source link is provably dead.

    Only a definitive 'this does not exist' counts: a 404/410 response, or a
    domain that does not resolve (DNS). Everything else — a 200, a bot-blocking
    403, a 5xx, a rate limit, a timeout, or no network at all — is 'unverified'
    and never blocks, so a real-but-restricted source can never fail a
    legitimate article.

    A 403 does NOT gate publication, and it is tempting to think it should. The
    floor says cite only what you have read, so a page the proof cannot read
    looks like a citation nobody opened. It is not, and this was measured on
    2026-07-14 against the whole published library: 37 of 244 cited URLs refused
    this probe, which would have blocked 14 of 30 articles — every SEC EDGAR
    filing, a JAMA randomized trial, an EU Council release. All were readable.
    A real browser and the agent's own fetcher both opened them; one of the
    "gated" pages was read start to finish while the fix was being written.

    The reason is that Cloudflare and Akamai do not fingerprint the User-Agent.
    They fingerprint the TLS handshake, the HTTP/2 profile, and header order,
    and urllib is unmistakably a script no matter what string it sends. So a 403
    here means "you are a script", never "this page is unreadable", and an HTTP
    status cannot be a readability oracle. Gating on it would blame articles for
    the probe's own bad manners, and would fall hardest on the best-sourced work
    in the paper, which is the work that cites primaries behind bot walls.

    "Cite only what you have read" is real, and it is enforced where the evidence
    actually lives: the researcher logs a verbatim passage per source, the writer
    may cite only what that log supports, and the editor attacks the pairing.
    """
    if status in DEAD_STATUSES:
        return "dead"
    if status is not None:
        return "ok"  # got a response: the URL exists (or is merely restricted)
    if error == "dns":
        return "dead"  # the domain itself does not resolve
    return "unverified"  # timeout, refused, offline — cannot say


def _probe_link(href):
    req = urllib.request.Request(
        href, headers={"User-Agent": LINK_UA, "Range": "bytes=0-0"}
    )
    try:
        # A one-byte Range GET, not HEAD: some servers 404/405 a HEAD they would
        # serve, and a browser-like UA keeps casual bot filters from lying to us.
        with urllib.request.urlopen(req, timeout=LINK_TIMEOUT_S) as resp:
            return classify_link(resp.status, None)
    except urllib.error.HTTPError as e:
        return classify_link(e.code, None)
    except urllib.error.URLError as e:
        return classify_link(
            None, "dns" if isinstance(e.reason, socket.gaierror) else "net"
        )
    except (TimeoutError, ValueError, OSError):
        return classify_link(None, "net")


def dead_source_links(hrefs):
    if not hrefs:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=LINK_WORKERS) as pool:
        verdicts = list(pool.map(_probe_link, hrefs))
    return [
        href for href, verdict in zip(hrefs, verdicts, strict=True) if verdict == "dead"
    ]
