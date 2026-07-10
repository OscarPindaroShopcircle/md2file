#!/usr/bin/env bash
#
# Regenerate all converted .docx results from the JS implementation into
# output/js/ (git-ignored). Renders the fixtures and the two examples.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
source "$ROOT/scripts/colors.sh"

FIXTURES="$ROOT/tests/fixtures"
EX="$ROOT/examples"
OUT="$ROOT/output/js"
CLI="$HERE/src/index.js"

mkdir -p "$OUT" "$OUT/examples"

if [[ ! -d "$HERE/node_modules" ]]; then
  c_info ">> installing js dependencies..."
  (cd "$HERE" && npm install)
fi

c_info ">> converting fixtures -> $OUT"
for md in "$FIXTURES"/*.md; do
  base="$(basename "$md" .md)"
  [[ "$base" == "circeus-report" ]] && continue
  c_step "   - $base.md"
  node "$CLI" "$md" -o "$OUT/$base.docx" >/dev/null
done

c_step "   - circeus-report.md (with cover chrome)"
node "$CLI" "$FIXTURES/circeus-report.md" -o "$OUT/circeus-report.docx" \
  --theme circeus-light \
  --eyebrow "Internal engineering report" \
  --title "IP protection: multi-turn leakage detection" \
  --subtitle "Branch: feature/ip_protection_advanced" \
  --subtitle "Period: June – July 2026" \
  --footer "Circeus — confidential" \
  --page-numbers >/dev/null

c_info ">> converting examples -> $OUT/examples"
c_step "   - 01-plain"
node "$CLI" "$EX/01-plain/report.md" -o "$OUT/examples/01-plain.docx" >/dev/null

c_step "   - 02-branded"
node "$CLI" "$EX/02-branded/report.md" -o "$OUT/examples/02-branded.docx" \
  --theme "$EX/02-branded/circeus-brand-light.json" \
  --logo "$EX/02-branded/assets/circeus-logo-dark-charcoal.png" \
  --logo-width 150 \
  --eyebrow "Operating overview" \
  --title "Circeus operating overview" \
  --subtitle "For founders considering a partnership" \
  --footer "Circeus — circeus.com" \
  --page-numbers >/dev/null

c_success ">> done. results in $OUT:"
find "$OUT" -name '*.docx' | sort | while read -r f; do c_step "   ${f#$OUT/}"; done
