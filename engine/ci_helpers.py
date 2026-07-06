#!/usr/bin/env python3
"""Small CI helpers kept separate from check.py's core logic."""
import argparse
import re
import subprocess

import yaml

PR_PATH_RE = re.compile(r"^library/([a-z0-9-]{1,32})/[a-z0-9-]{1,64}\.html$")


def autopublish(repo, diff_base):
    out = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", f"{diff_base}...HEAD"],
        capture_output=True, text=True, check=True).stdout.strip().splitlines()
    if len(out) != 1:
        print("false")
        return
    m = PR_PATH_RE.match(out[0])
    if not m:
        print("false")
        return
    try:
        with open(f"{repo}/series/{m.group(1)}/series.yaml") as fh:
            cfg = yaml.safe_load(fh)
        print("true" if cfg.get("autopublish", False) else "false")
    except Exception:
        print("false")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["autopublish"])
    p.add_argument("--repo", default="_main")
    p.add_argument("--diff-base", required=True)
    a = p.parse_args()
    autopublish(a.repo, a.diff_base)
