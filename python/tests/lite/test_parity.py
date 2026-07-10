"""Parity tests: the barebones (lite) CLI must produce output identical to the
full (typer/pydantic) CLI, and its code path must not import the heavy deps.

Both CLIs are thin wrappers over the same engine, so equality is checked at three
levels: config models, the conversion engine fed by each config system, and the
actual CLI entry points end-to-end.
"""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path

import pytest

from md2docx import config_models as full
from md2docx import core
from md2docx.lite import config as lite

FIXTURES = Path(__file__).parent.parent / "fixtures"
FIXTURE_NAMES = [
    "01-minimal.md",
    "02-lists.md",
    "03-inline.md",
    "04-table.md",
    "05-full.md",
    "06-inline-html.md",
    "circeus-report.md",
]

# core.xml can carry package timestamps; every other part is content we control.
_VOLATILE = {"docProps/core.xml"}


def _parts(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def assert_docx_equal(a: Path, b: Path) -> None:
    pa, pb = _parts(a), _parts(b)
    assert set(pa) == set(pb), f"part names differ: {set(pa) ^ set(pb)}"
    for name in pa:
        if name in _VOLATILE:
            continue
        assert pa[name] == pb[name], f"part {name} differs"


# --- unit: config models agree -------------------------------------------


def test_theme_defaults_match():
    assert asdict(lite.Theme()) == full.Theme().model_dump()


def test_chrome_defaults_match():
    assert asdict(lite.Chrome()) == full.Chrome().model_dump()


def test_config_loaders_agree_on_json(tmp_path):
    cfg = {
        "input_path": "x.md",
        "output_path": "out.docx",
        "theme": {
            "font": "Georgia",
            "colors": {"text": "111111", "primary": "222222"},
            "headings": {"h1": {"size": 30, "color": "333333", "before": 20, "after": 10, "bold": False}},
            "cover": {"title_bold": False},
        },
        "chrome": {"title": "Hello", "subtitles": ["a", "b"], "page_numbers": True},
    }
    f = tmp_path / "c.json"
    f.write_text(json.dumps(cfg))

    pyd = full.build_config(f).model_dump()
    lt = asdict(lite.build_config(f))
    assert lt == pyd


def test_cli_overrides_win_in_both(tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"input_path": "file.md", "chrome": {"title": "File", "page_numbers": False}}))
    pyd = full.build_config(f, input_path="cli.md", title="CLI").model_dump()
    lt = asdict(lite.build_config(f, input_path="cli.md", title="CLI"))
    assert lt == pyd
    assert lt["input_path"] == "cli.md" and lt["chrome"]["title"] == "CLI"


# --- integration: engine output identical from each config system --------


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_engine_output_identical_defaults(name, tmp_path):
    fx = FIXTURES / name
    a, b = tmp_path / "full.docx", tmp_path / "lite.docx"
    core.convert(full.RunConfig(input_path=str(fx), output_path=str(a)))
    core.convert(lite.RunConfig(input_path=str(fx), output_path=str(b)))
    assert_docx_equal(a, b)


def test_engine_output_identical_config_driven(tmp_path):
    cfg = {
        "theme": {"font": "Georgia", "headings": {"h2": {"size": 18, "color": "445566", "before": 12, "after": 6}}},
        "chrome": {
            "title": "Parity Report",
            "eyebrow": "Test",
            "subtitles": ["one", "two"],
            "footer_text": "Confidential",
            "page_numbers": True,
        },
    }
    f = tmp_path / "c.json"
    f.write_text(json.dumps(cfg))
    fx = FIXTURES / "circeus-report.md"

    a, b = tmp_path / "full.docx", tmp_path / "lite.docx"
    core.convert(full.build_config(f, input_path=str(fx), output_path=str(a)))
    core.convert(lite.build_config(f, input_path=str(fx), output_path=str(b)))
    assert_docx_equal(a, b)


# --- end-to-end: the two CLIs agree --------------------------------------


@pytest.mark.parametrize("name", ["05-full.md", "circeus-report.md"])
def test_cli_entry_points_agree(name, tmp_path):
    from typer.testing import CliRunner

    from md2docx.cli import app
    from md2docx.lite.cli import main as lite_main

    fx = FIXTURES / name
    a, b = tmp_path / "full.docx", tmp_path / "lite.docx"
    args = ["--title", "T", "--eyebrow", "E", "--subtitle", "S1", "--footer", "F", "--page-numbers"]

    result = CliRunner().invoke(app, ["convert", str(fx), "-o", str(a), *args])
    assert result.exit_code == 0, result.output
    rc = lite_main([str(fx), "-o", str(b), *args])
    assert rc == 0

    assert_docx_equal(a, b)


# --- guard: lite path stays barebones ------------------------------------


def test_lite_imports_no_heavy_deps():
    code = (
        "import md2docx.lite.cli, sys, json; "
        "print(json.dumps([m for m in ('typer','pydantic','rich','yaml') if m in sys.modules]))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    loaded = json.loads(out.stdout.strip())
    assert loaded == [], f"lite CLI imported heavy deps: {loaded}"
