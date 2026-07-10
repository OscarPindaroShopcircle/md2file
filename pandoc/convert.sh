#!/usr/bin/env bash
#
# Convert a markdown file to a styled .docx with pandoc, applying styling via a
# reference document (built by build-references.sh).
#
# Usage:
#   convert.sh <input.md> -o <out.docx> [options]
#
# Options:
#   -o, --out <file>       output .docx (required)
#   -r, --ref <file>       reference .docx (default: references/circeus-light.docx)
#       --title <str>      document title (pandoc title block)
#       --subtitle <str>   document subtitle
#       --author <str>     document author
#
# Note: footer text and page numbers are baked into the *reference* document
# (see build-references.sh / the theme YAML's `chrome:` block), not passed here.
# A cover logo is not supported by the pandoc approach.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$HERE/.." && pwd)/scripts/colors.sh"

REF="$HERE/references/circeus-light.docx"
OUT=""
TITLE=""; SUBTITLE=""; AUTHOR=""
INPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--out) OUT="$2"; shift 2 ;;
    -r|--ref) REF="$2"; shift 2 ;;
    --title) TITLE="$2"; shift 2 ;;
    --subtitle) SUBTITLE="$2"; shift 2 ;;
    --author) AUTHOR="$2"; shift 2 ;;
    -*) c_error "unknown option: $1"; exit 2 ;;
    *) INPUT="$1"; shift ;;
  esac
done

[[ -n "$INPUT" ]] || { c_error "error: no input file"; exit 2; }
[[ -n "$OUT" ]]   || { c_error "error: -o/--out is required"; exit 2; }
[[ -f "$REF" ]]   || { c_error "error: reference not found: $REF (run build-references.sh)"; exit 2; }

args=(--reference-doc="$REF" --resource-path="$(dirname "$INPUT")")
[[ -n "$TITLE" ]]    && args+=(--metadata "title=$TITLE")
[[ -n "$SUBTITLE" ]] && args+=(--metadata "subtitle=$SUBTITLE")
[[ -n "$AUTHOR" ]]   && args+=(--metadata "author=$AUTHOR")

mkdir -p "$(dirname "$OUT")"
pandoc "$INPUT" -o "$OUT" "${args[@]}"
c_success "wrote $OUT"
