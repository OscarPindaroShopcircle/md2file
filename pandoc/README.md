# md2docx (pandoc)

Convert Markdown to a styled `.docx` with [pandoc](https://pandoc.org), applying
styling through a **reference document**:

```bash
pandoc input.md -o out.docx --reference-doc=reference.docx
```

Pandoc maps Markdown onto named Word styles (`Normal`, `Heading 1..6`, `Title`,
`Subtitle`, `Source Code`, `Block Text`, `Hyperlink`, ...). We take pandoc's
default reference and restyle those to match an md2docx theme, reusing the typed
theme models from the Python implementation — so the *same theme YAML* drives the
python-docx and pandoc outputs.

## Setup

Needs `pandoc` and the Python project (for the theme models):

```bash
../setup.sh pandoc      # installs pandoc (dnf/apt-get/brew) + builds references
# or manually:
./build-references.sh
```

This writes `references/circeus-light.docx` and `references/circeus-brand.docx`
(git-ignored).

## Usage

```bash
./convert.sh input.md -o out.docx \
  -r references/circeus-brand.docx \
  --title "My report" --subtitle "Q3 2026" --author "Circeus"
```

| Option              | Meaning                                             |
|---------------------|-----------------------------------------------------|
| `-o, --out`         | output `.docx` (required)                            |
| `-r, --ref`         | reference `.docx` (default `references/circeus-light.docx`) |
| `--title/--subtitle/--author` | pandoc title-block metadata               |

Regenerate all fixtures + examples into `output/pandoc/`:

```bash
./regenerate.sh
```

## How theming works

`build-references.sh` runs `build_reference.py`, which:

1. fetches pandoc's default reference (`pandoc --print-default-data-file reference.docx`),
2. restyles `Normal`, headings, `Title`/`Subtitle`, inline/block code, blockquote,
   and hyperlink styles from the theme's colors/fonts/sizes,
3. sets page geometry,
4. optionally bakes a **footer** (text + page numbers) from the theme YAML's
   `chrome:` block.

Add a new theme by dropping a YAML in `themes/` (same schema as the Python config)
and adding a `build ...` line in `build-references.sh`.

## Trade-offs vs. the JS / Python versions

The pandoc approach is the least code but the least control:

- **Title/subtitle/author** come from pandoc's title block (metadata), not a
  hand-built cover — so there's **no cover logo** (pandoc can't place one).
- **Footer text and page numbers** are baked into the *reference* document, not
  passed per-run (change them in the theme YAML and rebuild the reference).
- **Code blocks** get pandoc's syntax highlighting, which overrides the plain
  `Source Code` color for recognized languages.
- Raw HTML follows pandoc's own rules (tags dropped, inner text kept in docx).

For a bespoke cover with a logo and per-run chrome, use the JS or Python version.
