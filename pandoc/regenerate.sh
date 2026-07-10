#!/usr/bin/env bash
#
# Regenerate all converted .docx results from the PANDOC implementation into
# output/pandoc/ (git-ignored). Builds the reference docs first.
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
source "$ROOT/scripts/colors.sh"

FIXTURES="$ROOT/tests/fixtures"
OUT="$ROOT/output/pandoc"
LIGHT="$HERE/references/circeus-light.docx"
BRAND="$HERE/references/circeus-brand.docx"

"$HERE/build-references.sh"

mkdir -p "$OUT" "$OUT/examples"

c_info ">> converting fixtures -> $OUT"
for md in "$FIXTURES"/*.md; do
  base="$(basename "$md" .md)"
  [[ "$base" == "circeus-report" ]] && continue
  c_step "   - $base.md"
  "$HERE/convert.sh" "$md" -o "$OUT/$base.docx" -r "$LIGHT" >/dev/null
done

c_step "   - circeus-report.md (title block)"
"$HERE/convert.sh" "$FIXTURES/circeus-report.md" -o "$OUT/circeus-report.docx" -r "$LIGHT" \
  --title "IP protection: multi-turn leakage detection" \
  --subtitle "Branch: feature/ip_protection_advanced" >/dev/null

c_info ">> converting examples -> $OUT/examples"
c_step "   - 01-plain"
"$HERE/convert.sh" "$ROOT/examples/01-plain/report.md" -o "$OUT/examples/01-plain.docx" -r "$LIGHT" >/dev/null
c_step "   - 02-branded (circeus-brand reference)"
"$HERE/convert.sh" "$ROOT/examples/02-branded/report.md" -o "$OUT/examples/02-branded.docx" -r "$BRAND" \
  --title "Circeus operating overview" \
  --subtitle "For founders considering a partnership" >/dev/null

c_success ">> done. results in $OUT:"
find "$OUT" -name '*.docx' | sort | while read -r f; do c_step "   ${f#$OUT/}"; done
