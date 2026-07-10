"""Barebones argparse CLI. Stdlib-only front end over the shared engine.

No typer, no pydantic, no rich. Deps used by this path: argparse/dataclasses/json
(stdlib) + the rendering engine (markdown-it-py, python-docx).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from md2docx import core

from . import config as cfgmod

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="md2docx-lite",
        description="Convert Markdown into a styled Word (.docx) document (barebones CLI).",
    )
    p.add_argument("input", nargs="?", help="Input markdown file (overrides config).")
    p.add_argument("-c", "--config", type=Path, help="JSON (or YAML) config file.")
    p.add_argument("-o", "--output", help="Output .docx path (overrides config).")
    p.add_argument("--title", help="Cover title (overrides config).")
    p.add_argument("--eyebrow", help="Cover eyebrow (overrides config).")
    p.add_argument("--subtitle", action="append", help="Cover subtitle, repeatable (overrides config).")
    p.add_argument("--logo", help="Cover logo path (overrides config).")
    p.add_argument("--logo-width", type=int, help="Logo width in px (overrides config).")
    p.add_argument("--footer", help="Footer text (overrides config).")
    pn = p.add_mutually_exclusive_group()
    pn.add_argument("--page-numbers", dest="page_numbers", action="store_true", default=None,
                    help="Show footer page numbers (overrides config).")
    pn.add_argument("--no-page-numbers", dest="page_numbers", action="store_false",
                    help="Hide footer page numbers (overrides config).")
    p.add_argument("--dry-run", action="store_true", help="Render without writing a file.")
    p.add_argument("-q", "--quiet", action="store_true", help="Suppress non-error output.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.config is not None and not args.config.is_file():
        print(f"error: config not found: {args.config}", file=sys.stderr)
        return EXIT_USAGE

    try:
        cfg = cfgmod.build_config(
            args.config,
            input_path=args.input,
            output_path=args.output,
            title=args.title,
            eyebrow=args.eyebrow,
            subtitles=args.subtitle,
            logo=args.logo,
            logo_width=args.logo_width,
            footer_text=args.footer,
            page_numbers=args.page_numbers,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    try:
        result = core.convert(cfg, dry_run=args.dry_run)
    except Exception as exc:  # engine-level failure (e.g. missing input)
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    for w in result.warnings:
        if w.startswith("image-not-found:"):
            print(f"warning: image not found: {w.split(':', 1)[1]}", file=sys.stderr)
        elif w.startswith("logo-not-usable:"):
            print(f"warning: logo not usable: {w.split(':', 1)[1]}", file=sys.stderr)
        else:
            print(f"warning: stripped HTML tag (kept inner text): <{w}>", file=sys.stderr)

    if not args.dry_run and not args.quiet:
        print(f"wrote {result.output_path}")
    return EXIT_OK


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
