---
name: md2docx-circeus
description: "Convert Markdown into a Circeus-branded Word (.docx) document (JavaScript). Use whenever the user wants to turn markdown into a Word/.docx with Circeus branding — the branded theme and logo are applied automatically. Self-contained — bundles the JS implementation; needs only Node + npm. Two tools: convert a markdown FILE, or convert a markdown STRING."
---

# md2docx (Circeus-branded, self-contained)

Convert Markdown to a **Circeus-branded** Word `.docx`. The branded theme
(monochrome palette) and the Circeus logo are applied **automatically** — no
flags needed. This skill bundles a complete JS implementation (`app/`, using
`markdown-it` + `docx`) — it does **not** depend on any other project.

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

## Defaults

- **Theme**: `circeus-brand` (monochrome) — applied automatically.
- **Logo**: bundled `assets/circeus-logo.png` — applied automatically.

Override either with `--theme` or `--logo` if needed.

## Options (both tools)

| Option             | Meaning                                                         |
|--------------------|----------------------------------------------------------------|
| `-o, --out PATH`   | Output `.docx` (default: input basename `.docx`, or a temp file). |
| `--theme NAME\|PATH` | Override the theme (built-in: `circeus-light`, `circeus-brand`) or path to a theme `.json`. Default: `circeus-brand`. |
| `--title STR`      | Cover title (emits a cover page).                              |
| `--eyebrow STR`    | Small label above the cover title.                            |
| `--subtitle STR`   | Cover subtitle — repeatable.                                  |
| `--footer STR`     | Footer text.                                                  |
| `--page-numbers`   | Show "Page N" in the footer.                                  |
| `--logo PATH`      | Override the cover logo image. Default: bundled Circeus logo. |
| `--logo-width N`   | Logo width in px.                                             |

## Examples

```bash
# simplest — Circeus branded, with logo, output next to the input
python scripts/convert_file.py notes.md

# report with cover + page numbers
python scripts/convert_file.py notes.md -o /tmp/report.docx \
  --title "Quarterly Report" --eyebrow "Internal" --subtitle "Q3 2026" \
  --footer "Confidential" --page-numbers

# convert a snippet to a temp file
python scripts/convert_string.py --text $'# Hello\n\nSome **bold** text.'

# override to plain (unbranded) Circeus
python scripts/convert_file.py notes.md --theme circeus-light --logo none
```

## Supported Markdown

Headings, paragraphs, bold/italic/inline-code, links, nested bullet & ordered
lists, GFM tables (with alignment), fenced code, blockquotes, `---` dividers, and
images. Raw HTML tags are stripped (inner text kept; `<br>` becomes a line break).
