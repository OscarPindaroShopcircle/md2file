"""Unit tests for config models, loading, and CLI-override merging."""

from __future__ import annotations

import json

import pytest
import yaml
from pydantic import ValidationError

from md2docx.config_models import (
    RunConfig,
    Theme,
    build_config,
    load_config_file,
    save_config,
)
from md2docx.exceptions import ConfigError


def test_defaults_match_circeus_light():
    theme = Theme()
    assert theme.font == "Calibri"
    assert theme.colors.primary == "1A365D"
    assert theme.headings.h1.size == 22
    assert theme.headings.level(5) is theme.headings.h3  # h4-h6 fall back to h3
    assert theme.page.content_width == 12240 - 1440 - 1440


def test_invalid_hex_color_rejected():
    with pytest.raises(ValidationError):
        Theme.model_validate({"colors": {"text": "zzz"}})


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Theme.model_validate({"nonexistent": 1})


def test_load_config_file_yaml_and_json(tmp_path):
    y = tmp_path / "c.yaml"
    y.write_text("input_path: a.md\ntheme:\n  font: Georgia\n")
    assert load_config_file(y)["theme"]["font"] == "Georgia"

    j = tmp_path / "c.json"
    j.write_text(json.dumps({"input_path": "a.md"}))
    assert load_config_file(j)["input_path"] == "a.md"


def test_load_config_file_bad_extension(tmp_path):
    bad = tmp_path / "c.txt"
    bad.write_text("nope")
    with pytest.raises(ConfigError):
        load_config_file(bad)


def test_build_config_priority_cli_over_file(tmp_path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "input_path": "from_file.md",
                "chrome": {"title": "File title", "page_numbers": False},
            }
        )
    )
    cfg = build_config(cfg_file, input_path="from_cli.md", title="CLI title")
    # CLI wins where provided
    assert cfg.input_path == "from_cli.md"
    assert cfg.chrome.title == "CLI title"
    # file value preserved where CLI didn't override (shallow chrome merge)
    assert cfg.chrome.page_numbers is False


def test_build_config_requires_input():
    with pytest.raises(ValidationError):
        build_config(None)  # no input anywhere


def test_build_config_none_flags_do_not_override(tmp_path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(yaml.dump({"input_path": "a.md", "chrome": {"title": "Keep me"}}))
    cfg = build_config(cfg_file, title=None)  # None must not clobber
    assert cfg.chrome.title == "Keep me"


def test_generate_config_template_is_valid():
    template = RunConfig(input_path="input.md").model_dump()
    # the emitted template must itself validate
    assert RunConfig.model_validate(template).theme.font == "Calibri"


@pytest.mark.parametrize("fmt", ["yaml", "json"])
def test_save_config_mirrors_format(tmp_path, fmt):
    cfg = RunConfig(input_path="a.md")
    out = save_config(cfg, tmp_path, fmt, "doc")
    assert out.suffix == f".{fmt}"
    reloaded = load_config_file(out)
    assert reloaded["input_path"] == "a.md"
