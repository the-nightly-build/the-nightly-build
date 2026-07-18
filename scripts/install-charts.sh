#!/usr/bin/env bash
# Install the optional, repo-pinned chart-rendering toolchain.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

uv sync --group charts
# Kaleido renders PNGs through its own Chrome; fetch it once.
uv run --group charts plotly_get_chrome -y
