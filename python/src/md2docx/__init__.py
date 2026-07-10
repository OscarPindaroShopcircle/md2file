"""md2docx — Markdown to styled Word (.docx), python-docx implementation."""

from .core import ConvertResult, convert

__all__ = ["convert", "ConvertResult"]
