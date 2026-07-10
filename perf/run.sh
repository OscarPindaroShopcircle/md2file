#!/usr/bin/env bash
#
# Convenience wrapper: sync the harness and run it. All arguments are forwarded
# to `md2docx-bench run` (see --help). Benchmarks whichever implementations are
# installed — run ../setup.sh first to set them all up.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
source "$ROOT/scripts/colors.sh"

if [[ ! -d "$HERE/.venv" ]]; then
  c_info ">> uv sync (perf harness)..."
  (cd "$HERE" && uv sync)
fi

# Default to the committed bench.yaml unless the caller passed their own --config/-c.
args=("$@")
if [[ -f "$HERE/bench.yaml" ]] && [[ ! " $* " == *" -c "* ]] && [[ ! " $* " == *" --config "* ]]; then
  args=(-c "$HERE/bench.yaml" "$@")
  c_info ">> using config: $HERE/bench.yaml"
fi

c_header "== md2docx performance harness =="
(cd "$HERE" && uv run md2docx-bench run "${args[@]}")
