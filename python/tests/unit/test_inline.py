"""Unit tests for the inline token -> run mapping."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from md2docx.render.context import RenderContext
from md2docx.render.inline import render_inline


def _inline_token(md, text):
    """First inline token from a one-paragraph markdown string."""
    tokens = md.parse(text)
    return next(t for t in tokens if t.type == "inline")


def _render(md, theme, text):
    doc = Document()
    para = doc.add_paragraph()
    ctx = RenderContext(theme=theme, doc_dir=Path("."))
    render_inline(para, _inline_token(md, text), ctx)
    return para, ctx


def test_plain_bold_italic_code(md, theme):
    para, _ = _render(md, theme, "plain **bold** *italic* `code`")
    by_text = {r.text: r for r in para.runs}
    assert by_text["bold"].bold is True
    assert by_text["italic"].italic is True
    # inline code uses the mono font
    assert by_text["code"].font.name == theme.mono_font


def test_nested_emphasis(md, theme):
    para, _ = _render(md, theme, "**bold with *both* inside**")
    both = next(r for r in para.runs if r.text == "both")
    assert both.bold is True and both.italic is True


def test_link_becomes_hyperlink(md, theme):
    para, _ = _render(md, theme, "see [the site](https://example.com) now")
    hyperlinks = para._p.findall(qn("w:hyperlink"))
    assert len(hyperlinks) == 1
    # link text lives inside the hyperlink element, not as a bare run
    assert "the site" in hyperlinks[0].xml


def test_html_stripped_and_warned(md, theme):
    para, ctx = _render(md, theme, "keep <b>this</b> and <i>that</i>")
    joined = "".join(r.text for r in para.runs)
    assert "this" in joined and "that" in joined
    assert "<b>" not in joined and "<i>" not in joined
    assert set(ctx.warnings) == {"b", "i"}


def test_br_becomes_line_break(md, theme):
    para, ctx = _render(md, theme, "line one<br>line two")
    assert any(r._r.findall(qn("w:br")) for r in para.runs)
    assert "br" not in ctx.warnings  # <br> is handled, not warned
