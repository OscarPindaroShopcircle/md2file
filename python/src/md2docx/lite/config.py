"""Dataclass mirror of the config models — no pydantic.

Field names and defaults are kept identical to ``md2docx.config_models`` so the
shared rendering engine produces byte-identical document parts from either
config system (the parity tests enforce this). Validation is intentionally
minimal — this is the barebones path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class Margin:
    top: int = 1440
    right: int = 1440
    bottom: int = 1440
    left: int = 1440


@dataclass
class Page:
    width: int = 12240
    height: int = 15840
    margin: Margin = field(default_factory=Margin)

    @property
    def content_width(self) -> int:
        return self.width - self.margin.left - self.margin.right


@dataclass
class Colors:
    text: str = "1A202C"
    primary: str = "1A365D"
    secondary: str = "2C7A7B"
    muted: str = "718096"
    panel: str = "F7FAFC"
    divider: str = "CBD5E0"
    bg: str = "FFFFFF"
    code_text: str = "2D3748"
    code_bg: str = "F1F5F9"


@dataclass
class Body:
    size: float = 11
    line: float = 1.3
    after: float = 8
    list_after: float = 3


@dataclass
class Heading:
    size: float
    color: str
    before: float
    after: float
    rule: bool = False
    rule_size: int = 4
    bold: bool = True


@dataclass
class Headings:
    h1: Heading = field(
        default_factory=lambda: Heading(size=22, color="1A365D", before=18, after=8, rule=True, rule_size=6)
    )
    h2: Heading = field(default_factory=lambda: Heading(size=16, color="1A365D", before=14, after=6))
    h3: Heading = field(default_factory=lambda: Heading(size=13, color="2C7A7B", before=10, after=4))

    def level(self, n: int) -> Heading:
        return {1: self.h1, 2: self.h2, 3: self.h3}[min(3, max(1, n))]


@dataclass
class Code:
    size: float = 9.5


@dataclass
class Table:
    border_size: int = 4
    border_color: str = "CBD5E0"
    header_fill: str = "1A365D"
    header_color: str = "FFFFFF"
    cell_pad: int = 90


@dataclass
class Numbering:
    bullet: str = "•"
    sub_bullet: str = "◦"


@dataclass
class Cover:
    top_space: float = 60
    title_size: float = 34
    subtitle_size: float = 13
    eyebrow_size: float = 10.5
    title_bold: bool = True


@dataclass
class Footer:
    size: float = 9


@dataclass
class Image:
    max_width_px: int = 480


@dataclass
class Theme:
    font: str = "Calibri"
    mono_font: str = "Consolas"
    colors: Colors = field(default_factory=Colors)
    page: Page = field(default_factory=Page)
    body: Body = field(default_factory=Body)
    headings: Headings = field(default_factory=Headings)
    code: Code = field(default_factory=Code)
    table: Table = field(default_factory=Table)
    numbering: Numbering = field(default_factory=Numbering)
    cover: Cover = field(default_factory=Cover)
    footer: Footer = field(default_factory=Footer)
    image: Image = field(default_factory=Image)


@dataclass
class Chrome:
    title: Optional[str] = None
    eyebrow: Optional[str] = None
    subtitles: list[str] = field(default_factory=list)
    logo: Optional[str] = None
    logo_width: int = 160
    footer_text: Optional[str] = None
    page_numbers: bool = False


@dataclass
class RunConfig:
    input_path: str
    output_path: Optional[str] = None
    theme: Theme = field(default_factory=Theme)
    chrome: Chrome = field(default_factory=Chrome)


# --- construction from plain dicts (json/yaml) ---------------------------


def _from_dict(cls, data: Any):
    """Recursively build a dataclass from a dict, ignoring unknown keys."""
    if not is_dataclass(cls) or not isinstance(data, dict):
        return data
    kwargs = {}
    type_hints = {f.name: f.type for f in fields(cls)}
    for f in fields(cls):
        if f.name not in data:
            continue
        value = data[f.name]
        nested = _NESTED.get((cls.__name__, f.name))
        if nested is not None and isinstance(value, dict):
            kwargs[f.name] = _from_dict(nested, value)
        else:
            kwargs[f.name] = value
    return cls(**kwargs)


# explicit map of which fields are themselves dataclasses (avoids parsing typing)
_NESTED = {
    ("Page", "margin"): Margin,
    ("Headings", "h1"): Heading,
    ("Headings", "h2"): Heading,
    ("Headings", "h3"): Heading,
    ("Theme", "colors"): Colors,
    ("Theme", "page"): Page,
    ("Theme", "body"): Body,
    ("Theme", "headings"): Headings,
    ("Theme", "code"): Code,
    ("Theme", "table"): Table,
    ("Theme", "numbering"): Numbering,
    ("Theme", "cover"): Cover,
    ("Theme", "footer"): Footer,
    ("Theme", "image"): Image,
    ("RunConfig", "theme"): Theme,
    ("RunConfig", "chrome"): Chrome,
}


def load_config_file(path: Path) -> dict:
    """Load a JSON (always) or YAML (if pyyaml is installed) config into a dict."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on env
            raise ValueError(
                f"YAML config {path} requires pyyaml, which is not installed. Use a .json config."
            ) from exc
        return yaml.safe_load(text) or {}
    raise ValueError(f"Unsupported config extension {path.suffix!r}. Use .json, .yaml, or .yml.")


def build_config(
    config_file: Optional[Path],
    *,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
    eyebrow: Optional[str] = None,
    subtitles: Optional[list[str]] = None,
    logo: Optional[str] = None,
    logo_width: Optional[int] = None,
    footer_text: Optional[str] = None,
    page_numbers: Optional[bool] = None,
) -> RunConfig:
    """Merge a config file with CLI overrides (CLI > file > default)."""
    base: dict = load_config_file(config_file) if config_file is not None else {}

    if input_path is not None:
        base["input_path"] = input_path
    if output_path is not None:
        base["output_path"] = output_path

    chrome = dict(base.get("chrome") or {})
    if title is not None:
        chrome["title"] = title
    if eyebrow is not None:
        chrome["eyebrow"] = eyebrow
    if subtitles:
        chrome["subtitles"] = subtitles
    if logo is not None:
        chrome["logo"] = logo
    if logo_width is not None:
        chrome["logo_width"] = logo_width
    if footer_text is not None:
        chrome["footer_text"] = footer_text
    if page_numbers is not None:
        chrome["page_numbers"] = page_numbers
    if chrome:
        base["chrome"] = chrome

    if "input_path" not in base:
        raise ValueError("No input file given (pass a markdown file or set input_path in the config).")

    return _from_dict(RunConfig, base)
