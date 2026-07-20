#!/usr/bin/env node
import { parseArgs } from "node:util";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import MarkdownIt from "markdown-it";
import { Packer } from "docx";
import { loadTheme } from "./theme.js";
import { render } from "./renderer.js";
import { cover as buildCover, buildDocument } from "./builders.js";

/**
 * Core conversion. `src` is markdown text; returns { buffer, warnings }.
 * `options`: { theme, title, eyebrow, subtitles, logo, logoWidth, footer,
 *              pageNumbers, docDir }
 */
export async function convert(src, options = {}) {
  const theme = loadTheme(options.theme || "circeus-light");
  const md = new MarkdownIt({ html: false, linkify: true, typographer: false });
  const tokens = md.parse(src, {});

  const { elements, numbering, warnings } = render(tokens, theme, {
    docDir: options.docDir || process.cwd(),
  });

  let coverEls = [];
  if (options.title) {
    coverEls = buildCover(
      {
        title: options.title,
        eyebrow: options.eyebrow,
        subtitles: options.subtitles || [],
        logo: options.logo && fs.existsSync(options.logo) ? options.logo : null,
        logoWidth: options.logoWidth,
      },
      theme,
    );
  }

  const doc = buildDocument({
    theme,
    cover: coverEls,
    elements,
    numbering,
    footerText: options.footer,
    pageNumbers: options.pageNumbers,
  });

  const buffer = await Packer.toBuffer(doc);
  return { buffer, warnings };
}

function usage() {
  return `md2docx — markdown -> styled .docx

Usage:
  md2docx <input.md> [options]

Options:
  -o, --out <file>       output .docx (default: input basename + .docx)
      --theme <name|path> built-in theme name or path to a theme .json (default: circeus-light)
      --title <str>       cover title (a cover page is emitted only if given)
      --eyebrow <str>     small label above the cover title
      --subtitle <str>    cover subtitle (repeatable)
      --logo <path>       cover logo image (used only if the file exists)
      --logo-width <px>   logo width in pixels (default: 160)
      --footer <str>      footer text (left)
      --page-numbers      show "Page N" at footer right
  -h, --help             show this help
`;
}

async function main(argv) {
  let parsed;
  try {
    parsed = parseArgs({
      args: argv,
      allowPositionals: true,
      options: {
        out: { type: "string", short: "o" },
        theme: { type: "string", default: "circeus-light" },
        title: { type: "string" },
        eyebrow: { type: "string" },
        subtitle: { type: "string", multiple: true },
        logo: { type: "string" },
        "logo-width": { type: "string" },
        footer: { type: "string" },
        "page-numbers": { type: "boolean", default: false },
        help: { type: "boolean", short: "h", default: false },
      },
    });
  } catch (err) {
    process.stderr.write(`error: ${err.message}\n\n${usage()}`);
    process.exit(2);
  }

  const { values, positionals } = parsed;
  if (values.help || positionals.length === 0) {
    process.stdout.write(usage());
    process.exit(values.help ? 0 : 1);
  }

  const input = positionals[0];
  if (!fs.existsSync(input)) {
    process.stderr.write(`error: input file not found: ${input}\n`);
    process.exit(1);
  }

  const src = fs.readFileSync(input, "utf8");
  const out = values.out || `${path.basename(input, path.extname(input))}.docx`;

  if (values.logo && !fs.existsSync(values.logo)) {
    process.stderr.write(`warning: logo not found, skipping: ${values.logo}\n`);
  }

  const { buffer, warnings } = await convert(src, {
    theme: values.theme,
    title: values.title,
    eyebrow: values.eyebrow,
    subtitles: values.subtitle,
    logo: values.logo,
    logoWidth: values["logo-width"] ? parseInt(values["logo-width"], 10) : undefined,
    footer: values.footer,
    pageNumbers: values["page-numbers"],
    docDir: path.dirname(path.resolve(input)),
  });

  fs.writeFileSync(out, buffer);
  process.stdout.write(`wrote ${out} (${buffer.length} bytes)\n`);

  if (warnings.size) {
    const stripped = [...warnings].filter((w) => !w.startsWith("image-not-found:"));
    const images = [...warnings].filter((w) => w.startsWith("image-not-found:"));
    if (stripped.length) {
      process.stderr.write(`warning: stripped HTML tags (kept inner text): ${stripped.map((t) => `<${t}>`).join(", ")}\n`);
    }
    for (const im of images) {
      process.stderr.write(`warning: ${im.replace("image-not-found:", "image not found: ")}\n`);
    }
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] || "").href) {
  main(process.argv.slice(2));
}
