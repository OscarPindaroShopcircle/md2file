"""Shared helpers for the md2docx-js skill tools (self-contained)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# The bundled JS implementation lives next to this skill.
APP_DIR = Path(__file__).resolve().parent.parent / "app"


def node_command() -> list[str]:
    node = shutil.which("node")
    if not node:
        sys.exit("error: 'node' not found on PATH. Install Node.js (>=18).")
    if not (APP_DIR / "node_modules").exists():
        npm = shutil.which("npm")
        if not npm:
            sys.exit("error: 'npm' not found; cannot install the bundled JS dependencies.")
        print("installing bundled js dependencies (first run only)...", file=sys.stderr)
        r = subprocess.run([npm, "install", "--prefix", str(APP_DIR), "--no-audit", "--no-fund"])
        if r.returncode != 0:
            sys.exit("error: npm install failed for the bundled JS implementation.")
    return [node, str(APP_DIR / "src" / "index.js")]


def add_style_args(ap: argparse.ArgumentParser) -> None:
    """Styling / chrome / output options common to both tools."""
    ap.add_argument("-o", "--out", help="Output .docx path.")
    ap.add_argument(
        "--theme",
        default="circeus-light",
        help="Theme name (built-in: circeus-light) or path to a theme .json. Default: Circeus.",
    )
    ap.add_argument("--title", help="Cover title (emits a cover page).")
    ap.add_argument("--eyebrow", help="Small label above the cover title.")
    ap.add_argument("--subtitle", action="append", help="Cover subtitle (repeatable).")
    ap.add_argument("--footer", help="Footer text.")
    ap.add_argument("--page-numbers", action="store_true", help="Show 'Page N' in the footer.")
    ap.add_argument("--logo", help="Cover logo image path.")
    ap.add_argument("--logo-width", type=int, help="Logo width in px.")


def _resolve_theme(theme: str) -> str:
    """Absolutize a theme that's a file path; leave built-in names untouched."""
    if theme.endswith(".json") or "/" in theme:
        p = Path(theme)
        if p.exists():
            return str(p.resolve())
    return theme


def style_argv(a: argparse.Namespace) -> list[str]:
    """Translate parsed style args into js-CLI flags (paths absolutized)."""
    argv: list[str] = ["--theme", _resolve_theme(a.theme)]
    if a.out:
        argv += ["-o", a.out]
    if a.title:
        argv += ["--title", a.title]
    if a.eyebrow:
        argv += ["--eyebrow", a.eyebrow]
    for s in a.subtitle or []:
        argv += ["--subtitle", s]
    if a.footer:
        argv += ["--footer", a.footer]
    if a.logo:
        argv += ["--logo", str(Path(a.logo).resolve())]
    if a.logo_width:
        argv += ["--logo-width", str(a.logo_width)]
    if a.page_numbers:
        argv += ["--page-numbers"]
    return argv
