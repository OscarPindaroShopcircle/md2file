# Examples

Ready-to-run inputs so anyone can try md2docx. Both examples use the **same**
markdown content — the only difference is the styling passed on the command line,
which is the whole point of the tool (content is pure; theme and chrome are flags).

```
examples/
  01-plain/
    report.md                     # Circeus overview, no styling
  02-branded/
    report.md                     # same content
    circeus-brand-light.json      # theme derived from the circeus-brand skill (light tokens)
    assets/
      circeus-logo-dark-charcoal.png   # official logo (for light backgrounds)
      circeus-logo-light-gray.png      # official logo (watermark/subtle use)
```

## 1. Plain — default theme, no chrome

```bash
node js/src/index.js examples/01-plain/report.md \
  -o output/js/examples/01-plain.docx
```

## 2. Branded — Circeus theme + logo + cover chrome

Near-monochrome look from the `circeus-brand` skill: Geist font, off-black/off-white,
medium-weight (non-bold) headings, thin rule lines, and the official logo on the cover.

```bash
node js/src/index.js examples/02-branded/report.md \
  -o output/js/examples/02-branded.docx \
  --theme examples/02-branded/circeus-brand-light.json \
  --logo examples/02-branded/assets/circeus-logo-dark-charcoal.png \
  --logo-width 150 \
  --eyebrow "Operating overview" \
  --title "Circeus operating overview" \
  --subtitle "For founders considering a partnership" \
  --footer "Circeus — circeus.com" \
  --page-numbers
```

Or just run `./examples/convert-examples.sh` from the repo root to generate both
into `output/js/examples/`.

## Notes

- **Logos are official brand assets** — embedded as-is, never recolored or
  regenerated (per the circeus-brand skill).
- **Geist** may not be installed in Word/LibreOffice; if absent it falls back to a
  neutral sans. The color/size scale still applies.
- The branded theme uses the **light** tokens (default for printed docs). Swap in a
  dark-token theme for a website-matching look.
