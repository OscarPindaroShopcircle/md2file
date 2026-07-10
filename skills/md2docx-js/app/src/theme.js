import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { deepMerge } from "./util.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const THEMES_DIR = path.resolve(__dirname, "../themes");

// Built-in defaults. Any theme file is deep-merged over this, so partial theme
// files only need to specify the tokens they want to override.
export const DEFAULTS = {
  font: "Calibri",
  monoFont: "Consolas",
  colors: {
    text: "1A202C",
    primary: "1A365D",
    secondary: "2C7A7B",
    muted: "718096",
    panel: "F7FAFC",
    divider: "CBD5E0",
    bg: "FFFFFF",
    codeText: "2D3748",
    codeBg: "F1F5F9",
  },
  page: {
    width: 12240, // Letter, twips
    height: 15840,
    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
  },
  body: { size: 11, line: 1.3, after: 8, listAfter: 3 },
  headings: {
    h1: { size: 22, color: "1A365D", before: 18, after: 8, rule: true, ruleSize: 6 },
    h2: { size: 16, color: "1A365D", before: 14, after: 6, rule: false, ruleSize: 4 },
    h3: { size: 13, color: "2C7A7B", before: 10, after: 4, rule: false, ruleSize: 4 },
  },
  code: { size: 9.5 },
  table: {
    borderSize: 4,
    borderColor: "CBD5E0",
    headerFill: "1A365D",
    headerColor: "FFFFFF",
    cellPad: 90,
  },
  numbering: { bullet: "•", subBullet: "◦" },
  cover: { topSpace: 60, titleSize: 34, subtitleSize: 13, eyebrowSize: 10.5 },
  footer: { size: 9 },
  image: { maxWidthPx: 480 },
};

/**
 * Resolve a theme argument into a full theme object.
 * - if `arg` ends in `.json`  -> read that file as a path
 * - otherwise                 -> read `themes/<arg>.json`
 * The result is deep-merged over DEFAULTS.
 */
export function loadTheme(arg = "circeus-light") {
  let raw = {};
  try {
    const file = arg.endsWith(".json") ? arg : path.join(THEMES_DIR, `${arg}.json`);
    raw = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (err) {
    if (arg.endsWith(".json")) {
      throw new Error(`Could not read theme file "${arg}": ${err.message}`);
    }
    throw new Error(`Unknown theme "${arg}" (no themes/${arg}.json). ${err.message}`);
  }
  return deepMerge(DEFAULTS, raw);
}
