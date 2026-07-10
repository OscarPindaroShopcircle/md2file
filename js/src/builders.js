import fs from "node:fs";
import {
  Document,
  Paragraph,
  TextRun,
  ExternalHyperlink,
  ImageRun,
  Table,
  TableRow,
  TableCell,
  WidthType,
  BorderStyle,
  AlignmentType,
  LevelFormat,
  Footer,
  PageNumber,
  PageBreak,
  Tab,
  TabStopType,
} from "docx";
import { pt, line } from "./util.js";

const contentWidth = (theme) => theme.page.width - theme.page.margin.left - theme.page.margin.right;

// --- block builders -----------------------------------------------------

export function heading(level, runs, theme) {
  const h = theme.headings[`h${level}`];
  return new Paragraph({
    children: runs,
    keepNext: true,
    spacing: { before: pt(h.before), after: pt(h.after), line: line(theme.body.line), lineRule: "auto" },
    border: h.rule
      ? { bottom: { style: BorderStyle.SINGLE, size: h.ruleSize, color: theme.colors.divider, space: 4 } }
      : undefined,
  });
}

export function body(runs, theme, opts = {}) {
  const para = {
    children: runs,
    spacing: { after: pt(theme.body.after), line: line(theme.body.line), lineRule: "auto" },
    alignment: opts.alignment,
  };
  if (opts.quote) {
    para.indent = { left: 360 };
    para.border = { left: { style: BorderStyle.SINGLE, size: 18, color: theme.colors.secondary, space: 12 } };
  }
  return new Paragraph(para);
}

export function bullet(runs, theme, level = 0) {
  return new Paragraph({
    children: runs,
    numbering: { reference: "bullet-list", level },
    spacing: { after: pt(theme.body.listAfter), line: line(theme.body.line), lineRule: "auto" },
  });
}

export function numbered(runs, theme, reference, level = 0) {
  return new Paragraph({
    children: runs,
    numbering: { reference, level },
    spacing: { after: pt(theme.body.listAfter), line: line(theme.body.line), lineRule: "auto" },
  });
}

export function divider(theme) {
  return new Paragraph({
    children: [],
    spacing: { before: pt(6), after: pt(6) },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: theme.colors.divider, space: 1 } },
  });
}

export function codeBlock(code, theme) {
  const lines = code.replace(/\n+$/, "").split("\n");
  const children = [];
  lines.forEach((ln, i) => {
    if (i > 0) children.push(new TextRun({ text: "", break: 1 }));
    children.push(
      new TextRun({
        text: ln.length ? ln : " ",
        font: theme.monoFont,
        size: pt(theme.code.size),
        color: theme.colors.codeText,
      }),
    );
  });
  const b = { style: BorderStyle.SINGLE, size: 2, color: theme.colors.divider, space: 6 };
  return new Paragraph({
    children,
    shading: { fill: theme.colors.codeBg },
    spacing: { before: pt(6), after: pt(6), line: line(1.2), lineRule: "auto" },
    border: { top: b, bottom: b, left: b, right: b },
  });
}

// --- tables -------------------------------------------------------------

const alignMap = {
  center: AlignmentType.CENTER,
  right: AlignmentType.RIGHT,
  left: AlignmentType.LEFT,
};

export function cell(runs, theme, opts = {}) {
  return new TableCell({
    width: { size: opts.width, type: WidthType.DXA },
    shading: opts.header ? { fill: theme.table.headerFill } : undefined,
    margins: {
      top: theme.table.cellPad,
      bottom: theme.table.cellPad,
      left: theme.table.cellPad,
      right: theme.table.cellPad,
    },
    children: [
      new Paragraph({
        children: runs,
        alignment: alignMap[opts.align] || AlignmentType.LEFT,
        spacing: { after: 0, line: line(theme.body.line), lineRule: "auto" },
      }),
    ],
  });
}

export function makeTable(headers, rows, theme, aligns = []) {
  const ncol = headers.length || (rows[0] ? rows[0].length : 1);
  const colW = Math.floor(contentWidth(theme) / ncol);
  const b = { style: BorderStyle.SINGLE, size: theme.table.borderSize, color: theme.table.borderColor };
  const borders = { top: b, bottom: b, left: b, right: b, insideHorizontal: b, insideVertical: b };

  const tableRows = [];
  if (headers.length) {
    tableRows.push(
      new TableRow({
        tableHeader: true,
        children: headers.map((r, i) => cell(r, theme, { header: true, width: colW, align: aligns[i] })),
      }),
    );
  }
  for (const row of rows) {
    tableRows.push(
      new TableRow({ children: row.map((r, i) => cell(r, theme, { width: colW, align: aligns[i] })) }),
    );
  }

  return new Table({
    width: { size: contentWidth(theme), type: WidthType.DXA },
    columnWidths: Array(ncol).fill(colW),
    borders,
    rows: tableRows,
  });
}

