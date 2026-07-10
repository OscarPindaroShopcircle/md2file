---
name: md2docx-js
description: "Convert Markdown into a styled Word (.docx) document (JavaScript). Use whenever the user wants to turn markdown text or a markdown file into a Word/.docx document, optionally styled (Circeus brand by default). Self-contained — bundles the JS implementation; needs only Node + npm. Two tools: convert a markdown FILE, or convert a markdown STRING, with optional theme, cover title/eyebrow/subtitles, footer, page numbers, and logo."
---

# md2docx (JavaScript, self-contained)

Convert Markdown to a styled Word `.docx`. This skill bundles a complete JS
implementation (`app/`, using `markdown-it` + `docx`) — it does **not** depend on
any other project. **The default style is Circeus.**

Requirements: Node.js (>=18) and npm. The bundled dependencies install
automatically into `app/node_modules` on first use.

The two tools are small Python scripts that shell out to the bundled Node CLI.
Run them from this skill's directory.

## Tool 1 — convert a markdown FILE

```bash
python scripts/convert_file.py <input.md> [options]
```

Best when the markdown exists on disk (image paths resolve relative to the file).

## Tool 2 — convert a markdown STRING

```bash
python scripts/convert_string.py --text "<markdown>" [options]
# or pipe it:
echo "# Title" | python scripts/convert_string.py [options]
```

For markdown in hand. If `--out` is omitted, a temp `.docx` is written and its
path printed. (A string has no directory, so relative image links won't resolve —
use the file tool for documents with local images.)

## Options (both tools)

| Option             | Meaning                                                         |
|--------------------|----------------------------------------------------------------|
| `-o, --out PATH`   | Output `.docx` (default: input basename `.docx`, or a temp file). |
| `--theme NAME\|PATH` | Theme name (bundled: `circeus-light`, `circeus-brand`) or path to a theme `.json`. Default: Circeus. |
| `--title STR`      | Cover title (emits a cover page).                              |
| `--eyebrow STR`    | Small label above the cover title.                            |
| `--subtitle STR`   | Cover subtitle — repeatable.                                  |
| `--footer STR`     | Footer text.                                                  |
| `--page-numbers`   | Show "Page N" in the footer.                                  |
| `--logo PATH`      | Cover logo image.                                             |
| `--logo-width N`   | Logo width in px.                                             |

## Styling

- **Default is Circeus** — pass nothing (built-in `circeus-light`).
- **Branded Circeus** (monochrome) is bundled: `--theme circeus-brand`, and for
  the cover mark `--logo assets/circeus-logo.png`.
- **Custom theme**: `--theme /path/to/theme.json` (see `app/themes/circeus-light.json`).

## Examples

```bash
# simplest — Circeus style, output next to the input
python scripts/convert_file.py notes.md

# report with cover + page numbers
python scripts/convert_file.py notes.md -o /tmp/report.docx \
  --title "Quarterly Report" --eyebrow "Internal" --subtitle "Q3 2026" \
  --footer "Confidential" --page-numbers

# convert a snippet to a temp file
python scripts/convert_string.py --text $'# Hello\n\nSome **bold** text.'

# branded Circeus, with the bundled logo
python scripts/convert_file.py notes.md --theme circeus-brand --logo assets/circeus-logo.png
```

## Supported Markdown

Headings, paragraphs, bold/italic/inline-code, links, nested bullet & ordered
lists, GFM tables (with alignment), fenced code, blockquotes, `---` dividers, and
images. Raw HTML tags are stripped (inner text kept; `<br>` becomes a line break).
