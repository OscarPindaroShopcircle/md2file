# md2docx — markdown → styled Word (.docx) converter

## Context

There is a one-off Node script (using the `docx` library) that produces a beautifully
styled Word report ("IP protection: multi-turn leakage detection"). It works, but it
hardcodes three things that should be separated:

1. **Styling** (colors, fonts, sizes, page geometry) — baked into `COLOR`/`FONT`/`PAGE_*` consts.
2. **Chrome** (logo path, eyebrow text, cover title/subtitles, footer text) — literal strings.
3. **Content** — every heading/paragraph/bullet/table is a hand-written `h2(...)`, `bullet(...)`,
   `makeTable(...)` call.

Goal: a reusable tool that takes **any markdown file as input** and emits a `.docx`, where a
procedural parser reads the markdown and calls the existing pretty docx builder functions.
The nice rendering layer (the builders) is kept; only the fragile hand-authored front end is replaced.

This plan covers the **JavaScript** implementation first (per the user). Python and pandoc
versions come later — their folders are created as placeholders now.

Tooling confirmed available: Node v22.22.2, npm 10.9.7 (pandoc NOT installed; Python 3.14 + uv present).

## Decisions (locked with user)

- **Location:** `~/md2docx` (a new standalone folder, OUTSIDE the `guardrails` repo).
- **Parser:** use **`markdown-it`** to tokenize, then map its token stream onto the docx builders.
  Not a hand-rolled regex parser. markdown-it is constructed with `{ html: false }`.
- **Inline/raw HTML:** NOT rendered as HTML. Strip the tags but keep their inner text; map
  `<br>`/`<br/>` to a line break; print a warning to stderr listing which tags were stripped
  (so nothing disappears silently).
- **Content vs chrome/theme:** the markdown file is pure content. All chrome and the theme are
  **CLI parameters** — no YAML frontmatter. Theme is either a built-in name or a path to a theme JSON.
- **Dependencies allowed.** Runtime deps kept minimal: `markdown-it`, `docx`. CLI parsing uses
  Node's built-in `node:util` `parseArgs` (no dep). No `gray-matter` needed (no frontmatter).

## Folder layout

```
~/md2docx/
  README.md                 # what it is, install, usage, examples, HTML caveat
  .gitignore                # node_modules, *.docx outputs, assets/*.png (keep .gitkeep)
  js/
    package.json            # deps: markdown-it, docx; bin: md2docx -> src/index.js
    src/
      index.js              # CLI entry: parseArgs -> pipeline -> write .docx
      theme.js              # load built-in theme by name OR read theme JSON path; validate + defaults
      builders.js           # docx element builders parameterized by (theme): h1/h2/h3, body,
                            #   bullet, numbered, makeTable, cell, divider, image, codeBlock,
                            #   blockquote, eyebrow, cover, footer, buildDocument(styles/numbering/section)
      inline.js             # walk a markdown-it `inline` token's children -> TextRun[]
                            #   (text, strong/em, code_inline, link, softbreak/hardbreak, html_inline->strip)
      renderer.js           # walk markdown-it block tokens -> docx element[]; owns list/table state
    themes/
      circeus-light.json    # the current script's palette/fonts/geometry, extracted verbatim
  python/  .gitkeep         # placeholder (pure-python version later, e.g. python-docx)
  pandoc/  .gitkeep         # placeholder (pandoc + reference.docx approach later)
  tests/
    fixtures/               # escalating complexity (see below)
    run.mjs                 # node:test runner: render each fixture, assert
```

## JS pipeline (index.js)

1. Parse CLI with `node:util` `parseArgs`:
   - positional: `input.md`
   - `-o, --out <file.docx>` (default: input basename + `.docx`)
   - `--theme <name|path>` (default `circeus-light`)
   - `--title <str>`, `--eyebrow <str>`, `--subtitle <str>` (repeatable → array),
     `--logo <path>`, `--logo-width <pt>`, `--footer <str>`, `--page-numbers` (flag)
2. Read markdown file (UTF-8).
3. `md = new MarkdownIt({ html: false, linkify: true, typographer: false })`; `tokens = md.parse(src, {})`.
4. `theme = loadTheme(themeArg)`.
5. `elements = render(tokens, theme)` (renderer.js) — the procedural map from tokens to builders.
6. Build cover/chrome elements from CLI params (cover only if `--title` given; logo only if `--logo`
   given and file exists).
7. `doc = buildDocument({ theme, chrome, elements })` — styles, numbering configs, section w/ footer.
8. `Packer.toBuffer(doc)` → write to `--out`. Log warnings collected during render (stripped HTML).

## Token → builder mapping (renderer.js)

