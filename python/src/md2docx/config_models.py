"""Pydantic config models, config-file loading, and CLI-override merging.

This module owns the entire configuration surface. Per project rules it must not
import ``typer`` or ``rich``. A config is a full *run* description: the input
markdown, the output path, the visual ``theme``, and the document ``chrome``
(cover title, logo, footer, ...). YAML is the primary input format; CLI flags are
optional overrides.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .exceptions import ConfigError

# A 6-digit RRGGBB hex color (no leading '#') — matches what python-docx wants.
HexColor = Annotated[str, Field(pattern=r"^[0-9A-Fa-f]{6}$")]


class _Model(BaseModel):
    """Base for every config model: reject unknown keys so typos are caught."""

    model_config = ConfigDict(extra="forbid")


# --- theme sub-models ----------------------------------------------------


class Margin(_Model):
    top: int = Field(1440, description="Top margin in twips (1440 = 1 inch).")
    right: int = Field(1440, description="Right margin in twips.")
    bottom: int = Field(1440, description="Bottom margin in twips.")
    left: int = Field(1440, description="Left margin in twips.")


class Page(_Model):
    width: int = Field(12240, description="Page width in twips (Letter = 12240).")
    height: int = Field(15840, description="Page height in twips (Letter = 15840).")
    margin: Margin = Field(default_factory=Margin, description="Page margins.")

    @property
    def content_width(self) -> int:
        return self.width - self.margin.left - self.margin.right


class Colors(_Model):
    text: HexColor = Field("1A202C", description="Default body text color.")
    primary: HexColor = Field("1A365D", description="Primary/heading/title color.")
    secondary: HexColor = Field("2C7A7B", description="Accent color (links, eyebrow, h3).")
    muted: HexColor = Field("718096", description="Muted color (subtitles, quotes, footer).")
    panel: HexColor = Field("F7FAFC", description="Light panel/fill color.")
    divider: HexColor = Field("CBD5E0", description="Rule/divider line color.")
    bg: HexColor = Field("FFFFFF", description="Background color.")
    code_text: HexColor = Field("2D3748", description="Code text color.")
    code_bg: HexColor = Field("F1F5F9", description="Code background shading.")


class Body(_Model):
    size: float = Field(11, description="Body font size in points.")
    line: float = Field(1.3, description="Line spacing as a multiple.")
    after: float = Field(8, description="Space after a paragraph in points.")
    list_after: float = Field(3, description="Space after a list item in points.")


class Heading(_Model):
    size: float = Field(..., description="Heading font size in points.")
    color: HexColor = Field(..., description="Heading text color.")
    before: float = Field(..., description="Space before in points.")
    after: float = Field(..., description="Space after in points.")
    rule: bool = Field(False, description="Draw a bottom rule under the heading.")
    rule_size: int = Field(4, description="Rule thickness in eighths of a point.")
    bold: bool = Field(True, description="Render the heading bold.")


class Headings(_Model):
    h1: Heading = Field(
        default_factory=lambda: Heading(size=22, color="1A365D", before=18, after=8, rule=True, rule_size=6),
        description="Level-1 heading style.",
    )
    h2: Heading = Field(
        default_factory=lambda: Heading(size=16, color="1A365D", before=14, after=6),
        description="Level-2 heading style.",
    )
    h3: Heading = Field(
        default_factory=lambda: Heading(size=13, color="2C7A7B", before=10, after=4),
        description="Level-3 heading style (h4-h6 fall back to this).",
    )

    def level(self, n: int) -> Heading:
        return {1: self.h1, 2: self.h2, 3: self.h3}[min(3, max(1, n))]


class Code(_Model):
    size: float = Field(9.5, description="Monospace code font size in points.")


class Table(_Model):
    border_size: int = Field(4, description="Table border thickness in eighths of a point.")
    border_color: HexColor = Field("CBD5E0", description="Table border color.")
    header_fill: HexColor = Field("1A365D", description="Header-row background fill.")
    header_color: HexColor = Field("FFFFFF", description="Header-row text color.")
    cell_pad: int = Field(90, description="Cell padding in twips.")


class Numbering(_Model):
    bullet: str = Field("•", description="Top-level bullet glyph.")
    sub_bullet: str = Field("◦", description="Nested bullet glyph.")


class Cover(_Model):
    top_space: float = Field(60, description="Space above the cover block in points.")
    title_size: float = Field(34, description="Cover title size in points.")
    subtitle_size: float = Field(13, description="Cover subtitle size in points.")
    eyebrow_size: float = Field(10.5, description="Cover eyebrow size in points.")
    title_bold: bool = Field(True, description="Render the cover title bold.")


class Footer(_Model):
    size: float = Field(9, description="Footer font size in points.")


class Image(_Model):
    max_width_px: int = Field(480, description="Maximum embedded image width in pixels.")


class Theme(_Model):
    font: str = Field("Calibri", description="Body/heading font family.")
    mono_font: str = Field("Consolas", description="Monospace font for code.")
    colors: Colors = Field(default_factory=Colors)
    page: Page = Field(default_factory=Page)
    body: Body = Field(default_factory=Body)
    headings: Headings = Field(default_factory=Headings)
    code: Code = Field(default_factory=Code)
    table: Table = Field(default_factory=Table)
    numbering: Numbering = Field(default_factory=Numbering)
    cover: Cover = Field(default_factory=Cover)
    footer: Footer = Field(default_factory=Footer)
    image: Image = Field(default_factory=Image)


# --- chrome (per-document, non-theme presentation) -----------------------


class Chrome(_Model):
    title: Optional[str] = Field(None, description="Cover title. A cover page is emitted only if set.")
    eyebrow: Optional[str] = Field(None, description="Small label above the cover title.")
    subtitles: list[str] = Field(default_factory=list, description="Cover subtitles, in order.")
    logo: Optional[str] = Field(None, description="Cover logo image path (used only if it exists).")
    logo_width: int = Field(160, description="Cover logo width in pixels.")
    footer_text: Optional[str] = Field(None, description="Footer text (left side).")
    page_numbers: bool = Field(False, description="Show 'Page N' at the footer right.")


# --- top-level run config -------------------------------------------------


class RunConfig(_Model):
    input_path: str = Field(..., description="Path to the input markdown file.")
    output_path: Optional[str] = Field(
        None, description="Output .docx path. Defaults to the input basename + .docx in the cwd."
    )
    theme: Theme = Field(default_factory=Theme, description="Visual theme.")
    chrome: Chrome = Field(default_factory=Chrome, description="Cover/footer chrome.")


# --- loading and merging --------------------------------------------------


def load_config_file(path: Path) -> dict:
    """Load a YAML or JSON config file into a raw dict."""
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text) or {}
    if path.suffix == ".json":
        return json.loads(text)
    raise ConfigError(f"Unsupported config extension {path.suffix!r}. Use .yaml, .yml, or .json.")


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
    """Merge a config file with CLI overrides.

    Priority: CLI flag (non-None) > config file value > Pydantic default.
    Chrome overrides are merged one level deep into the ``chrome`` section.
    """
    base: dict = load_config_file(config_file) if config_file is not None else {}

    overrides: dict = {}
    if input_path is not None:
        overrides["input_path"] = input_path
    if output_path is not None:
        overrides["output_path"] = output_path

    chrome_over: dict = {}
    if title is not None:
        chrome_over["title"] = title
    if eyebrow is not None:
        chrome_over["eyebrow"] = eyebrow
    if subtitles:
        chrome_over["subtitles"] = subtitles
    if logo is not None:
        chrome_over["logo"] = logo
    if logo_width is not None:
        chrome_over["logo_width"] = logo_width
    if footer_text is not None:
        chrome_over["footer_text"] = footer_text
    if page_numbers is not None:
        chrome_over["page_numbers"] = page_numbers
    if chrome_over:
        overrides["chrome"] = chrome_over

    merged = {**base, **overrides}
    # shallow-merge the nested chrome section (one level deep only)
    if isinstance(base.get("chrome"), dict) and chrome_over:
        merged["chrome"] = {**base["chrome"], **chrome_over}

    return RunConfig.model_validate(merged)


def save_config(cfg: RunConfig, output_dir: Path, source_format: str, stem: str) -> Path:
    """Write the effective (merged, validated) config next to the output.

    Mirrors the input format: YAML in -> YAML out, otherwise JSON.
    """
    data = cfg.model_dump()
    if source_format == "yaml":
        out = output_dir / f"{stem}.used.yaml"
        out.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")
    else:
        out = output_dir / f"{stem}.used.json"
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out
