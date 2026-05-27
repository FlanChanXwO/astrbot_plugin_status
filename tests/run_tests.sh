#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PLUGIN_DIR"

uv run ruff check main.py core tests
uv run ruff format --check main.py core tests
python3 -m compileall main.py core tests
pytest tests/ -v
