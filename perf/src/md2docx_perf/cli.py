"""Typer CLI for the performance harness. Owns parsing, output, and error
display only — logic lives in ``core``, config in ``config_models``."""

from __future__ import annotations

import enum
import json
import signal
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table
from typing_extensions import Annotated

from . import core
from .config_models import BenchConfig, build_config, save_config
from .exceptions import BenchError, ConfigError

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130

console = Console()  # stdout — the results table
err_console = Console(stderr=True)  # stderr — diagnostics

app = typer.Typer(add_completion=False, help="Config-driven performance harness for the md2docx implementations.")


class Verbosity(enum.IntEnum):
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2


_verbosity = Verbosity.NORMAL


def _emit(msg: str, level: Verbosity, color: str, *, bold: bool = False) -> None:
    if _verbosity >= level:
        style = f"bold {color}" if bold else color
        err_console.print(f"[{style}]{msg}[/{style}]")


def print_info(msg: str, *, bold: bool = False) -> None:
    _emit(msg, Verbosity.NORMAL, "cyan", bold=bold)


def print_detail(msg: str, *, bold: bool = False) -> None:
    _emit(msg, Verbosity.VERBOSE, "white", bold=bold)


def print_warning(msg: str, *, bold: bool = False) -> None:
    _emit(msg, Verbosity.NORMAL, "yellow", bold=bold)


def print_success(msg: str, *, bold: bool = False) -> None:
    _emit(msg, Verbosity.NORMAL, "green", bold=bold)


def print_error(msg: str) -> None:
    err_console.print(f"[bold red]{msg}[/bold red]")  # errors always print


def _set_verbosity(quiet: bool, verbose: bool) -> None:
    global _verbosity
    if quiet and verbose:
        print_error("Options --quiet and --verbose are mutually exclusive.")
        raise typer.Exit(code=EXIT_USAGE)
    if quiet:
        _verbosity = Verbosity.QUIET
    elif verbose:
        _verbosity = Verbosity.VERBOSE


def _render(out: core.BenchOutput) -> None:
    wpp = out.words_per_page
    for cls in out.classes:
        pages = cls.total_words / wpp
        mb = cls.total_bytes / 1e6
        table = Table(
            title=f"{cls.name} — {cls.files} files, {mb:.2f} MB, ~{pages:.1f} pages",
            title_style="bold cyan",
            header_style="bold white",
        )
        table.add_column("impl", style="cyan")
        for col in ("total (s)", "ms/doc", "docs/s", "MB/s", "pages/s"):
            table.add_column(col, justify="right")
        for r in cls.results:
            if not r.ok:
                table.add_row(r.name, "[red]FAILED[/red]", r.error or "", "", "", "")
                continue
            secs = r.total_seconds
            table.add_row(
                r.name,
                f"{secs:.3f}",
                f"{secs / cls.files * 1000:.1f}",
                f"{cls.files / secs:.2f}",
                f"{mb / secs:.2f}",
                f"{pages / secs:.1f}",
            )
        console.print(table)


