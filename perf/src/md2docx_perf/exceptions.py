"""Custom exception classes. No logic — just definitions."""

from __future__ import annotations


class ConfigError(Exception):
    """Configuration is invalid or internally inconsistent."""


class BenchError(Exception):
    """A benchmark run could not be carried out (missing impls, inputs, etc.)."""
