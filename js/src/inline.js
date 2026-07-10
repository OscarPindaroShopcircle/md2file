import fs from "node:fs";
import path from "node:path";
import { TextRun, ExternalHyperlink, ImageRun } from "docx";

// Walk a markdown-it `inline` token's `children` and produce an array of
// run-level docx elements (TextRun | ExternalHyperlink | ImageRun).
//
// ctx = { theme, docDir, warnings:Set, base } where `base` supplies the default
// run props (color/font/size and optional bold/italics) — this is how headings
// and table-header cells restyle their text without special-casing here.

function attr(token, name) {
  const a = (token.attrs || []).find((x) => x[0] === name);
  return a ? a[1] : null;
}

function baseOf(ctx) {
  const t = ctx.theme;
  return {
    color: t.colors.text,
    font: t.font,
    size: Math.round(t.body.size * 2),
    bold: false,
    italics: false,
    ...(ctx.base || {}),
  };
}

export function runsFromInline(token, ctx) {
  const base = baseOf(ctx);
  const children = token.children || [];
  const out = [];

  let bold = base.bold ? 1 : 0;
  let italic = base.italics ? 1 : 0;
  let link = null; // { href, runs: [] }

  const emit = (run) => (link ? link.runs.push(run) : out.push(run));

  const mkText = (text, extra = {}) =>
    new TextRun({
      text,
      bold: bold > 0 || undefined,
      italics: italic > 0 || undefined,
      font: base.font,
      size: base.size,
      color: link ? ctx.theme.colors.secondary : base.color,
      underline: link ? {} : undefined,
      ...extra,
    });

  for (const t of children) {
    switch (t.type) {
      case "text":
        // With markdown-it { html:false }, raw HTML arrives as literal text.
        // Strip tags but keep inner text; <br> -> line break; warn on the rest.
        emitText(t.content, emit, mkText, ctx);
        break;
      case "strong_open":
        bold++;
        break;
      case "strong_close":
        bold--;
        break;
      case "em_open":
        italic++;
        break;
      case "em_close":
        italic--;
        break;
      case "s_open": // ~~strikethrough~~
      case "s_close":
        break;
      case "code_inline":
        emit(
          new TextRun({
            text: t.content,
            font: ctx.theme.monoFont,
            size: base.size,
            color: link ? ctx.theme.colors.secondary : ctx.theme.colors.codeText,
            shading: { fill: ctx.theme.colors.codeBg },
            bold: bold > 0 || undefined,
            italics: italic > 0 || undefined,
            underline: link ? {} : undefined,
          }),
        );
        break;
      case "softbreak":
        emit(mkText(" "));
        break;
      case "hardbreak":
        emit(new TextRun({ text: "", break: 1, font: base.font, size: base.size }));
        break;
      case "link_open":
        link = { href: attr(t, "href") || "", runs: [] };
        break;
      case "link_close":
        if (link) {
          const runs = link.runs.length ? link.runs : [mkTextForLink(link.href, base, ctx)];
          out.push(new ExternalHyperlink({ link: link.href, children: runs }));
          link = null;
        }
        break;
      case "image": {
        const run = imageRun(t, ctx);
        if (run) emit(run);
        break;
      }
      case "html_inline":
        handleInlineHtml(t.content, emit, mkText, ctx);
        break;
      default:
        if (t.content) emit(mkText(t.content));
    }
  }
  return out;
}

// Emit a text token, stripping any literal HTML tags it contains (the
// strip-and-warn policy). `<br>`/`<br/>` becomes a line break; every other tag
// name is recorded in ctx.warnings and dropped, keeping the surrounding text.
const TAG_RE = /<\/?\s*([a-zA-Z][a-zA-Z0-9]*)(?:\s[^>]*?)?\/?\s*>/g;
function emitText(text, emit, mkText, ctx) {
  if (text.indexOf("<") === -1) {
    emit(mkText(text));
    return;
  }
  let last = 0;
  let m;
  TAG_RE.lastIndex = 0;
  while ((m = TAG_RE.exec(text))) {
    if (m.index > last) emit(mkText(text.slice(last, m.index)));
    const tag = m[1].toLowerCase();
    if (tag === "br") emit(new TextRun({ text: "", break: 1 }));
    else ctx.warnings.add(tag);
    last = TAG_RE.lastIndex;
  }
  if (last < text.length) emit(mkText(text.slice(last)));
}

function mkTextForLink(text, base, ctx) {
  return new TextRun({
    text,
    font: base.font,
    size: base.size,
    color: ctx.theme.colors.secondary,
    underline: {},
  });
}

function handleInlineHtml(content, emit, mkText, ctx) {
  if (/^<\s*br\s*\/?\s*>$/i.test(content)) {
    emit(new TextRun({ text: "", break: 1 }));
    return;
  }
  const m = content.match(/^<\/?\s*([a-zA-Z][a-zA-Z0-9]*)/);
  if (m) ctx.warnings.add(m[1].toLowerCase());
  // Otherwise strip the tag; any inner text arrives as separate `text` tokens.
}

// --- images -------------------------------------------------------------

function pngSize(buf) {
  if (buf.length > 24 && buf[0] === 0x89 && buf[1] === 0x50 && buf[2] === 0x4e && buf[3] === 0x47) {
    return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
  }
  return null;
}

function imageRun(token, ctx) {
  const src = attr(token, "src") || "";
  const alt = token.content || src;
  try {
    const abs = path.isAbsolute(src) ? src : path.resolve(ctx.docDir || process.cwd(), src);
    const data = fs.readFileSync(abs);
    const ext = path.extname(abs).slice(1).toLowerCase();
    const type = ext === "jpg" ? "jpeg" : ext || "png";

    const max = ctx.theme.image.maxWidthPx;
    let width = max;
    let height = Math.round(max * 0.66);
    const dim = pngSize(data);
    if (dim && dim.w > 0) {
      const scale = Math.min(1, max / dim.w);
      width = Math.round(dim.w * scale);
      height = Math.round(dim.h * scale);
    }
    return new ImageRun({ data, type, transformation: { width, height } });
  } catch {
    ctx.warnings.add(`image-not-found:${src}`);
    return new TextRun({
      text: `[image: ${alt}]`,
      italics: true,
      color: ctx.theme.colors.muted,
      font: ctx.theme.font,
      size: Math.round(ctx.theme.body.size * 2),
    });
  }
}
