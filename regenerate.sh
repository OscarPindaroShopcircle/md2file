#!/usr/bin/env bash
#
# Regenerate all converted .docx results into ./output (git-ignored).
#
# Renders every fixture in tests/fixtures/ with the JS converter, plus the
# circeus-report with its full cover/footer chrome so you can eyeball the
# "real" styled document.
#
# Usage:
#   ./regenerate.sh                 # convert everything with defaults
#   ./regenerate.sh --theme foo     # pass extra flags through to the converter
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES="$ROOT/tests/fixtures"
OUT="$ROOT/output/js"    # results from the JS implementation
CLI="$ROOT/js/src/index.js"

mkdir -p "$OUT"

# Make sure JS deps are installed.
if [[ ! -d "$ROOT/js/node_modules" ]]; then
  echo ">> installing js dependencies..."
  (cd "$ROOT/js" && npm install)
fi

echo ">> converting fixtures -> $OUT"

# Plain conversions (no cover/chrome) for every fixture except the report.
for md in "$FIXTURES"/*.md; do
  base="$(basename "$md" .md)"
  [[ "$base" == "circeus-report" ]] && continue
  echo "   - $base.md"
  node "$CLI" "$md" -o "$OUT/$base.docx" "$@"
done

# The full "real" report, with cover + footer + page numbers.
echo "   - circeus-report.md (with cover chrome)"
node "$CLI" "$FIXTURES/circeus-report.md" -o "$OUT/circeus-report.docx" \
  --theme circeus-light \
  --eyebrow "Internal engineering report" \
  --title "IP protection: multi-turn leakage detection" \
  --subtitle "Branch: feature/ip_protection_advanced" \
  --subtitle "Period: June – July 2026" \
  --footer "Circeus — confidential" \
  --page-numbers \
  "$@"

echo ">> done. results in $OUT:"
ls -1 "$OUT"/*.docx | sed 's|.*/|   |'
