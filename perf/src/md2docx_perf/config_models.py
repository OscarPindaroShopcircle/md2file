"""Pydantic config models, file loading, and CLI-override merging.

Config-driven per .devin/rules/typer-cli-config.md: every parameter can live in a
YAML/JSON file; CLI flags are optional overrides. No typer/rich imports here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .exceptions import ConfigError

Impl = Literal["js", "python", "python-lite", "pandoc"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SizeClass(_Model):
    name: str = Field(..., description="Label for this size class (e.g. 'short').")
    count: int = Field(..., gt=0, description="Number of files to generate/convert.")
    pages: float = Field(..., gt=0, description="Approx pages per file (1 page = words_per_page words).")
    seed: int = Field(0, description="RNG seed base for reproducible generation.")


def _default_sizes() -> list[SizeClass]:
    return [
        SizeClass(name="short", count=100, pages=0.4, seed=1),
        SizeClass(name="medium", count=10, pages=20, seed=2),
        SizeClass(name="large", count=3, pages=100, seed=3),
    ]


class BenchConfig(_Model):
    inputs_dir: str = Field("/tmp/md2docx-perf/inputs", description="Where generated markdown is written/read.")
    output_dir: str = Field("/tmp/md2docx-perf/out", description="Where converted .docx (and the effective config) go.")
    words_per_page: int = Field(500, gt=0, description="Words per 'page' for sizing and throughput.")
    warmup: bool = Field(True, description="Run one untimed conversion per implementation before timing.")
    regenerate: bool = Field(True, description="Ensure inputs exist before benchmarking (generation is not timed).")
    force: bool = Field(False, description="Re-create input files even if they already exist (ignore the cache).")
    jobs: Optional[int] = Field(
        None, ge=1, description="Parallel generation workers. null = number of CPUs."
    )
    repo_root: Optional[str] = Field(
        None, description="md2docx repo root. If null, auto-detected by walking up from the cwd."
    )
    implementations: Optional[list[Impl]] = Field(
        None, description="Implementations to benchmark. If null, auto-detect all available."
    )
    sizes: list[SizeClass] = Field(default_factory=_default_sizes, description="Size classes to benchmark.")


def load_config_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text) or {}
    if path.suffix == ".json":
        return json.loads(text)
    raise ConfigError(f"Unsupported config extension {path.suffix!r}. Use .yaml, .yml, or .json.")


def build_config(
    config_file: Optional[Path],
    *,
    inputs_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    words_per_page: Optional[int] = None,
    warmup: Optional[bool] = None,
    regenerate: Optional[bool] = None,
    force: Optional[bool] = None,
    jobs: Optional[int] = None,
    repo_root: Optional[str] = None,
    implementations: Optional[list[str]] = None,
) -> BenchConfig:
    """Merge a config file with CLI overrides. Priority: CLI > file > default."""
    base: dict = load_config_file(config_file) if config_file is not None else {}

    overrides: dict = {}
    if inputs_dir is not None:
        overrides["inputs_dir"] = inputs_dir
    if output_dir is not None:
        overrides["output_dir"] = output_dir
    if words_per_page is not None:
        overrides["words_per_page"] = words_per_page
    if warmup is not None:
        overrides["warmup"] = warmup
    if regenerate is not None:
        overrides["regenerate"] = regenerate
    if force is not None:
        overrides["force"] = force
    if jobs is not None:
        overrides["jobs"] = jobs
    if repo_root is not None:
        overrides["repo_root"] = repo_root
    if implementations:
        overrides["implementations"] = implementations

    return BenchConfig.model_validate({**base, **overrides})


def save_config(cfg: BenchConfig, output_dir: Path, source_format: str) -> Path:
    data = cfg.model_dump()
    if source_format == "yaml":
        out = output_dir / "bench_config_used.yaml"
        out.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")
    else:
        out = output_dir / "bench_config_used.json"
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out
