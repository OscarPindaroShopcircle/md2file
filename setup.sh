#!/usr/bin/env bash
#
# Set up the md2docx repository: check tooling and install dependencies for each
# implementation (js, python, pandoc).
#
# Usage:
#   ./setup.sh            # set up everything that is available
#   ./setup.sh js         # set up only specific implementations
#   ./setup.sh js python
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$ROOT/scripts/colors.sh"

# Implementations to set up (default: all).
TARGETS=("$@")
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=(js python pandoc)
fi

want() { for t in "${TARGETS[@]}"; do [[ "$t" == "$1" ]] && return 0; done; return 1; }
have() { command -v "$1" >/dev/null 2>&1; }

ok=0
skip=0

c_header "== md2docx setup =="
echo

# --- JavaScript (Node + npm) -------------------------------------------------
if want js; then
  c_header ">> js"
  if have node && have npm; then
    c_step "   node $(node --version), npm $(npm --version)"
    (cd "$ROOT/js" && npm install)
    c_success "   ok — run: node js/src/index.js <input.md> [options]"
    ok=$((ok + 1))
  else
    c_warn "   SKIP — node/npm not found. Install Node.js >= 18."
    skip=$((skip + 1))
  fi
  echo
fi

# --- Python (uv + python-docx) ----------------------------------------------
if want python; then
  c_header ">> python"
  if have uv; then
    c_step "   uv $(uv --version | awk '{print $2}')"
    if [[ -f "$ROOT/python/pyproject.toml" ]]; then
      (cd "$ROOT/python" && uv sync)
      c_success "   ok — run: uv run md2docx / md2docx-lite"
      ok=$((ok + 1))
    else
      c_warn "   pending — python/ implementation not built yet (no pyproject.toml)."
      skip=$((skip + 1))
    fi
  else
    c_warn "   SKIP — uv not found. Install from https://docs.astral.sh/uv/"
    skip=$((skip + 1))
  fi
  echo
fi

# --- pandoc ------------------------------------------------------------------
# The pandoc/ approach needs the pandoc binary. If it's missing we try to install
# it via whichever package manager is available (dnf / apt-get / brew).
install_pandoc() {
  if have dnf; then
    c_step "   using dnf"
    sudo dnf install -y pandoc
  elif have apt-get; then
    c_step "   using apt-get"
    sudo apt-get update && sudo apt-get install -y pandoc
  elif have brew; then
    c_step "   using brew"
    brew install pandoc
  else
    c_warn "   no supported package manager (dnf/apt-get/brew)."
    c_warn "   install manually: https://pandoc.org/installing.html"
    return 1
  fi
}

if want pandoc; then
  c_header ">> pandoc"
  ready=false
  if have pandoc; then
    c_step "   $(pandoc --version | head -1)"
    ready=true
  else
    c_info "   pandoc not found — attempting install..."
    if install_pandoc && have pandoc; then
      c_step "   $(pandoc --version | head -1)"
      ready=true
    fi
  fi
  if $ready; then
    # reference docs need the python package (for the typed theme models)
    if have uv && [[ -f "$ROOT/python/pyproject.toml" ]]; then
      (cd "$ROOT/python" && uv sync >/dev/null)
      "$ROOT/pandoc/build-references.sh"
    fi
    c_success "   ok"
    ok=$((ok + 1))
  else
    c_warn "   SKIP — could not install pandoc automatically."
    skip=$((skip + 1))
  fi
  echo
fi

# --- git hooks + self-contained skills --------------------------------------
# Keep the bundled skills in sync (pre-commit rebuilds them from repo sources).
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  c_header ">> skills / git hooks"
  "$ROOT/scripts/install-hooks.sh" >/dev/null && c_success "   git hooks installed"
  if have uv && [[ -f "$ROOT/python/pyproject.toml" ]]; then
    (cd "$ROOT/python" && uv sync >/dev/null)
    uv --project "$ROOT/python" run python "$ROOT/scripts/build_skills.py" >/dev/null && c_success "   skill bundles built"
  fi
  echo
fi

c_done "== done: $ok ready, $skip skipped/pending =="
c_info "Next: ./regenerate.sh   (renders fixtures into output/<impl>/)"
