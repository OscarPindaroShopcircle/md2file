---
name: md2docx-python
description: "Convert Markdown into a styled Word (.docx) document (Python). Use whenever the user wants to turn markdown text or a markdown file into a Word/.docx document, optionally styled (Circeus brand by default). Self-contained — no external project needed, only `uv`. Two tools: convert a markdown FILE, or convert a markdown STRING, with optional theme, cover title/eyebrow/subtitles, footer, page numbers, and logo."
---

# md2docx (Python, self-contained)

Convert Markdown to a styled Word `.docx`. This skill bundles a complete,
minimal-dependency engine (`md2docx_lite/`, using only `markdown-it-py` +
`python-docx`) — it does **not** depend on any other project. **The default style
is Circeus.**

Requirement: [`uv`](https://docs.astral.sh/uv/). The tools carry inline
dependency metadata, so `uv run` installs `markdown-it-py` + `python-docx`
automatically on first use — nothing else to set up.

Run the tools from this skill's directory.

## Tool 1 — convert a markdown FILE

```bash
uv run scripts/convert_file.py <input.md> [options]
```

Best when the markdown exists on disk (image paths resolve relative to the file).

## Tool 2 — convert a markdown STRING

```bash
uv run scripts/convert_string.py --text "<markdown>" [options]
# or pipe it:
echo "# Title" | uv run scripts/convert_string.py [options]
```

For markdown in hand. If `--out` is omitted, a temp `.docx` is written and its
path printed. (A string has no directory, so relative image links won't resolve —
use the file tool for documents with local images.)

## Options (both tools)

| Option            | Meaning                                                          |
|-------------------|-----------------------------------------------------------------|
| `-o, --out PATH`  | Output `.docx` (default: input basename `.docx`, or a temp file). |
| `-c, --config F`  | YAML/JSON run config for a custom **theme + chrome**. Omit for Circeus. |
| `--title STR`     | Cover title (emits a cover page).                                |
| `--eyebrow STR`   | Small label above the cover title.                              |
| `--subtitle STR`  | Cover subtitle — repeatable.                                    |
| `--footer STR`    | Footer text.                                                    |
| `--page-numbers`  | Show "Page N" in the footer.                                    |
| `--logo PATH`     | Cover logo image.                                               |
| `--logo-width N`  | Logo width in px.                                               |

## Styling

- **Default is Circeus** — pass nothing.
- **Branded Circeus** (monochrome + logo) is bundled: `-c themes/circeus-brand.json`
  and, for the cover mark, `--logo assets/circeus-logo.png`.
- **Custom theme**: pass `-c` with your own JSON run config (a `theme:` section,
  optionally `chrome:`). YAML also works if `pyyaml` is available, but JSON needs
  no extra dependency.

## Examples

```bash
# simplest — Circeus style, output next to the input
uv run scripts/convert_file.py notes.md

# report with cover + page numbers
uv run scripts/convert_file.py notes.md -o /tmp/report.docx \
  --title "Quarterly Report" --eyebrow "Internal" --subtitle "Q3 2026" \
  --footer "Confidential" --page-numbers

# convert a snippet to a temp file
uv run scripts/convert_string.py --text $'# Hello\n\nSome **bold** text.'

# branded Circeus, with the bundled logo
uv run scripts/convert_file.py notes.md -c themes/circeus-brand.json --logo assets/circeus-logo.png
```

## Supported Markdown

Headings, paragraphs, bold/italic/inline-code, links, nested bullet & ordered
lists, GFM tables (with alignment), fenced code, blockquotes, `---` dividers, and
images. Raw HTML tags are stripped (inner text kept; `<br>` becomes a line break).
