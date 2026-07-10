# md2docx performance harness

A config-driven [Typer](https://typer.tiangolo.com) CLI that benchmarks the
throughput of each md2docx implementation (js, python, python-lite, pandoc).

It generates random-but-valid markdown of a few size classes into a temp dir
(**generation is not timed**), then converts each file with every available
implementation in its own process and reports throughput.

## Run

```bash
../setup.sh            # make sure js/python/pandoc are installed first
./run.sh               # generate inputs + benchmark (defaults)
./run.sh --no-warmup --impl js --impl pandoc   # subset, no warmup
```

Or directly:

```bash
uv run md2docx-bench run -c bench.yaml
uv run md2docx-bench generate-config -o bench.yaml   # template with all defaults
```

## Defaults

Three size classes (1 page ≈ 500 words): `short` (100 files, ~0.4 pages),
`medium` (10 files, 20 pages), `large` (3 files, 100 pages). Override via
`bench.yaml`:

Input generation is **parallel** (`jobs`, default = CPU count) and **deterministic
+ cached**: each file's content depends only on its seed, and a file that already
exists is reused — so re-running regenerates nothing. Change `pages`/`words_per_page`?
Set `force: true` (or `--force`) to ignore the cache, or delete `inputs_dir`.

Config file:

```yaml
inputs_dir: /tmp/md2docx-perf/inputs
output_dir: /tmp/md2docx-perf/out
words_per_page: 500
warmup: true
regenerate: true
implementations: null        # null = auto-detect all available
sizes:
  - {name: short,  count: 100, pages: 0.4, seed: 1}
  - {name: medium, count: 10,  pages: 20,  seed: 2}
  - {name: large,  count: 3,   pages: 100, seed: 3}
```

Priority is **CLI flag > config file > default**; the effective config is written
to `output_dir/bench_config_used.{yaml,json}` after each run.

## Metrics

Per size class: total time, ms/doc, and throughput in docs/s, MB/s, and pages/s.
Each conversion runs as a separate process, so timings include real per-invocation
startup cost (which dominates for many small files and amortizes for large ones).

## Structure (config-driven Typer layout)

```
src/md2docx_perf/
  cli.py             # Typer app, rich tables, output/error display
  config_models.py   # Pydantic BenchConfig + load/build/save (no typer/rich)
  core.py            # markdown generation + subprocess timing (no typer/rich/pydantic)
  exceptions.py      # exception classes only
```
