"""Fuzzy / adversarial tests.

Two complementary strategies:

1. **High-volume property fuzzing** (:func:`_Generator`) — build large, deeply
   nested random documents where every visible token is a unique sentinel. The
   generator records exactly which sentinels must survive as visible text; after
   conversion we assert all of them appear, the file is a valid docx, and no
   spurious warnings were raised. Seeded RNG keeps every failure reproducible and
   prints the offending markdown.

2. **Curated hard cases** — hand-written inputs that target the nasty corners a
   markdown->docx converter tends to get wrong: XML metacharacters, HTML inside
   code (must be preserved) vs. HTML in prose (must be stripped), entity
   decoding, autolinks, escapes, setext headings, deep/mixed list nesting,
   blockquotes containing lists and code, formatted table cells, hard breaks, and
   reference links.

The invariants are deliberately conservative (presence of text, no crash, valid
file) so a failure means a real defect, never a flaky expectation.
"""

from __future__ import annotations

import random

import pytest

from md2docx.config_models import RunConfig
from md2docx.core import convert

# A nasty pool: multiple scripts, emoji, math, and ampersands (XML escaping bait).
_WORDS = [
    "alpha", "café", "naïve", "résumé", "Ω", "Δ", "日本語", "你好世界",
    "Привет", "мир", "مرحبا", "𝕏", "🎯", "🚀emoji", "Ω≈ç", "AT&T", "R&D",
    "q&z", "Straße", "Åström", "naïveté",
]


# --------------------------------------------------------------------------
# 1. property fuzzing
# --------------------------------------------------------------------------
class _Generator:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self._c = 0
        self.expected: set[str] = set()

    def _tok(self) -> str:
        self._c += 1
        return f"{self.rng.choice(_WORDS)}{self._c}"

    def _keep(self, tok: str) -> str:
        self.expected.add(tok)
        return tok

    def _inline(self, n: int | None = None) -> str:
        n = n or self.rng.randint(2, 6)
        out: list[str] = []
        for _ in range(n):
            style = self.rng.choice(
                ["plain", "plain", "bold", "italic", "bolditalic", "code", "link", "nested"]
            )
            if style == "plain":
                out.append(self._keep(self._tok()))
            elif style == "bold":
                out.append(f"**{self._keep(self._tok())}**")
            elif style == "italic":
                out.append(f"*{self._keep(self._tok())}*")
            elif style == "bolditalic":
                out.append(f"***{self._keep(self._tok())}***")
            elif style == "code":
                out.append(f"`{self._keep(self._tok())}`")
            elif style == "link":
                out.append(f"[{self._keep(self._tok())}](https://e.com/{self._tok()})")
            else:  # nested emphasis + code
                a, b, c = self._keep(self._tok()), self._keep(self._tok()), self._keep(self._tok())
                out.append(f"**{a} `{c}` *{b}***")
        return " ".join(out)

    def _heading(self) -> str:
        return "#" * self.rng.randint(1, 6) + " " + self._inline(self.rng.randint(1, 4))

    def _code(self) -> str:
        lines = [f"{self._keep(self._tok())} {self._keep(self._tok())}" for _ in range(self.rng.randint(1, 4))]
        lang = self.rng.choice(["", "py", "js", "text"])
        return "```" + lang + "\n" + "\n".join(lines) + "\n```"

    def _list(self, ordered: bool, depth: int, indent: str = "") -> str:
        lines: list[str] = []
        for i in range(self.rng.randint(2, 4)):
            marker = f"{i + 1}. " if ordered else "- "
            lines.append(indent + marker + self._inline(self.rng.randint(1, 3)))
            if depth > 0 and self.rng.random() < 0.55:
                lines.append(self._list(self.rng.random() < 0.5, depth - 1, indent + " " * len(marker)))
        return "\n".join(lines)

    def _quote(self, depth: int) -> str:
        if self.rng.random() < 0.5:
            block = self._inline()
        else:
            block = self._list(self.rng.random() < 0.5, min(2, depth))
        return "\n".join(("> " + ln if ln else ">") for ln in block.split("\n"))

    def _table(self) -> str:
        cols = self.rng.randint(2, 4)
        header = [self._keep(self._tok()) for _ in range(cols)]
        aligns = [self.rng.choice([":--", "--:", ":-:", "---"]) for _ in range(cols)]
        rows = []
        for _ in range(self.rng.randint(1, 4)):
            cells = []
            for _ in range(cols):
                if self.rng.random() < 0.15:
                    cells.append(" ")  # empty cell
                    continue
                t = self._keep(self._tok())
                cells.append(self.rng.choice([t, f"**{t}**", f"`{t}`"]))
            rows.append(cells)
        md = "| " + " | ".join(header) + " |\n"
        md += "| " + " | ".join(aligns) + " |\n"
        for r in rows:
            md += "| " + " | ".join(r) + " |\n"
        return md

    def build(self) -> tuple[str, set[str]]:
        blocks = []
        for _ in range(self.rng.randint(6, 16)):
            kind = self.rng.choice(
                ["heading", "para", "para", "list", "list", "quote", "table", "code", "hr"]
            )
            if kind == "heading":
                blocks.append(self._heading())
            elif kind == "para":
                blocks.append(self._inline())
            elif kind == "list":
                blocks.append(self._list(self.rng.random() < 0.5, self.rng.randint(0, 5)))
            elif kind == "quote":
                blocks.append(self._quote(self.rng.randint(0, 2)))
            elif kind == "table":
                blocks.append(self._table())
            elif kind == "code":
                blocks.append(self._code())
            else:
                blocks.append(self.rng.choice(["---", "***", "___"]))
        return "\n\n".join(blocks), set(self.expected)


