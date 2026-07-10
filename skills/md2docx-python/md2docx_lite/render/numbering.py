"""List numbering management.

python-docx's built-in list styles can't restart ordered lists or use custom
bullet glyphs cleanly, so we inject our own ``abstractNum``/``num`` definitions
into the document's numbering part — one shared bullet definition (two levels)
and a fresh, restart-at-1 definition per ordered list.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from .oxml import nsdecls, parse_xml, qn

if TYPE_CHECKING:
    from ..config import Theme


class NumberingManager:
    def __init__(self, document, theme: "Theme") -> None:
        self._numbering = document.part.numbering_part.element
        self._theme = theme
        self._bullet_id: int | None = None

    # -- id allocation ----------------------------------------------------
    def _next_abstract_id(self) -> int:
        ids = [int(e.get(qn("w:abstractNumId"))) for e in self._numbering.findall(qn("w:abstractNum"))]
        return max(ids) + 1 if ids else 0

    def _next_num_id(self) -> int:
        ids = [int(e.get(qn("w:numId"))) for e in self._numbering.findall(qn("w:num"))]
        return max(ids) + 1 if ids else 1

    def _create(self, make_abstract: Callable[[int], str]) -> int:
        abstract_id = self._next_abstract_id()
        abstract_el = parse_xml(make_abstract(abstract_id))
        # abstractNum must precede num elements in the part
        first_num = self._numbering.find(qn("w:num"))
        if first_num is not None:
            first_num.addprevious(abstract_el)
        else:
            self._numbering.append(abstract_el)

        num_id = self._next_num_id()
        num_el = parse_xml(
            f'<w:num {nsdecls("w")} w:numId="{num_id}">'
            f'<w:abstractNumId w:val="{abstract_id}"/></w:num>'
        )
        self._numbering.append(num_el)
        return num_id

    # -- public -----------------------------------------------------------
    def bullet_id(self) -> int:
        """The shared bullet numbering id (created once)."""
        if self._bullet_id is None:
            self._bullet_id = self._create(self._bullet_abstract)
        return self._bullet_id

    def new_ordered(self) -> int:
        """A fresh ordered numbering id that restarts at 1."""
        return self._create(self._ordered_abstract)

    # -- xml builders -----------------------------------------------------
    def _bullet_abstract(self, aid: int) -> str:
        n = self._theme.numbering
        return (
            f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{aid}">'
            f'<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
            f'<w:lvlText w:val="{n.bullet}"/><w:lvlJc w:val="left"/>'
            f'<w:pPr><w:ind w:left="420" w:hanging="260"/></w:pPr></w:lvl>'
            f'<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
            f'<w:lvlText w:val="{n.sub_bullet}"/><w:lvlJc w:val="left"/>'
            f'<w:pPr><w:ind w:left="840" w:hanging="260"/></w:pPr></w:lvl>'
            f"</w:abstractNum>"
        )

    def _ordered_abstract(self, aid: int) -> str:
        return (
            f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{aid}">'
            f'<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
            f'<w:lvlText w:val="%1."/><w:lvlJc w:val="left"/>'
            f'<w:pPr><w:ind w:left="420" w:hanging="260"/></w:pPr></w:lvl>'
            f'<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/>'
            f'<w:lvlText w:val="%2."/><w:lvlJc w:val="left"/>'
            f'<w:pPr><w:ind w:left="840" w:hanging="260"/></w:pPr></w:lvl>'
            f"</w:abstractNum>"
        )
