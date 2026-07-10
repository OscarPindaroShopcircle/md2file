import { runsFromInline } from "./inline.js";
import {
  heading,
  body,
  bullet,
  numbered,
  divider,
  codeBlock,
  makeTable,
  bulletConfig,
  orderedConfig,
} from "./builders.js";
import { pt } from "./util.js";
import { AlignmentType } from "docx";

function attr(token, name) {
  const a = (token.attrs || []).find((x) => x[0] === name);
  return a ? a[1] : null;
}

function alignFromToken(token) {
  const s = attr(token, "style") || "";
  const m = s.match(/text-align:\s*(left|right|center)/);
  return m ? m[1] : "left";
}

function isSoleImage(inlineToken) {
  const kids = (inlineToken.children || []).filter((c) => c.type !== "softbreak");
  return kids.length === 1 && kids[0].type === "image";
}

// Base run-style used inside a blockquote (muted text).
function quoteBase(theme) {
  return { color: theme.colors.muted };
}

/**
 * Turn a flat markdown-it token stream into an array of docx block elements.
 * Returns { elements, numbering, warnings }.
 */
export function render(tokens, theme, opts = {}) {
  const ctx = { theme, docDir: opts.docDir || process.cwd(), warnings: new Set() };
  const elements = [];
  const numbering = [bulletConfig(theme)];
  const listStack = []; // [{ type: 'bullet'|'ordered', ref? }]
  let orderedCount = 0;
  let quoteDepth = 0;

  const listLevel = () => Math.min(1, Math.max(0, listStack.length - 1));

  for (let i = 0; i < tokens.length; i++) {
    const tk = tokens[i];
    switch (tk.type) {
      case "heading_open": {
        const level = Math.min(3, parseInt(tk.tag.slice(1), 10) || 3);
        const h = theme.headings[`h${level}`];
        const inlineTok = tokens[i + 1];
        const runs = runsFromInline(inlineTok, {
          ...ctx,
          base: { color: h.color, size: pt(h.size), bold: h.bold !== false, font: theme.font },
        });
        elements.push(heading(level, runs, theme));
        i += 2; // inline + heading_close
        break;
      }

      case "paragraph_open": {
        const inlineTok = tokens[i + 1];
        const base = quoteDepth > 0 ? quoteBase(theme) : undefined;
        const runs = runsFromInline(inlineTok, { ...ctx, base });
        if (listStack.length) {
          const top = listStack[listStack.length - 1];
          if (top.type === "ordered") elements.push(numbered(runs, theme, top.ref, listLevel()));
          else elements.push(bullet(runs, theme, listLevel()));
        } else {
          elements.push(
            body(runs, theme, {
              quote: quoteDepth > 0,
              alignment: isSoleImage(inlineTok) ? AlignmentType.CENTER : undefined,
            }),
          );
        }
        i += 2; // inline + paragraph_close
        break;
      }

      case "bullet_list_open":
        listStack.push({ type: "bullet" });
        break;
      case "bullet_list_close":
        listStack.pop();
        break;
      case "ordered_list_open": {
        orderedCount += 1;
        const ref = `ordered-${orderedCount}`;
        numbering.push(orderedConfig(ref));
        listStack.push({ type: "ordered", ref });
        break;
      }
      case "ordered_list_close":
        listStack.pop();
        break;

      case "blockquote_open":
        quoteDepth += 1;
        break;
      case "blockquote_close":
        quoteDepth -= 1;
        break;

      case "hr":
        elements.push(divider(theme));
        break;

      case "fence":
      case "code_block":
        elements.push(codeBlock(tk.content, theme));
        break;

      case "table_open": {
        const res = parseTable(tokens, i, ctx, theme);
        elements.push(res.table);
        i = res.end; // table_close
        break;
      }

      case "html_block": {
        const runs = stripHtmlBlock(tk.content, ctx);
        if (runs.length) elements.push(body(runs, theme));
        break;
      }

      default:
        break;
    }
  }

  return { elements, numbering, warnings: ctx.warnings };
}

function parseTable(tokens, start, ctx, theme) {
  const headers = [];
  const rows = [];
  const aligns = [];
  let inHead = false;
  let curRow = null;
  let i = start + 1;

  for (; i < tokens.length; i++) {
    const t = tokens[i];
    if (t.type === "table_close") break;
    switch (t.type) {
      case "thead_open":
        inHead = true;
        break;
      case "thead_close":
        inHead = false;
        break;
      case "tr_open":
        curRow = [];
        break;
      case "tr_close":
        if (inHead) headers.push(...curRow);
        else rows.push(curRow);
        curRow = null;
        break;
      case "th_open":
      case "td_open": {
        const align = alignFromToken(t);
        if (inHead) aligns.push(align);
        const inlineTok = tokens[i + 1];
        const base = inHead ? { bold: true, color: theme.table.headerColor } : undefined;
        const runs = runsFromInline(inlineTok, { ...ctx, base });
        curRow.push(runs);
        i += 1; // skip the inline token
        break;
      }
      default:
        break;
    }
  }

  return { table: makeTable(headers, rows, theme, aligns), end: i };
}

function stripHtmlBlock(html, ctx) {
  // record the tags we drop
  for (const m of html.matchAll(/<\/?\s*([a-zA-Z][a-zA-Z0-9]*)/g)) {
    ctx.warnings.add(m[1].toLowerCase());
  }
  const text = html
    .replace(/<\s*br\s*\/?\s*>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/\n{2,}/g, "\n")
    .trim();
  if (!text) return [];
  const runs = runsFromInline({ children: [{ type: "text", content: text }] }, ctx);
  return runs;
}
