"""Diagnostics helpers and CLI entrypoints for qsplitter."""

from .debug_renderer import write_debug_page_images
from .diagnostics import run_diagnostics_for_paper, validate_hierarchy

__all__ = [
    "write_debug_page_images",
    "run_diagnostics_for_paper",
    "validate_hierarchy",
]