def _run(tmp_path, markdown: str, **chrome):
    src = tmp_path / "doc.md"
    src.write_text(markdown, encoding="utf-8")
    out = tmp_path / "doc.docx"
    cfg = RunConfig(input_path=str(src), output_path=str(out))
    if chrome:
        cfg = RunConfig(input_path=str(src), output_path=str(out), chrome=chrome)
    return convert(cfg), out


@pytest.mark.parametrize("seed", range(200))
def test_generated_documents_survive(seed, tmp_path, read_docx_text):
    markdown, expected = _Generator(random.Random(seed)).build()
    result, out = _run(tmp_path, markdown)

    assert out.read_bytes()[:2] == b"PK", f"seed {seed}: not a valid docx"
    assert result.warnings == [], f"seed {seed}: unexpected warnings {result.warnings}"

    text = read_docx_text(out)
    missing = sorted(t for t in expected if t not in text)
    assert not missing, (
        f"seed {seed}: {len(missing)}/{len(expected)} sentinels missing, "
        f"e.g. {missing[:8]}\n--- markdown ---\n{markdown[:1200]}"
    )


@pytest.mark.parametrize("seed", range(40))
def test_random_inline_nesting_does_not_crash(seed, tmp_path):
    rng = random.Random(9000 + seed)
    toks = [f"t{i}" for i in range(rng.randint(4, 9))]
    text = "".join(
        rng.choice([f"**{t}**", f"*{t}*", f"`{t}`", f"***{t}***", f"[{t}](u)", t]) for t in toks
    )
    _, out = _run(tmp_path, text)
    assert out.exists()


