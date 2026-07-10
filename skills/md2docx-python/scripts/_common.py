"""Shared helpers for the md2docx-python skill tools (self-contained)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the bundled `md2docx_lite` package importable regardless of cwd.
_SKILL_DIR = Path(__file__).resolve().parent.parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))


def add_style_args(ap: argparse.ArgumentParser) -> None:
    """Styling / chrome / output options common to both tools."""
    ap.add_argument("-o", "--out", help="Output .docx path.")
    ap.add_argument(
        "-c",
        "--config",
        help="YAML/JSON run config (theme + chrome). Omit for the built-in Circeus style.",
    )
    ap.add_argument("--title", help="Cover title (emits a cover page).")
    ap.add_argument("--eyebrow", help="Small label above the cover title.")
    ap.add_argument("--subtitle", action="append", help="Cover subtitle (repeatable).")
    ap.add_argument("--footer", help="Footer text.")
    ap.add_argument("--page-numbers", action="store_true", default=None, help="Show 'Page N' in the footer.")
    ap.add_argument("--logo", help="Cover logo image path.")
    ap.add_argument("--logo-width", type=int, help="Logo width in px.")


def make_config(a: argparse.Namespace, *, input_path: str, output_path: str | None):
    """Build a lite RunConfig from parsed args (paths absolutized)."""
    from md2docx_lite.config import build_config

    config_file = Path(a.config).resolve() if a.config else None
    return build_config(
        config_file,
        input_path=input_path,
        output_path=output_path,
        title=a.title,
        eyebrow=a.eyebrow,
        subtitles=a.subtitle,
        logo=str(Path(a.logo).resolve()) if a.logo else None,
        logo_width=a.logo_width,
        footer_text=a.footer,
        page_numbers=a.page_numbers,
    )


def report(result) -> None:
    """Print the output path and any warnings."""
    for w in result.warnings:
        if w.startswith("image-not-found:"):
            print(f"warning: image not found: {w.split(':', 1)[1]}", file=sys.stderr)
        elif w.startswith("logo-not-usable:"):
            print(f"warning: logo not usable: {w.split(':', 1)[1]}", file=sys.stderr)
        else:
            print(f"warning: stripped HTML tag (kept inner text): <{w}>", file=sys.stderr)
    print(f"wrote {result.output_path}")
