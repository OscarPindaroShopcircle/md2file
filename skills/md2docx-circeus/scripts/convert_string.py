#!/usr/bin/env python3
"""Convert a Markdown STRING into a Circeus-branded Word (.docx) document.

Self-contained: shells out to the bundled JS (docx) implementation in ../app.
Defaults: Circeus branded theme + bundled logo. Markdown comes from --text or
stdin. If --out is omitted, a temp .docx is written and its path printed.

Examples:
  python convert_string.py --text "# Hello\n\nWorld" -o /tmp/hello.docx
  echo "# Hi" | python convert_string.py --title "Note"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from _common import add_style_args, node_command, style_argv


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", help="Markdown text. If omitted, read from stdin.")
    add_style_args(ap)
    a = ap.parse_args()

    text = a.text if a.text is not None else sys.stdin.read()
    if not text.strip():
        print("error: no markdown text provided (use --text or pipe via stdin).", file=sys.stderr)
        return 1

    md_fd, md_path = tempfile.mkstemp(suffix=".md")
    os.close(md_fd)
    Path(md_path).write_text(text, encoding="utf-8")

    out = a.out
    if not out:
        docx_fd, out = tempfile.mkstemp(suffix=".docx")
        os.close(docx_fd)
        a.out = out

    cmd = node_command() + [md_path] + style_argv(a)
    rc = subprocess.run(cmd).returncode
    Path(md_path).unlink(missing_ok=True)
    if rc == 0:
        print(f"wrote {out}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