@app.command()
def run(
    config_file: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="YAML or JSON config file.", exists=True, readable=True),
    ] = None,
    inputs_dir: Annotated[Optional[str], typer.Option("--inputs-dir", help="Inputs dir. Overrides config.")] = None,
    output_dir: Annotated[Optional[str], typer.Option("--output-dir", help="Output dir. Overrides config.")] = None,
    words_per_page: Annotated[
        Optional[int], typer.Option("--words-per-page", help="Words per page. Overrides config.")
    ] = None,
    warmup: Annotated[
        Optional[bool], typer.Option("--warmup/--no-warmup", help="Warmup pass. Overrides config.")
    ] = None,
    regenerate: Annotated[
        Optional[bool], typer.Option("--regenerate/--no-regenerate", help="Ensure inputs exist. Overrides config.")
    ] = None,
    force: Annotated[
        Optional[bool], typer.Option("--force/--no-force", help="Re-create inputs even if cached. Overrides config.")
    ] = None,
    jobs: Annotated[
        Optional[int], typer.Option("--jobs", "-j", help="Parallel generation workers (default: CPUs). Overrides config.")
    ] = None,
    repo_root: Annotated[Optional[str], typer.Option("--repo-root", help="md2docx repo root. Overrides config.")] = None,
    impl: Annotated[
        Optional[list[str]], typer.Option("--impl", help="Implementation to benchmark (repeatable). Overrides config.")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Report the plan without generating or timing.")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress non-error output.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Generate inputs (untimed) and benchmark every implementation."""
    _set_verbosity(quiet, verbose)

    try:
        cfg = build_config(
            config_file,
            inputs_dir=inputs_dir,
            output_dir=output_dir,
            words_per_page=words_per_page,
            warmup=warmup,
            regenerate=regenerate,
            force=force,
            jobs=jobs,
            repo_root=repo_root,
            implementations=impl,
        )
    except ValidationError as exc:
        for err in exc.errors():
            field = " -> ".join(str(loc) for loc in err["loc"])
            print_error(f"Config field '{field}': {err['msg']}")
        raise typer.Exit(code=EXIT_USAGE)
    except (ConfigError, ValueError, FileNotFoundError) as exc:
        print_error(f"Configuration error: {exc}")
        raise typer.Exit(code=EXIT_USAGE)

    if dry_run:
        print_warning("Dry-run mode — no inputs generated, nothing timed.", bold=True)
    print_detail(f"Effective config: {cfg.model_dump()}")

    if dry_run:
        try:
            result = core.run(cfg, dry_run=True)
        except BenchError as exc:
            print_error(f"Benchmark failed: {exc}")
            raise typer.Exit(code=EXIT_ERROR)
        print_info(f"Would benchmark: {', '.join(result.impl_names)}")
        print_success("Done.", bold=True)
        return

    # Size the progress bars up front (needs the impl count).
    try:
        repo_root = core.resolve_repo_root(cfg.repo_root)
        impls = core.discover_impls(cfg, repo_root)
    except BenchError as exc:
        print_error(f"Benchmark failed: {exc}")
        raise typer.Exit(code=EXIT_ERROR)
    total_files = sum(sc.count for sc in cfg.sizes)
    total_gen = total_files if cfg.regenerate else 0
    total_conv = total_files * len(impls)

    show_progress = _verbosity >= Verbosity.NORMAL
    try:
        if show_progress:
            with Progress(
                TextColumn("[cyan]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                console=err_console,
                transient=True,
            ) as prog:
                gen_task = prog.add_task("generating", total=total_gen) if total_gen else None
                conv_task = prog.add_task("converting", total=total_conv)
                result = core.run(
                    cfg,
                    on_generate=(lambda: prog.advance(gen_task)) if gen_task is not None else None,
                    on_convert=lambda: prog.advance(conv_task),
                )
        else:
            result = core.run(cfg)
    except BenchError as exc:
        print_error(f"Benchmark failed: {exc}")
        raise typer.Exit(code=EXIT_ERROR)

    print_info(f"Implementations: {', '.join(result.impl_names)}")
    print_info(
        f"Input generation: {result.gen_seconds:.3f}s "
        f"({result.gen_written} written, {result.gen_cached} cached, {result.gen_workers} workers; "
        f"not counted in throughput)"
    )
    _render(result)

    source_format = "yaml" if (config_file and config_file.suffix in (".yaml", ".yml")) else "json"
    saved = save_config(cfg, result.output_dir, source_format)
    print_detail(f"Saved effective config to {saved}")
    print_success("Done.", bold=True)


@app.command(name="generate-config")
def generate_config(
    output: Annotated[Path, typer.Option("--output", "-o", help="Destination path.")] = Path("bench.yaml"),
    fmt: Annotated[str, typer.Option("--format", help="Template format: yaml or json.")] = "yaml",
) -> None:
    """Write a template config populated with all default values."""
    template = BenchConfig().model_dump()
    if fmt == "yaml":
        output.write_text(yaml.dump(template, default_flow_style=False, sort_keys=False), encoding="utf-8")
    elif fmt == "json":
        output.write_text(json.dumps(template, indent=2), encoding="utf-8")
    else:
        print_error(f"Unknown format {fmt!r}. Use 'yaml' or 'json'.")
        raise typer.Exit(code=EXIT_USAGE)
    print_success(f"Template written to {output}", bold=True)


def _handle_sigterm(signum: int, frame: object) -> None:
    print_warning("\nReceived SIGTERM — shutting down.")
    raise SystemExit(EXIT_INTERRUPTED)


signal.signal(signal.SIGTERM, _handle_sigterm)


def cli() -> None:
    try:
        app()
    except KeyboardInterrupt:
        print_warning("\nInterrupted.")
        sys.exit(EXIT_INTERRUPTED)
    except BrokenPipeError:
        sys.stderr.close()
        sys.exit(EXIT_OK)
    except SystemExit as exc:
        sys.exit(exc.code)
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        print_error(f"Unexpected error: {exc}")
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    cli()
