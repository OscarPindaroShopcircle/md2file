# md2docx (Python)

Pure-Python implementation of md2docx using [`python-docx`](https://python-docx.readthedocs.io)
and [`markdown-it-py`](https://markdown-it-py.readthedocs.io). It mirrors the JS
version's output but is **config-driven**: theme and chrome live in a YAML (or
JSON) config file, and CLI flags are optional overrides.

## Install

```bash
cd python
uv sync
```

## Usage

```bash
# convert with defaults (built-in circeus-light theme)
uv run md2docx convert path/to/input.md -o out.docx

# convert with a YAML config (theme + chrome) plus CLI overrides
uv run md2docx convert input.md -c theme.yaml --title "My report" --page-numbers

# emit a template config with every field + default value
uv run md2docx generate-config -o md2docx.yaml
```

### How configuration layers

Priority is **CLI flag > config file > built-in default**. After each run the
fully merged, validated config is written next to the output as
`<name>.used.yaml` / `.json` (mirroring the input format) for reproducibility.

Config shape (see `generate-config` output for the full schema):

```yaml
input_path: input.md
output_path: out.docx
theme:
  font: Calibri
  colors: { text: "1A202C", primary: "1A365D", ... }
  headings:
    h1: { size: 22, color: "1A365D", before: 18, after: 8, rule: true, bold: true }
  # ... page, body, code, table, numbering, cover, footer, image
chrome:
  title: "My report"
  eyebrow: "Internal"
  subtitles: ["Q3 2026"]
  logo: assets/logo.png
  footer_text: "Confidential"
  page_numbers: true
```

## Two CLIs, one engine

There are two front ends over the same rendering engine (`core` + `render`):

| Command        | Front-end deps                     | Config           |
|----------------|------------------------------------|------------------|
| `md2docx`      | typer, pydantic, rich, pyyaml      | YAML/JSON, validated |
| `md2docx-lite` | **stdlib only** (argparse, dataclasses, json) | JSON (YAML if pyyaml present) |

`md2docx-lite` exists for a minimal dependency footprint — importing it pulls in
no typer/pydantic/rich/pyyaml (enforced by a test). It reuses the exact same
engine, so its output is **byte-identical** to `md2docx` (the `tests/lite/`
parity suite asserts this at the config, engine, and CLI levels).

```bash
uv run md2docx-lite input.md -o out.docx --title "My report" --page-numbers
uv run md2docx-lite input.md -c config.json -o out.docx
```

## Architecture

Follows the config-driven Typer layout:

```
src/md2docx/
  cli.py              # Typer app; parsing, output, error display only
  config_models.py    # Pydantic models + load/build/save (no typer/rich)
  core.py             # convert(): md text -> saved .docx (no typer/rich/pydantic)
  exceptions.py       # exception classes only
  lite/               # barebones CLI (stdlib only), same engine
    config.py         # dataclass mirror of the config models
    cli.py            # argparse front end
  render/             # the rendering layer (tokens -> docx)
    context.py        # RunStyle / RenderContext value types
    oxml.py           # low-level OOXML helpers (borders, shading, hyperlinks, ...)
    numbering.py      # list numbering definitions (bullets + restart-per-ordered)
    inline.py         # inline tokens -> styled runs (+ HTML strip-and-warn)
    builders.py       # block builders (heading/body/table/code/cover/footer/...)
    renderer.py       # walks the token stream, owns list/quote/table state
```

## Tests

```bash
uv run pytest              # unit + integration + fuzzy
uv run pytest tests/unit   # fast, no docx written
```

- **unit** — pure functions: config merge/validation, inline run mapping, renderer state.
- **integration** — convert the shared fixtures in `../tests/fixtures`, inspect `word/document.xml`.
- **fuzzy** — generate random-but-known markdown, assert every injected sentinel
  survives into the document and nothing crashes.
