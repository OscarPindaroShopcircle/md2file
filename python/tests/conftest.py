"""Shared pytest fixtures."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from markdown_it import MarkdownIt

from md2docx.config_models import Theme

# Test data lives inside the test tree — the app itself is imported as an
# installed package (`uv sync`), so tests never need to know the repo layout.
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def theme() -> Theme:
    """Default (circeus-light) theme."""
    return Theme()


@pytest.fixture
def md() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])


@pytest.fixture
def read_docx_xml():
    """Return a callable: path -> raw word/document.xml text."""

    def _read(path) -> str:
        with zipfile.ZipFile(path) as z:
            return z.read("word/document.xml").decode("utf-8")

    return _read


_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@pytest.fixture
def read_docx_text():
    """Return a callable: path -> all visible document text, XML-unescaped.

    Concatenates every ``w:t`` node in ``word/document.xml`` (covers body,
    tables, hyperlinks, code, cover chrome). ElementTree unescapes entities, so
    the result contains real characters (``&``, ``<``, ``>``, unicode) — the
    right surface to assert against for adversarial inputs.
    """
    import xml.etree.ElementTree as ET

    def _read(path) -> str:
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
        return "".join(node.text or "" for node in root.iter(f"{_W_NS}t"))

    return _read
