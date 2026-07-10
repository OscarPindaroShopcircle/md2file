#!/usr/bin/env python3
"""Convert a Markdown FILE into a styled Word (.docx) document.

Self-contained: shells out to the bundled JS (docx) implementation in ../app.
Default style: Circeus.

Examples:
  python convert_file.py report.md
  python convert_file.py report.md -o /tmp/out.docx --title "Q3" --page-numbers
  python convert_file.py report.md --theme /path/to/theme.json
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _common import add_style_args, node_command, style_argv


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="Path to the markdown file.")
    add_style_args(ap)
    a = ap.parse_args()

    src = Path(a.input).resolve()
    if not src.is_file():
        print(f"error: input file not found: {a.input}", file=sys.stderr)
        return 1

    cmd = node_command() + [str(src)] + style_argv(a)
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
