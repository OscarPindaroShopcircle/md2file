#!/usr/bin/env bash
# Shared ANSI color helpers for the repo's shell scripts.
#
# Convention (matches .devin/rules/typer-cli.md):
#   green  -> success / "all ok"      (bold for final "Done")
#   red    -> errors                  (always bold)
#   yellow -> warnings / caution
#   cyan   -> informational / section headers (bold for headers)
#   white  -> generic text / detail
# No emojis. Warnings/errors go to stderr; progress goes to stdout. Color is
# auto-disabled when the target stream isn't a TTY or NO_COLOR is set.

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then _co_out=1; else _co_out=0; fi
if [[ -t 2 && -z "${NO_COLOR:-}" ]]; then _co_err=1; else _co_err=0; fi

_paint() {  # <fd> <sgr> <msg...>
  local fd="$1" sgr="$2"; shift 2
  local on; [[ "$fd" == 1 ]] && on=$_co_out || on=$_co_err
  if [[ "$on" == 1 ]]; then
    printf '\e[%sm%s\e[0m\n' "$sgr" "$*" >&"$fd"
  else
    printf '%s\n' "$*" >&"$fd"
  fi
}

c_header()  { _paint 1 "1;36" "$@"; }  # bold cyan  — section headers
c_info()    { _paint 1 "36"   "$@"; }  # cyan       — informational
c_step()    { _paint 1 "37"   "$@"; }  # white      — detail / list items
c_success() { _paint 1 "32"   "$@"; }  # green      — success
c_done()    { _paint 1 "1;32" "$@"; }  # bold green — final "Done"
c_warn()    { _paint 2 "33"   "$@"; }  # yellow     — warnings (stderr)
c_error()   { _paint 2 "1;31" "$@"; }  # bold red   — errors (stderr)
