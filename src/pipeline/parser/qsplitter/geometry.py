"""Compatibility exports for shared bbox helpers.

The qsplitter and msplitter pipelines use the same coordinate model. Keep the
implementation in one place so bbox changes do not drift between parsers.
"""

from src.pipeline.msplitter.geometry import *  # noqa: F401,F403
