#!/usr/bin/env bash
# Local launcher for Linux/macOS/WSL.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
    command -v uv >/dev/null || { echo "Install uv: https://docs.astral.sh/uv/" >&2; exit 1; }
    uv sync
fi
exec .venv/bin/python -m services.launcher "$@"
