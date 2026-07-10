#!/usr/bin/env bash
#
# Regenerate all converted .docx results from the PYTHON implementation into
# output/python/ (git-ignored).
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
source "$ROOT/scripts/colors.sh"

PYDIR="$HERE"
FIXTURES="$ROOT/tests/fixtures"
OUT="$ROOT/output/python"

mkdir -p "$OUT" "$OUT/examples"

if [[ ! -d "$PYDIR/.venv" ]]; then
  c_info ">> uv sync..."
  (cd "$PYDIR" && uv sync)
fi

run() { (cd "$PYDIR" && uv run md2docx convert "$@"); }

c_info ">> converting fixtures -> $OUT"
for md in "$FIXTURES"/*.md; do
  base="$(basename "$md" .md)"
  [[ "$base" == "circeus-report" ]] && continue
  c_step "   - $base.md"
  run "$md" -o "$OUT/$base.docx" -q
done

c_step "   - circeus-report.md (with cover chrome)"
run "$FIXTURES/circeus-report.md" -o "$OUT/circeus-report.docx" -q \
  --eyebrow "Internal engineering report" \
  --title "IP protection: multi-turn leakage detection" \
  --subtitle "Branch: feature/ip_protection_advanced" \
  --subtitle "Period: June – July 2026" \
  --footer "Circeus — confidential" \
  --page-numbers

c_info ">> converting examples -> $OUT/examples"
c_step "   - 01-plain"
run "$ROOT/examples/01-plain/report.md" -o "$OUT/examples/01-plain.docx" -q

c_step "   - 02-branded (YAML config)"
# run from the example folder so the config's relative paths (logo, report.md) resolve
(cd "$ROOT/examples/02-branded" && uv --project "$PYDIR" run md2docx convert \
  -c circeus-brand-light.yaml -o "$OUT/examples/02-branded.docx" -q)

c_success ">> done. results in $OUT:"
find "$OUT" -name '*.docx' | sort | while read -r f; do c_step "   ${f#$OUT/}"; done
