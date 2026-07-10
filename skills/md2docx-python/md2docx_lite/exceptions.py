"""Custom exception classes. No logic — just definitions."""

from __future__ import annotations


class ConfigError(Exception):
    """Configuration is invalid or internally inconsistent."""


class ConversionError(Exception):
    """A document conversion failed (bad input, unreadable asset, etc.)."""
