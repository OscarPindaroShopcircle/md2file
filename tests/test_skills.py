"""End-to-end tests for the self-contained skills.

Each skill is exercised exactly how an LLM would use it: run its tool scripts as
subprocesses and assert they emit a valid .docx with the expected content. A
skill whose toolchain isn't installed is SKIPPED (not failed), so CI on a machine
without, say, Node still passes while telling you the JS skill was untested.

Run with:  uv --project python run pytest tests/test_skills.py -v
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parents[1] / "skills"
PY_SKILL = SKILLS / "md2docx-python"
JS_SKILL = SKILLS / "md2docx-js"

_have = lambda tool: shutil.which(tool) is not None  # noqa: E731

need_uv = pytest.mark.skipif(not _have("uv"), reason="uv not installed — python skill untestable")
need_node = pytest.mark.skipif(
    not (_have("node") and _have("npm")), reason="node/npm not installed — js skill untestable"
)


def _run(cwd: Path, argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, timeout=300)


def _assert_docx(path: Path, must_contain: str) -> None:
    assert path.is_file(), f"no output at {path}"
    data = path.read_bytes()
    assert data[:2] == b"PK", "output is not a valid .docx (zip)"
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert must_contain in xml, f"expected text {must_contain!r} not found in output"
    return xml


# --- python skill (uv run, bundled lite engine) --------------------------

@need_uv
def test_python_skill_convert_string(tmp_path):
    out = tmp_path / "s.docx"
    r = _run(PY_SKILL, ["uv", "run", "scripts/convert_string.py",
                        "--text", "# PyString\n\nHello **world**.", "-o", str(out)])
    assert r.returncode == 0, r.stderr
    _assert_docx(out, "PyString")


@need_uv
def test_python_skill_convert_file(tmp_path):
    src = tmp_path / "in.md"
    src.write_text("# PyFile\n\n- one\n- two\n\n| A | B |\n|:--|--:|\n| 1 | 2 |\n", encoding="utf-8")
    out = tmp_path / "f.docx"
    r = _run(PY_SKILL, ["uv", "run", "scripts/convert_file.py", str(src), "-o", str(out)])
    assert r.returncode == 0, r.stderr
    xml = _assert_docx(out, "PyFile")
    assert "<w:tbl>" in xml


@need_uv
def test_python_skill_branded_theme_and_logo(tmp_path):
    out = tmp_path / "b.docx"
    r = _run(PY_SKILL, ["uv", "run", "scripts/convert_string.py", "--text", "# Brand",
                        "-c", "themes/circeus-brand.json", "--logo", "assets/circeus-logo.png",
                        "--title", "T", "-o", str(out)])
    assert r.returncode == 0, r.stderr
    xml = _assert_docx(out, "Brand")
    assert "<w:drawing>" in xml, "bundled logo should embed an image"


# --- js skill (python tool -> bundled node impl) -------------------------

@need_node
def test_js_skill_convert_string(tmp_path):
    out = tmp_path / "s.docx"
    r = _run(JS_SKILL, [sys.executable, "scripts/convert_string.py",
                        "--text", "# JsString\n\nHello **world**.", "-o", str(out)])
    assert r.returncode == 0, r.stderr
    _assert_docx(out, "JsString")


@need_node
def test_js_skill_convert_file(tmp_path):
    src = tmp_path / "in.md"
    src.write_text("# JsFile\n\n1. a\n2. b\n\n| A | B |\n|:--|--:|\n| 1 | 2 |\n", encoding="utf-8")
    out = tmp_path / "f.docx"
    r = _run(JS_SKILL, [sys.executable, "scripts/convert_file.py", str(src), "-o", str(out)])
    assert r.returncode == 0, r.stderr
    xml = _assert_docx(out, "JsFile")
    assert "<w:tbl>" in xml


@need_node
def test_js_skill_branded_theme_and_logo(tmp_path):
    out = tmp_path / "b.docx"
    r = _run(JS_SKILL, [sys.executable, "scripts/convert_string.py", "--text", "# Brand",
                        "--theme", "circeus-brand", "--logo", "assets/circeus-logo.png",
                        "--title", "T", "-o", str(out)])
    assert r.returncode == 0, r.stderr
    xml = _assert_docx(out, "Brand")
    assert "<w:drawing>" in xml, "bundled logo should embed an image"
