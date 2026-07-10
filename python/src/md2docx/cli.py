"""Typer CLI. Owns argument parsing, output, and error display only — all logic
lives in ``core``; all config lives in ``config_models``."""

from __future__ import annotations

import enum
import signal
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from typing_extensions import Annotated

from . import core
from .config_models import RunConfig, build_config, save_config
from .exceptions import ConfigError, ConversionError

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(add_completion=False, help="Convert Markdown into a styled Word (.docx) document.")


class Verbosity(enum.IntEnum):
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2


_verbosity = Verbosity.NORMAL


def _p(msg: str, level: Verbosity, style: str, *, bold: bool = False) -> None:
    if _verbosity >= level:
        err_console.print(msg, style=f"bold {style}" if bold else style)


def info(msg: str) -> None:
    _p(msg, Verbosity.NORMAL, "cyan")


def detail(msg: str) -> None:
    _p(msg, Verbosity.VERBOSE, "white")


def warn(msg: str, *, bold: bool = False) -> None:
    _p(msg, Verbosity.NORMAL, "yellow", bold=bold)


def success(msg: str, *, bold: bool = False) -> None:
    _p(msg, Verbosity.NORMAL, "green", bold=bold)


def error(msg: str) -> None:
    err_console.print(msg, style="bold red")  # errors always print


def _set_verbosity(quiet: bool, verbose: bool) -> None:
    global _verbosity
    if quiet and verbose:
        error("Options --quiet and --verbose are mutually exclusive.")
        raise typer.Exit(code=EXIT_USAGE)
    if quiet:
        _verbosity = Verbosity.QUIET
    elif verbose:
        _verbosity = Verbosity.VERBOSE


@app.command()
def convert(
    input_file: Annotated[
        Optional[Path],
        typer.Argument(help="Input markdown file. Overrides config."),
    ] = None,
    config_file: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="YAML or JSON config file.", exists=True, readable=True),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output .docx path. Overrides config."),
    ] = None,
    title: Annotated[Optional[str], typer.Option("--title", help="Cover title. Overrides config.")] = None,
    eyebrow: Annotated[Optional[str], typer.Option("--eyebrow", help="Cover eyebrow. Overrides config.")] = None,
    subtitle: Annotated[
        Optional[list[str]],
        typer.Option("--subtitle", help="Cover subtitle (repeatable). Overrides config."),
    ] = None,
    logo: Annotated[Optional[str], typer.Option("--logo", help="Cover logo path. Overrides config.")] = None,
    logo_width: Annotated[
        Optional[int], typer.Option("--logo-width", help="Logo width in px. Overrides config.")
    ] = None,
    footer: Annotated[Optional[str], typer.Option("--footer", help="Footer text. Overrides config.")] = None,
    page_numbers: Annotated[
        Optional[bool],
        typer.Option("--page-numbers/--no-page-numbers", help="Footer page numbers. Overrides config."),
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Render without writing any file.")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress non-error output.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Convert a markdown file into a styled .docx."""
    _set_verbosity(quiet, verbose)

    try:
        cfg = build_config(
            config_file,
            input_path=str(input_file) if input_file else None,
            output_path=str(output) if output else None,
            title=title,
            eyebrow=eyebrow,
            subtitles=subtitle,
            logo=logo,
            logo_width=logo_width,
            footer_text=footer,
            page_numbers=page_numbers,
        )
    except ValidationError as exc:
        for err in exc.errors():
            field = " -> ".join(str(loc) for loc in err["loc"])
            error(f"Config field '{field}': {err['msg']}")
        raise typer.Exit(code=EXIT_USAGE)
    except (ConfigError, ValueError, FileNotFoundError) as exc:
        error(f"Configuration error: {exc}")
        raise typer.Exit(code=EXIT_USAGE)

    if dry_run:
        warn("Dry-run mode — no file will be written.", bold=True)
    detail(f"Effective config: {cfg.model_dump()}")

    try:
        result = core.convert(cfg, dry_run=dry_run)
    except ConversionError as exc:
        error(f"Conversion failed: {exc}")
        raise typer.Exit(code=EXIT_ERROR)

    for w in result.warnings:
        if w.startswith("image-not-found:"):
            warn(f"image not found: {w.split(':', 1)[1]}")
        elif w.startswith("logo-not-usable:"):
            warn(f"logo not usable: {w.split(':', 1)[1]}")
        else:
            warn(f"stripped HTML tag (kept inner text): <{w}>")

    if not dry_run:
        source_format = "yaml" if (config_file and config_file.suffix in (".yaml", ".yml")) else "json"
        saved = save_config(cfg, result.output_dir, source_format, result.output_path.stem)
        detail(f"Saved effective config to {saved}")
        info(f"Wrote {result.output_path}")

    success("Done.", bold=True)


@app.command(name="generate-config")
def generate_config(
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Destination path for the template config.")
    ] = Path("md2docx.yaml"),
    fmt: Annotated[str, typer.Option("--format", help="Template format: yaml or json.")] = "yaml",
) -> None:
    """Write a template configuration file populated with all default values."""
    template = RunConfig(input_path="input.md").model_dump()
    if fmt == "yaml":
        output.write_text(yaml.dump(template, default_flow_style=False, sort_keys=False), encoding="utf-8")
    elif fmt == "json":
        import json

        output.write_text(json.dumps(template, indent=2), encoding="utf-8")
    else:
        error(f"Unknown format {fmt!r}. Use 'yaml' or 'json'.")
        raise typer.Exit(code=EXIT_USAGE)
    success(f"Template written to {output}", bold=True)


def _handle_sigterm(signum: int, frame: object) -> None:
    warn("\nReceived SIGTERM — shutting down.")
    raise SystemExit(EXIT_INTERRUPTED)


signal.signal(signal.SIGTERM, _handle_sigterm)


def cli() -> None:
    try:
        app()
    except KeyboardInterrupt:
        warn("\nInterrupted.")
        sys.exit(EXIT_INTERRUPTED)
    except BrokenPipeError:
        sys.stderr.close()
        sys.exit(EXIT_OK)
    except SystemExit as exc:
        sys.exit(exc.code)
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        error(f"Unexpected error: {exc}")
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    cli()
