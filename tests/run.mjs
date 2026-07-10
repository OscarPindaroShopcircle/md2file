import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { convert } from "../js/src/index.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIX = path.join(__dirname, "fixtures");

const read = (name) => fs.readFileSync(path.join(FIX, name), "utf8");

// Render a fixture to a buffer (no file written unless we unzip it).
async function renderFixture(name, options = {}) {
  const src = read(name);
  return convert(src, { docDir: FIX, ...options });
}

// Unzip word/document.xml from a .docx buffer using the system `unzip`.
function documentXml(buffer) {
  const tmp = path.join(os.tmpdir(), `md2docx-${name(buffer)}.docx`);
  fs.writeFileSync(tmp, buffer);
  try {
    return execFileSync("unzip", ["-p", tmp, "word/document.xml"], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  } finally {
    fs.rmSync(tmp, { force: true });
  }
}
let counter = 0;
function name() {
  counter += 1;
  return `${process.pid}-${counter}`;
}

function assertValidDocx(buffer) {
  assert.ok(buffer.length > 0, "buffer should be non-empty");
  assert.equal(buffer[0], 0x50, "should start with 'P' (zip magic)");
  assert.equal(buffer[1], 0x4b, "should start with 'K' (zip magic)");
}

const FIXTURES = [
  "01-minimal.md",
  "02-lists.md",
  "03-inline.md",
  "04-table.md",
  "05-full.md",
  "06-inline-html.md",
  "circeus-report.md",
];

for (const fx of FIXTURES) {
  test(`renders ${fx} to a valid docx`, async () => {
    const { buffer } = await renderFixture(fx);
    assertValidDocx(buffer);
  });
}

test("01-minimal: heading and paragraph text present", async () => {
  const { buffer } = await renderFixture("01-minimal.md");
  const xml = documentXml(buffer);
  assert.match(xml, /Hello World/);
  assert.match(xml, /single paragraph of body text/);
});

test("02-lists: list items present and numbering referenced", async () => {
  const { buffer } = await renderFixture("02-lists.md");
  const xml = documentXml(buffer);
  assert.match(xml, /Nested item A/);
  assert.match(xml, /Step three/);
  assert.match(xml, /<w:numPr>/, "should contain numbering properties");
});

test("03-inline: bold, code, and link render", async () => {
  const { buffer } = await renderFixture("03-inline.md");
  const xml = documentXml(buffer);
  assert.match(xml, /bold text/);
  assert.match(xml, /inline code/);
  assert.match(xml, /link to example/);
  assert.match(xml, /<w:hyperlink/, "link should be a hyperlink");
});

test("04-table: cells render inside a table", async () => {
  const { buffer } = await renderFixture("04-table.md");
  const xml = documentXml(buffer);
  assert.match(xml, /<w:tbl>/, "should contain a table");
  assert.match(xml, /Feature/);
  assert.match(xml, /In progress/);
});

test("05-full: exercises code, blockquote, table, and image", async () => {
  const { buffer, warnings } = await renderFixture("05-full.md");
  const xml = documentXml(buffer);
  assert.match(xml, /<w:tbl>/);
  assert.match(xml, /function greet/);
  assert.match(xml, /This is a blockquote/);
  assert.match(xml, /<w:drawing>/, "image should embed a drawing");
  assert.ok(!warnings.has("image-not-found:assets/sample.png"), "sample image should be found");
});

test("06-inline-html: tags stripped, inner text kept, warnings recorded", async () => {
  const { buffer, warnings } = await renderFixture("06-inline-html.md");
  const xml = documentXml(buffer);
  // inner text survives
  assert.match(xml, /bold via a b tag/);
  assert.match(xml, /block-level div/);
  // literal tags do NOT appear as text
  assert.ok(!/&lt;div/.test(xml), "literal <div> should not appear as text");
  assert.ok(!/&lt;b&gt;/.test(xml), "literal <b> should not appear as text");
  // warnings list the stripped tags
  assert.ok(warnings.has("div"), "should warn about stripped <div>");
  assert.ok(warnings.has("b"), "should warn about stripped <b>");
});

test("circeus-report: cover chrome + footer via options", async () => {
  const { buffer } = await renderFixture("circeus-report.md", {
    eyebrow: "Internal engineering report",
    title: "IP protection: multi-turn leakage detection",
    subtitles: ["Branch: feature/ip_protection_advanced", "Period: June – July 2026"],
    footer: "Circeus — confidential",
    pageNumbers: true,
  });
  const xml = documentXml(buffer);
  assert.match(xml, /IP protection: multi-turn leakage detection/, "cover title present");
  assert.match(xml, /INTERNAL ENGINEERING REPORT/, "eyebrow uppercased");
  assert.match(xml, /Precision/, "table content present");
});