# --------------------------------------------------------------------------
# 2. curated hard cases (presence of text)
# --------------------------------------------------------------------------
_CURATED = {
    "xml_specials": (
        'Tom & Jerry, 5 > 3, 100% done, "quoted" and it\'s fine',
        ["Tom & Jerry", "5 > 3", "100%", '"quoted"', "it's fine"],
    ),
    "ampersands": ("AT&T, R&D, Q&A, a&&b end", ["AT&T", "R&D", "Q&A", "a&&b"]),
    "less_than_not_tag": (
        "if a < b and c <= d and e< f then g",
        ["a < b", "c <= d", "e< f"],
    ),
    "emphasis_combo": (
        "***bold italic*** then **b `c` *i*** end",
        ["bold italic", "b", "c", "i", "end"],
    ),
    "unicode_mix": (
        "café résumé naïve 你好世界 Привет мир مرحبا العالم 🎉🚀 Ω≈ç√",
        ["café", "résumé", "naïve", "你好世界", "Привет", "مرحبا", "🎉🚀", "Ω≈ç√"],
    ),
    "escaped_markdown": (
        r"\*literal stars\* and \# literal hash and \`literal backtick\`",
        ["*literal stars*", "# literal hash", "`literal backtick`"],
    ),
    "autolink": (
        "visit <https://example.com/path?q=1&r=2> now",
        ["https://example.com/path?q=1&r=2", "visit", "now"],
    ),
    "pipe_in_code": ("run `ls | grep x` please", ["ls | grep x", "run", "please"]),
    "backtick_in_code": ("value ``code with ` backtick`` here", ["code with ` backtick"]),
    "entity_decoding": (
        "Fish &amp; Chips, &copy; Circeus, letter &#65; done",
        ["Fish & Chips", "© Circeus", "letter A done"],
    ),
    "setext_headings": (
        "Big Title\n=========\n\nSmaller One\n-----------\n\nbody text",
        ["Big Title", "Smaller One", "body text"],
    ),
    "all_heading_levels": (
        "# H one\n## H two\n### H three\n#### H four\n##### H five\n###### H six",
        ["H one", "H two", "H three", "H four", "H five", "H six"],
    ),
    "hr_variants": (
        "aaa\n\n---\n\nbbb\n\n***\n\nccc\n\n___\n\nddd",
        ["aaa", "bbb", "ccc", "ddd"],
    ),
    "reference_link": (
        "See [the guide][g] here.\n\n[g]: https://e.com/guide",
        ["the guide", "See", "here"],
    ),
    "loose_list_multi_para": (
        "- first para\n\n  second para\n\n- another item",
        ["first para", "second para", "another item"],
    ),
    "hard_break": ("line one  \nline two after break", ["line one", "line two after break"]),
    "adjacent_emphasis": ("**a**b**c** and *d*e*f* end", ["a", "b", "c", "d", "e", "f", "end"]),
    "deep_nested_bullets": (
        "- lv0\n  - lv1\n    - lv2\n      - lv3\n        - lv4\n          - lv5",
        ["lv0", "lv1", "lv2", "lv3", "lv4", "lv5"],
    ),
    "mixed_list_nesting": (
        "1. one\n   - two\n     1. three\n2. four",
        ["one", "two", "three", "four"],
    ),
    "blockquote_list_and_code": (
        "> outer quote\n>\n> - qitem1\n> - qitem2\n>\n> ```\n> quoted code line\n> ```",
        ["outer quote", "qitem1", "qitem2", "quoted code line"],
    ),
    "table_formatted_specials": (
        "| Name & Co | Val |\n|:--|--:|\n| **bold x** | 5>3 |\n| `code y` | |\n| plain z | a&b |",
        ["Name & Co", "bold x", "5>3", "code y", "plain z", "a&b"],
    ),
    "code_preserves_md_and_html": (
        "```\n# not a heading\n- not a list\n<div>literal</div>\na & b\n```",
        ["# not a heading", "- not a list", "<div>literal</div>", "a & b"],
    ),
    "long_token": ("prefix " + "L" + "x" * 800 + " suffix", ["L" + "x" * 800]),
    "many_inline_elements": (
        " ".join(f"**w{i}**" if i % 2 else f"`w{i}`" for i in range(40)),
        ["w0", "w17", "w39"],
    ),
}


@pytest.mark.parametrize("name", sorted(_CURATED))
def test_curated_text_survives(name, tmp_path, read_docx_text):
    markdown, must_contain = _CURATED[name]
    result, out = _run(tmp_path, markdown)
    text = read_docx_text(out)
    missing = [s for s in must_contain if s not in text]
    assert not missing, f"{name}: missing {missing}\ntext={text!r}"


# --------------------------------------------------------------------------
# 2b. curated behavior (warnings / stripping)
# --------------------------------------------------------------------------
def test_html_in_prose_is_stripped_and_warned(tmp_path, read_docx_text):
    result, out = _run(tmp_path, "Hello <b>bold</b> <em>x</em> <span>y</span> world")
    text = read_docx_text(out)
    assert "bold" in text and "x" in text and "y" in text
    assert "<b>" not in text and "<span>" not in text
    assert {"b", "em", "span"} <= set(result.warnings)


def test_html_inside_code_is_preserved_not_warned(tmp_path, read_docx_text):
    result, out = _run(tmp_path, "Run `<script>alert(1)</script>` safely")
    text = read_docx_text(out)
    assert "<script>alert(1)</script>" in text
    assert result.warnings == []  # code must NOT trigger the strip-and-warn path


def test_br_is_a_break_not_a_warning(tmp_path, read_docx_text):
    result, out = _run(tmp_path, "a<br>b<br/>c")
    text = read_docx_text(out)
    assert "a" in text and "b" in text and "c" in text
    assert "br" not in result.warnings


def test_missing_image_warns_and_keeps_alt(tmp_path, read_docx_text):
    result, out = _run(tmp_path, "![my alt text](does-not-exist.png)")
    text = read_docx_text(out)
    assert "[image: my alt text]" in text
    assert "image-not-found:does-not-exist.png" in result.warnings
