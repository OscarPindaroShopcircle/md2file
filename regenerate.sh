#!/usr/bin/env bash
#
# Regenerate converted .docx results for every implementation into output/<impl>/
# (git-ignored). Each implementation has its own regenerate.sh; this dispatches
# to them and skips any whose toolchain isn't installed.
#
# Usage:
#   ./regenerate.sh                 # all available implementations
#   ./regenerate.sh js pandoc       # only the named ones
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$ROOT/scripts/colors.sh"

TARGETS=("$@")
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=(js python pandoc)
fi
want() { for t in "${TARGETS[@]}"; do [[ "$t" == "$1" ]] && return 0; done; return 1; }
have() { command -v "$1" >/dev/null 2>&1; }

did=0
skipped=0

run_impl() {  # <name> <tool> <script>
  local name="$1" tool="$2" script="$3"
  want "$name" || return 0
  c_header "== $name =="
  if ! have "$tool"; then
    c_warn "   SKIP — '$tool' not found (run ./setup.sh $name)"
    skipped=$((skipped + 1))
    return 0
  fi
  bash "$script"
  did=$((did + 1))
  echo
}

run_impl js     node   "$ROOT/js/regenerate.sh"
run_impl python uv     "$ROOT/python/regenerate.sh"
run_impl pandoc pandoc "$ROOT/pandoc/regenerate.sh"

c_done "== regenerated $did implementation(s), skipped $skipped =="
c_info "   compare side by side under: $ROOT/output/{js,python,pandoc}/"
