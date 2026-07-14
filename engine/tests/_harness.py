"""Shared plumbing for the zero-framework suites.

check/snippet/git and the pass/fail tally used to be pasted into each
suite, so a fix to failure reporting had to land three times. Each suite
runs as its own process (run_tests.py chains the other two via
subprocess), so the module-level tally here never crosses suites.
"""

import subprocess
from dataclasses import dataclass, field


@dataclass
class Tally:
    passed: int = 0
    failed: list[str] = field(default_factory=list)


TALLY = Tally()


def snippet(haystack, needle=None, *, width=240):
    text = haystack if isinstance(haystack, str) else str(haystack)
    if needle:
        i = text.find(needle if isinstance(needle, str) else str(needle))
        if i != -1:
            lo = max(0, i - width // 2)
            hi = i + len(str(needle)) + width // 2
            return ("…" if lo else "") + text[lo:hi] + ("…" if hi < len(text) else "")
    return text[:width] + ("…" if len(text) > width else "")


def check(name, condition, *, detail="", needle=None, haystack=None):
    if condition:
        TALLY.passed += 1
        print(f"  ok   {name}")
        return
    TALLY.failed.append(name)
    print(f"  FAIL {name}")
    if needle is not None:
        print(f"        looked for: {needle!r}")
    if haystack is not None:
        print(f"        in: {snippet(haystack, needle)}")
    if detail:
        print(f"        {detail}")


def git(*args, cwd):
    run = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {cwd}: {run.stderr.strip()}"
        )


def summary():
    print()
    print(f"{TALLY.passed} passed, {len(TALLY.failed)} failed")
    if TALLY.failed:
        print("FAILED:", TALLY.failed)
        return 1
    return 0
