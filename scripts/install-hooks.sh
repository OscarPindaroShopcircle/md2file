#!/usr/bin/env bash
#
# Install the repo's git hooks by pointing git at the versioned hooks directory.
# Idempotent; safe to run repeatedly.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/colors.sh"

if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  c_warn "not a git repository — nothing to install."
  exit 0
fi

chmod +x "$ROOT/scripts/git-hooks/"* 2>/dev/null || true
git -C "$ROOT" config core.hooksPath scripts/git-hooks
c_success "installed git hooks (core.hooksPath = scripts/git-hooks)"
c_info "the pre-commit hook rebuilds the self-contained skills when their sources change."
