#!/usr/bin/env bash
#
# Build pandoc reference .docx files from md2docx theme YAMLs. The reference docs
# are generated (git-ignored); run this once (setup.sh / regenerate.sh call it).
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
source "$ROOT/scripts/colors.sh"

PYDIR="$ROOT/python"
REFS="$HERE/references"
BASE="$REFS/.default-reference.docx"

command -v pandoc >/dev/null || { c_error "error: pandoc not installed (run ../setup.sh)"; exit 1; }

mkdir -p "$REFS"
c_info ">> fetching pandoc default reference"
pandoc --print-default-data-file reference.docx > "$BASE"

build() {  # <config-yaml> <output-name>
  c_step "   - $2"
  uv --project "$PYDIR" run python "$HERE/build_reference.py" \
    --base "$BASE" --config "$1" --output "$REFS/$2" >/dev/null
}

c_info ">> building references"
build "$HERE/themes/circeus-light.yaml"                    "circeus-light.docx"
build "$ROOT/examples/02-branded/circeus-brand-light.yaml" "circeus-brand.docx"

c_success ">> references in $REFS:"
find "$REFS" -name '*.docx' | sort | while read -r f; do c_step "   ${f#$REFS/}"; done
