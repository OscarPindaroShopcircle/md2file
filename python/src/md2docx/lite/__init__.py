"""Barebones front-end for md2docx.

Same rendering engine (``md2docx.core`` / ``md2docx.render``), but a stdlib-only
front end: dataclasses instead of pydantic, argparse instead of typer, json
(optionally yaml if available) instead of pyyaml-required config. Importing this
package pulls in no typer / pydantic / rich / pyyaml.
"""
