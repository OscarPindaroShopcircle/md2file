#!/usr/bin/env bash
#
# Convert the shipped examples into output/js/examples/ so people can eyeball the
# difference between an unstyled document and the Circeus-branded one.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/colors.sh"

EX="$ROOT/examples"
OUT="$ROOT/output/js/examples"
CLI="$ROOT/js/src/index.js"

mkdir -p "$OUT"

c_info ">> 01-plain (default theme, no chrome)"
node "$CLI" "$EX/01-plain/report.md" -o "$OUT/01-plain.docx" >/dev/null

c_info ">> 02-branded (circeus-brand light theme + logo + cover)"
node "$CLI" "$EX/02-branded/report.md" -o "$OUT/02-branded.docx" \
  --theme "$EX/02-branded/circeus-brand-light.json" \
  --logo "$EX/02-branded/assets/circeus-logo-dark-charcoal.png" \
  --logo-width 150 \
  --eyebrow "Operating overview" \
  --title "Circeus operating overview" \
  --subtitle "For founders considering a partnership" \
  --footer "Circeus — circeus.com" \
  --page-numbers >/dev/null

c_success ">> done. results in $OUT:"
find "$OUT" -name '*.docx' | sort | while read -r f; do c_step "   ${f##*/}"; done
