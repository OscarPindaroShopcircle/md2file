#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown-it-py>=3", "python-docx>=1.1"]
# ///
"""Convert a Markdown FILE into a styled Word (.docx) document.

Self-contained: uses the bundled lite md2docx engine (python-docx). Default
style: Circeus. Run with `uv run convert_file.py ...` (deps auto-install).

Examples:
  uv run convert_file.py report.md
  uv run convert_file.py report.md -o /tmp/out.docx --title "Q3" --page-numbers
  uv run convert_file.py report.md -c mytheme.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import add_style_args, make_config, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="Path to the markdown file.")
    add_style_args(ap)
    a = ap.parse_args()

    src = Path(a.input).resolve()
    if not src.is_file():
        print(f"error: input file not found: {a.input}", file=sys.stderr)
        return 1

    from md2docx_lite.core import convert

    cfg = make_config(a, input_path=str(src), output_path=a.out)
    report(convert(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
