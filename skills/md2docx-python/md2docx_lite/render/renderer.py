"""Walk a flat markdown-it block token stream into python-docx elements,
owning list-nesting, blockquote, and table state."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import builders
from .context import RenderContext

_ALIGN_RE = re.compile(r"text-align:\s*(left|right|center)")


@dataclass
class _List:
    ordered: bool
    num_id: int


def _align_of(token) -> str:
    style = token.attrGet("style") or ""
    m = _ALIGN_RE.search(style)
    return m.group(1) if m else "left"


def _is_sole_image(inline_token) -> bool:
    kids = [c for c in (inline_token.children or []) if c.type != "softbreak"]
    return len(kids) == 1 and kids[0].type == "image"


def render(doc, tokens, ctx: RenderContext) -> None:
    list_stack: list[_List] = []
    quote_depth = 0
    i = 0
    n = len(tokens)

    while i < n:
        tk = tokens[i]
        ttype = tk.type

        if ttype == "heading_open":
            level = int(tk.tag[1]) if tk.tag[1:].isdigit() else 3
            builders.heading(doc, level, tokens[i + 1], ctx)
            i += 3  # heading_open, inline, heading_close
            continue

        if ttype == "paragraph_open":
            inline = tokens[i + 1]
            if list_stack:
                top = list_stack[-1]
                ilvl = min(1, len(list_stack) - 1)
                builders.list_item(doc, inline, ctx, top.num_id, ilvl)
            else:
                builders.body(doc, inline, ctx, quote=quote_depth > 0, center=_is_sole_image(inline))
            i += 3  # paragraph_open, inline, paragraph_close
            continue

        if ttype == "bullet_list_open":
            list_stack.append(_List(ordered=False, num_id=ctx.numbering.bullet_id()))
        elif ttype == "ordered_list_open":
            list_stack.append(_List(ordered=True, num_id=ctx.numbering.new_ordered()))
        elif ttype in ("bullet_list_close", "ordered_list_close"):
            list_stack.pop()
        elif ttype == "blockquote_open":
            quote_depth += 1
        elif ttype == "blockquote_close":
            quote_depth -= 1
        elif ttype == "hr":
            builders.divider(doc, ctx)
        elif ttype in ("fence", "code_block"):
            builders.code_block(doc, tk.content, ctx)
        elif ttype == "table_open":
            i = _render_table(doc, tokens, i, ctx)
            continue

        i += 1


def _render_table(doc, tokens, start: int, ctx: RenderContext) -> int:
    headers: list = []
    rows: list[list] = []
    aligns: list[str] = []
    in_head = False
    current: list = []
    i = start + 1
    while i < len(tokens):
        t = tokens[i]
        tt = t.type
        if tt == "table_close":
            break
        if tt == "thead_open":
            in_head = True
        elif tt == "thead_close":
            in_head = False
        elif tt == "tr_open":
            current = []
        elif tt == "tr_close":
            if in_head:
                headers = current
            else:
                rows.append(current)
        elif tt in ("th_open", "td_open"):
            if in_head:
                aligns.append(_align_of(t))
            current.append(tokens[i + 1])  # the inline token
            i += 1  # skip the inline token
        i += 1

    builders.table(doc, headers, rows, aligns, ctx)
    return i + 1  # position past table_close
