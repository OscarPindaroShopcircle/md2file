"""Integration tests: convert the shared fixtures to real .docx files."""

from __future__ import annotations

import pytest

from md2docx.config_models import Chrome, RunConfig
from md2docx.core import convert

FIXTURES = [
    "01-minimal.md",
    "02-lists.md",
    "03-inline.md",
    "04-table.md",
    "05-full.md",
    "06-inline-html.md",
    "circeus-report.md",
]


def _convert(fixtures_dir, name, tmp_path, **chrome):
    out = tmp_path / f"{name}.docx"
    cfg = RunConfig(
        input_path=str(fixtures_dir / name),
        output_path=str(out),
        chrome=Chrome(**chrome) if chrome else Chrome(),
    )
    return convert(cfg)


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_produces_valid_docx(fixtures_dir, name, tmp_path):
    result = _convert(fixtures_dir, name, tmp_path)
    data = result.output_path.read_bytes()
    assert data[:2] == b"PK"  # zip magic
    assert len(data) > 0


def test_minimal_content(fixtures_dir, tmp_path, read_docx_xml):
    result = _convert(fixtures_dir, "01-minimal.md", tmp_path)
    xml = read_docx_xml(result.output_path)
    assert "Hello World" in xml
    assert "single paragraph of body text" in xml


def test_table_content(fixtures_dir, tmp_path, read_docx_xml):
    result = _convert(fixtures_dir, "04-table.md", tmp_path)
    xml = read_docx_xml(result.output_path)
    assert "<w:tbl>" in xml
    assert "In progress" in xml


def test_full_has_all_features(fixtures_dir, tmp_path, read_docx_xml):
    result = _convert(fixtures_dir, "05-full.md", tmp_path)
    xml = read_docx_xml(result.output_path)
    for probe in ("<w:tbl>", "function greet", "This is a blockquote", "<w:drawing>", "<w:hyperlink"):
        assert probe in xml, probe
    assert not result.warnings  # sample image resolves


def test_inline_html_stripped_and_warned(fixtures_dir, tmp_path, read_docx_xml):
    result = _convert(fixtures_dir, "06-inline-html.md", tmp_path)
    xml = read_docx_xml(result.output_path)
    assert "bold via a b tag" in xml
    assert "block-level div" in xml
    assert "&lt;div" not in xml and "&lt;b&gt;" not in xml
    assert {"div", "b", "i"} <= set(result.warnings)


def test_cover_chrome_and_footer(fixtures_dir, tmp_path, read_docx_xml):
    result = _convert(
        fixtures_dir,
        "circeus-report.md",
        tmp_path,
        title="IP protection: multi-turn leakage detection",
        eyebrow="Internal engineering report",
        subtitles=["Branch: x", "Period: y"],
        footer_text="Circeus — confidential",
        page_numbers=True,
    )
    xml = read_docx_xml(result.output_path)
    assert "IP protection: multi-turn leakage detection" in xml
    assert "INTERNAL ENGINEERING REPORT" in xml  # eyebrow uppercased


def test_dry_run_writes_nothing(fixtures_dir, tmp_path):
    out = tmp_path / "nope.docx"
    cfg = RunConfig(input_path=str(fixtures_dir / "01-minimal.md"), output_path=str(out))
    convert(cfg, dry_run=True)
    assert not out.exists()