markdown-it emits a flat token stream; each `inline` token has a nested `children` array. Mapping:

- `heading_open` (tag `h1`/`h2`/`h3`; h4-h6 fall back to h3) → `h1/h2/h3()`
- `paragraph_open` + `inline` → `body()` (children via inline.js)
- `bullet_list_open` / `ordered_list_open` + `list_item` → `bullet()` / `numbered()`;
  track nesting via a level counter (numbering level 0/1); ordered lists get a fresh numbering ref.
- `table_open`/`thead`/`tbody`/`tr`/`th`/`td` → collect into `makeTable(headers, rows, widths)`;
  compute column widths by splitting CONTENT_WIDTH evenly (respect alignment attr if present).
- `hr` → `divider()`
- `fence` / `code_block` → monospace shaded paragraph (new `codeBlock()` builder)
- `blockquote_open` → new `blockquote()` builder (indented, muted, left border)
- `image` (inline) → `ImageRun` paragraph (resolve path relative to the markdown file's dir)
- `html_block` / `html_inline` → strip tags, keep text, `<br>`→break, record warning

Reused/kept from the original script (moved into builders.js, parameterized by `theme` instead of
module-level consts): `eyebrow`, `divider`, `h1/h2/h3`, `runsFromInline`→`inline.js`, `body`,
`bullet`, `numbered`, `cell`, `makeTable`, the `Document`/`styles`/`numbering`/`section`/`Footer`
assembly. `runsFromInline`'s regex is replaced by walking markdown-it inline children (handles
nested emphasis, links, and code correctly instead of a flat split).

## theme.js

`circeus-light.json` holds exactly the tokens the script hardcodes today:
`colors` (primary/secondary/muted/panel/divider/bg), `font`, `page` (width/height/margin),
`headings` (size + spacing per level), `body` (size/line), `table` (border size/color, cell padding),
`numbering` (bullet glyph, ordered format). `loadTheme(arg)`: if `arg` ends in `.json` treat as a
path and read it; else look up `themes/<arg>.json`; deep-merge over built-in defaults so partial
theme files work.

## Test setup (escalating)

Fixtures in `tests/fixtures/`, ordered simple → complex:

- `01-minimal.md` — one `#` heading + one paragraph.
- `02-lists.md` — nested unordered list + an ordered list.
- `03-inline.md` — bold, inline code, a link, mixed/nested inline.
- `04-table.md` — a GFM pipe table with column alignment.
- `05-full.md` — every supported feature: h1–h3, paragraphs, bold/code/links, nested + ordered
  lists, table, fenced code block, blockquote, `---` divider, image.
- `06-inline-html.md` — inline and block HTML (`<br>`, `<b>`, `<div>`) to exercise the
  strip-and-warn policy.
- `circeus-report.md` — end-to-end: the real report body (copy of
  `guardrails/docs/ip_protection_advanced_notion.md`) rendered with the Circeus chrome via CLI flags,
  to reproduce the original hardcoded output.

`tests/run.mjs` uses the built-in Node test runner (`node --test`). For each fixture it:
1. renders to an in-memory buffer (asserts no throw, buffer non-empty, starts with `PK` zip magic);
2. for a few fixtures, unzips `word/document.xml` (via `unzip -p`, already on the system) and asserts
   expected text/structure is present (e.g. table cell text, heading text, that stripped HTML tags
   like `<div>` do NOT appear literally while their inner text does).

## Verification (end-to-end)

1. `cd ~/md2docx/js && npm install`.
2. `node --test ../tests/run.mjs` → all fixtures render, content assertions pass.
3. Reproduce the real doc:
   `node src/index.js ../tests/fixtures/circeus-report.md -o /tmp/report.docx \
     --theme circeus-light --eyebrow "Internal engineering report" \
     --title "IP protection: multi-turn leakage detection" \
     --subtitle "Branch: feature/ip_protection_advanced" --subtitle "Period: June – July 2026" \
     --footer "Circeus — confidential" --page-numbers` (add `--logo` if a logo file is provided).
4. Open `/tmp/report.docx` and eyeball against the original script's output — headings, tables,
   bullets/numbered lists, footer, and page geometry should match.
5. Run `06-inline-html.md` and confirm a stderr warning lists the stripped tags and the output text
   is clean (no literal `<div>`).

## Notes / later passes

- `python/` and `pandoc/` are placeholders now. Python version likely `python-docx` mirroring the
  same builders; pandoc version likely `pandoc input.md -o out.docx --reference-doc=theme.docx`
  (needs pandoc installed — currently absent).
- Not building a live app; the deliverable is a CLI + tests. No changes are made inside the
  `guardrails` repo.
