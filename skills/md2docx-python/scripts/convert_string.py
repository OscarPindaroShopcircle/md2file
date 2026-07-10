#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown-it-py>=3", "python-docx>=1.1"]
# ///
"""Convert a Markdown STRING into a styled Word (.docx) document.

Self-contained: uses the bundled lite md2docx engine (python-docx). Default
style: Circeus. Markdown comes from --text or stdin. If --out is omitted, a temp
.docx is written and its path printed. Run with `uv run convert_string.py ...`.

Examples:
  uv run convert_string.py --text "# Hello\n\nWorld" -o /tmp/hello.docx
  echo "# Hi" | uv run convert_string.py --title "Note"
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from _common import add_style_args, make_config, report


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

    try:
        from md2docx_lite.core import convert

        cfg = make_config(a, input_path=md_path, output_path=out)
        report(convert(cfg))
    finally:
        Path(md_path).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