// --- chrome (cover / footer) --------------------------------------------

export function eyebrow(text, theme) {
  return new Paragraph({
    children: [
      new TextRun({
        text: text.toUpperCase(),
        color: theme.colors.secondary,
        bold: true,
        size: pt(theme.cover.eyebrowSize),
        font: theme.font,
        characterSpacing: 40,
      }),
    ],
    spacing: { after: pt(6) },
  });
}

function loadCoverImage(logoPath, widthPx, theme) {
  try {
    const data = fs.readFileSync(logoPath);
    const ext = logoPath.split(".").pop().toLowerCase();
    const type = ext === "jpg" ? "jpeg" : ext;
    const w = widthPx || 160;
    // preserve a sane default aspect if we can't read it
    let h = Math.round(w * 0.5);
    if (data[0] === 0x89 && data[1] === 0x50) {
      const iw = data.readUInt32BE(16);
      const ih = data.readUInt32BE(20);
      if (iw > 0) h = Math.round((ih / iw) * w);
    }
    return new ImageRun({ data, type, transformation: { width: w, height: h } });
  } catch {
    return null;
  }
}

export function cover(chrome, theme) {
  const els = [];
  const logo = chrome.logo ? loadCoverImage(chrome.logo, chrome.logoWidth, theme) : null;
  if (logo) els.push(new Paragraph({ children: [logo], spacing: { after: pt(18) } }));

  els.push(new Paragraph({ children: [], spacing: { before: pt(theme.cover.topSpace) } }));

  if (chrome.eyebrow) els.push(eyebrow(chrome.eyebrow, theme));

  els.push(
    new Paragraph({
      children: [
        new TextRun({
          text: chrome.title,
          bold: true,
          color: theme.colors.primary,
          size: pt(theme.cover.titleSize),
          font: theme.font,
        }),
      ],
      spacing: { after: pt(8) },
    }),
  );

  for (const sub of chrome.subtitles || []) {
    els.push(
      new Paragraph({
        children: [
          new TextRun({ text: sub, color: theme.colors.muted, size: pt(theme.cover.subtitleSize), font: theme.font }),
        ],
        spacing: { after: pt(4) },
      }),
    );
  }

  els.push(divider(theme));
  els.push(new Paragraph({ children: [new PageBreak()] }));
  return els;
}

function footer(theme, footerText, pageNumbers) {
  const runs = [];
  if (footerText) {
    runs.push(new TextRun({ text: footerText, color: theme.colors.muted, size: pt(theme.footer.size), font: theme.font }));
  }
  if (pageNumbers) {
    runs.push(
      new TextRun({
        children: [new Tab(), "Page ", PageNumber.CURRENT],
        color: theme.colors.muted,
        size: pt(theme.footer.size),
        font: theme.font,
      }),
    );
  }
  return new Footer({
    children: [
      new Paragraph({
        tabStops: [{ type: TabStopType.RIGHT, position: contentWidth(theme) }],
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: theme.colors.divider, space: 6 } },
        children: runs,
      }),
    ],
  });
}

// --- numbering configs --------------------------------------------------

export function bulletConfig(theme) {
  return {
    reference: "bullet-list",
    levels: [
      {
        level: 0,
        format: LevelFormat.BULLET,
        text: theme.numbering.bullet,
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 420, hanging: 260 } } },
      },
      {
        level: 1,
        format: LevelFormat.BULLET,
        text: theme.numbering.subBullet,
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 840, hanging: 260 } } },
      },
    ],
  };
}

export function orderedConfig(reference) {
  return {
    reference,
    levels: [
      {
        level: 0,
        format: LevelFormat.DECIMAL,
        text: "%1.",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 420, hanging: 260 } } },
      },
      {
        level: 1,
        format: LevelFormat.LOWER_LETTER,
        text: "%2.",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 840, hanging: 260 } } },
      },
    ],
  };
}

// --- document assembly --------------------------------------------------

export function buildDocument({ theme, cover = [], elements, numbering = [], footerText, pageNumbers }) {
  const hasFooter = Boolean(footerText) || Boolean(pageNumbers);
  return new Document({
    creator: "md2docx",
    styles: {
      default: {
        document: {
          run: { font: theme.font, size: pt(theme.body.size), color: theme.colors.text },
        },
      },
    },
    numbering: { config: numbering },
    sections: [
      {
        properties: {
          page: {
            size: { width: theme.page.width, height: theme.page.height },
            margin: theme.page.margin,
          },
        },
        footers: hasFooter ? { default: footer(theme, footerText, pageNumbers) } : undefined,
        children: [...cover, ...elements],
      },
    ],
  });
}
