# md2docx

Convert a Markdown file into a **styled Word (`.docx`)** document.

The content comes from the markdown file; everything else — the theme (colors,
fonts, page geometry) and the "chrome" (cover title, eyebrow, subtitles, logo,
footer, page numbers) — is passed on the command line. No frontmatter.

Multiple implementations live side by side:

| Folder     | Approach                                        | Status |
|------------|-------------------------------------------------|--------|
| `js/`      | Node + [`markdown-it`](https://github.com/markdown-it/markdown-it) + [`docx`](https://docx.js.org) | ✅ done |
| `python/`  | Python + [`markdown-it-py`](https://markdown-it-py.readthedocs.io) + [`python-docx`](https://python-docx.readthedocs.io) (config-driven Typer CLI) | ✅ done |
| `pandoc/`  | [pandoc](https://pandoc.org) + a restyled `--reference-doc` | ✅ done |

## Setup & regenerate

```bash
./setup.sh                 # install deps for every available implementation
./regenerate.sh            # regenerate ALL impls -> output/{js,python,pandoc}/
./regenerate.sh js pandoc  # or just the named ones
```

`regenerate.sh` dispatches to each implementation's own `regenerate.sh`
(`js/`, `python/`, `pandoc/`) and skips any whose toolchain isn't installed.

## Performance

`perf/` is a config-driven benchmark harness (Typer/pydantic) that generates
random markdown of several size classes (generation is not timed) and measures
each implementation's throughput:

```bash
./perf/run.sh              # 100 short + 10×20-page + 3×100-page, all impls
```

See `perf/README.md` for config and metrics.

See each implementation's README (`js/`… , `python/README.md`, `pandoc/README.md`)
and `examples/README.md` for runnable inputs (plain vs. Circeus-branded). The same
Circeus theme drives all three; the pandoc version has some inherent trade-offs
(no cover logo, footer baked into the reference) noted in `pandoc/README.md`.

## Skills (`skills/`)

Two self-contained Claude skills — `md2docx-python` (bundles the lite engine) and
`md2docx-js` (bundles the JS impl) — each convert a markdown file or string to a
styled `.docx`. They deliberately reference nothing else in the repo, so the
engine is *copied* into them. That copy is generated:

```bash
uv --project python run python scripts/build_skills.py          # rebuild bundles
uv --project python run python scripts/build_skills.py --check   # fail if drifted
./scripts/install-hooks.sh                                        # pre-commit auto-sync
```

`setup.sh` installs the pre-commit hook and builds the bundles; after that, any
change to the engine / JS / branded theme re-syncs the skills automatically on
commit.

End-to-end tests exercise each skill's tools (file + string, default + branded)
and **skip** a skill whose toolchain (`uv` / `node`) isn't installed rather than
failing:

```bash
./scripts/test-skills.sh          # or: uv --project python run pytest tests/test_skills.py -v
```

## JavaScript version

### Install

```bash
cd js
npm install
```

### Usage

```bash
node src/index.js <input.md> [options]
```

| Option              | Description                                              | Default              |
|---------------------|----------------------------------------------------------|----------------------|
| `-o, --out <file>`  | Output `.docx` path                                      | input basename `.docx` |
| `--theme <name\|path>` | Built-in theme name or path to a theme `.json`        | `circeus-light`      |
| `--title <str>`     | Cover title (a cover page is only emitted if given)      | —                    |
| `--eyebrow <str>`   | Small label above the cover title                        | —                    |
| `--subtitle <str>`  | Cover subtitle — repeatable                              | —                    |
| `--logo <path>`     | Cover logo image (only used if the file exists)          | —                    |
| `--logo-width <px>` | Logo width in pixels                                     | `160`                |
| `--footer <str>`    | Footer text (left side)                                  | —                    |
| `--page-numbers`    | Show `Page N` at the footer right                        | off                  |

### Example

```bash
node src/index.js report.md -o report.docx \
  --theme circeus-light \
  --eyebrow "Internal engineering report" \
  --title "IP protection: multi-turn leakage detection" \
  --subtitle "Branch: feature/ip_protection_advanced" \
  --subtitle "Period: June – July 2026" \
  --footer "Circeus — confidential" \
  --page-numbers
```

### Supported Markdown

Headings (`#`–`######`, h4–h6 fall back to h3), paragraphs, **bold**, *italic*,
`inline code`, links, nested bullet & ordered lists, GFM pipe tables (with column
alignment), fenced/indented code blocks, blockquotes, `---` dividers, and images.

### HTML caveat

`markdown-it` is constructed with `{ html: false }`. Raw HTML is **not** rendered
as HTML: tags are stripped but their inner text is kept, `<br>` becomes a line
break, and a warning is printed to stderr listing which tags were stripped — so
nothing disappears silently.

## Tests

```bash
cd js && npm install
node --test ../tests/run.mjs
```
