"""qsplitter package
Exports core functions for CLI use.
"""
from .builder import (
    build_hierarchical_structure,
    process_paper,
    process_all_papers,
    build_output_payload,
    load_paper_context,
    candidate_position,
)

def parse_mark_scheme_paper(*args, **kwargs):
    from src.pipeline.msplitter.ms_parser import parse_mark_scheme_paper as _parse_mark_scheme_paper

    return _parse_mark_scheme_paper(*args, **kwargs)


def process_mark_scheme_paper(*args, **kwargs):
    from src.pipeline.msplitter.ms_parser import process_mark_scheme_paper as _process_mark_scheme_paper

    return _process_mark_scheme_paper(*args, **kwargs)


def process_all_mark_scheme_papers(*args, **kwargs):
    from src.pipeline.msplitter.ms_parser import process_all_mark_scheme_papers as _process_all_mark_scheme_papers

    return _process_all_mark_scheme_papers(*args, **kwargs)

__all__ = [
    "build_hierarchical_structure",
    "process_paper",
    "process_all_papers",
    "build_output_payload",
    "load_paper_context",
    "candidate_position",
    "parse_mark_scheme_paper",
    "process_mark_scheme_paper",
    "process_all_mark_scheme_papers",
]
