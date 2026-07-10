"""Small value types shared across the render layer (no pydantic, no docx)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # type-only — keeps this module import-light
    from ..config import Theme


@dataclass
class RunStyle:
    """Default formatting for a run of text; emphasis toggles layer on top."""

    color: str
    font: str
    size: float
    bold: bool = False
    italic: bool = False


@dataclass
class RenderContext:
    """Threaded through the renderer: theme, where to resolve relative paths,
    accumulated warnings, and the numbering manager."""

    theme: "Theme"
    doc_dir: Path
    warnings: list[str] = field(default_factory=list)
    numbering: Any = None  # NumberingManager, attached by core (avoids a cycle)

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)


def base_style(theme: "Theme") -> RunStyle:
    """The default body run style for a theme."""
    return RunStyle(color=theme.colors.text, font=theme.font, size=theme.body.size)
