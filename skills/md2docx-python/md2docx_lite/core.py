"""Business logic: markdown text -> a saved .docx. No typer/rich/pydantic here."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from docx import Document
from markdown_it import MarkdownIt

from .exceptions import ConversionError
from .render import builders, renderer
from .render.context import RenderContext
from .render.numbering import NumberingManager

if TYPE_CHECKING:  # type-only; keeps pydantic out of core at runtime
    from .config import RunConfig


@dataclass
class ConvertResult:
    output_path: Path
    output_dir: Path
    warnings: list[str] = field(default_factory=list)


def _markdown() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])


def convert(cfg: "RunConfig", *, dry_run: bool = False) -> ConvertResult:
    """Render the configured markdown file to a .docx and (unless dry-run) save it."""
    input_path = Path(cfg.input_path)
    if not input_path.is_file():
        raise ConversionError(f"Input file not found: {input_path}")

    output_path = (
        Path(cfg.output_path)
        if cfg.output_path
        else Path.cwd() / f"{input_path.stem}.docx"
    )

    src = input_path.read_text(encoding="utf-8")
    theme = cfg.theme

    doc = Document()
    builders.configure_document(doc, theme)

    ctx = RenderContext(theme=theme, doc_dir=input_path.parent)
    ctx.numbering = NumberingManager(doc, theme)

    if cfg.chrome.title:
        builders.cover(doc, cfg.chrome, theme, ctx)

    tokens = _markdown().parse(src)
    renderer.render(doc, tokens, ctx)

    if cfg.chrome.footer_text or cfg.chrome.page_numbers:
        builders.footer(doc, theme, cfg.chrome.footer_text, cfg.chrome.page_numbers)

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))

    return ConvertResult(output_path=output_path, output_dir=output_path.parent, warnings=list(ctx.warnings))
