#!/usr/bin/env bash
# Install the optional, repo-pinned figure-capture toolchain.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

uv sync --group figure-capture
uv run --group figure-capture playwright install chromium
