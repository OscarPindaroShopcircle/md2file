#!/usr/bin/env bash
#
# Set up the md2docx repository: check tooling and install dependencies for each
# implementation. This grows as new versions are added (js, python, pandoc).
#
# Usage:
#   ./setup.sh            # set up everything that is available
#   ./setup.sh js         # set up only specific implementations
#   ./setup.sh js python
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Implementations to set up (default: all).
TARGETS=("$@")
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=(js python pandoc)
fi

want() { for t in "${TARGETS[@]}"; do [[ "$t" == "$1" ]] && return 0; done; return 1; }
have() { command -v "$1" >/dev/null 2>&1; }

ok=0
skip=0

echo "== md2docx setup =="
echo

# --- JavaScript (Node + npm) -------------------------------------------------
if want js; then
  echo ">> js"
  if have node && have npm; then
    echo "   node $(node --version), npm $(npm --version)"
    (cd "$ROOT/js" && npm install)
    echo "   ok — run: node js/src/index.js <input.md> [options]"
    ok=$((ok + 1))
  else
    echo "   SKIP — node/npm not found. Install Node.js >= 18."
    skip=$((skip + 1))
  fi
  echo
fi

# --- Python (uv + python-docx) ----------------------------------------------
# Placeholder: the python/ implementation is not built yet. Once it exists with
# a pyproject.toml, this will `uv sync` it.
if want python; then
  echo ">> python"
  if have uv; then
    echo "   uv $(uv --version | awk '{print $2}')"
    if [[ -f "$ROOT/python/pyproject.toml" ]]; then
      (cd "$ROOT/python" && uv sync)
      echo "   ok"
      ok=$((ok + 1))
    else
      echo "   pending — python/ implementation not built yet (no pyproject.toml)."
      skip=$((skip + 1))
    fi
  else
    echo "   SKIP — uv not found. Install from https://docs.astral.sh/uv/"
    skip=$((skip + 1))
  fi
  echo
fi

# --- pandoc ------------------------------------------------------------------
# Placeholder: the pandoc/ approach needs the pandoc binary (currently absent).
if want pandoc; then
  echo ">> pandoc"
  if have pandoc; then
    echo "   $(pandoc --version | head -1)"
    echo "   ok"
    ok=$((ok + 1))
  else
    echo "   SKIP — pandoc not installed. Install from https://pandoc.org/installing.html"
    echo "          (e.g. sudo apt-get install pandoc)"
    skip=$((skip + 1))
  fi
  echo
fi

echo "== done: $ok ready, $skip skipped/pending =="
echo "Next: ./regenerate.sh   (renders fixtures into output/<impl>/)"
