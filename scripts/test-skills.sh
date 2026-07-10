#!/usr/bin/env bash
#
# Run the end-to-end skill tests. Skills whose toolchain (uv / node) is missing
# are skipped rather than failed.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/colors.sh"

command -v uv >/dev/null || { c_error "uv is required to run the test harness"; exit 1; }
(cd "$ROOT/python" && uv sync >/dev/null)

c_header "== skill end-to-end tests =="
(cd "$ROOT/python" && uv run pytest "$ROOT/tests/test_skills.py" -v)
