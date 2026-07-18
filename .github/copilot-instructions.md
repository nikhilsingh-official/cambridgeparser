# Copilot instructions

This repository is a Python pipeline for parsing CS past-paper PDFs, OCR outputs, mark schemes, and pseudocode-analysis artifacts.

## Build, test, lint

- Full test suite: `python -m unittest discover -s tests -p 'test_*.py'`
- Single test example: `python -m unittest tests.test_segmentation.SegmentationTests.test_primary_ends_at_next_primary_not_secondary`
- msplitter tests (outside tests/): `python -m unittest src.pipeline.msplitter.tests.test_markers`
- Linting: no repo-configured linter.

## Key entry points

- Normalize marker outputs: `python -m src.pipeline.msplitter.normalize_marker_output --paper <paper_code> --marker-output-dir <raw_marker_dir> --ocr-dir <ocr_dir> --normalized-output-dir <normalized_dir>` (or `--all`)
- qsplitter CLI: `python -m src.pipeline.parser.qsplitter --paper <paper_code> --pdf-dir resources/pdfs/cs_papers --ocr-dir <ocr_dir> --marker-dir <normalized_marker_dir> --output-dir qp_output [--debug-bboxes]`
- Mark-scheme parser CLI: `python -m src.pipeline.msplitter.ms_parser --paper <paper_code> --pdf-dir resources/pdfs/cs_papers --marker-dir <normalized_marker_dir> --output-dir output/mark_scheme_segments [--debug-tables]`

## High-level architecture

- Inputs: PDFs live in `resources/pdfs/cs_papers`, OCR outputs are per-paper folders with `results.json`, and marker output is per-paper JSON (`<paper>.json` with optional `_meta`).
- Marker normalization (msplitter) rescales raw Marker JSON bboxes/polygons into OCR image coordinates so qsplitter and ms_parser can align OCR + marker geometry.
- qsplitter loads PDFs + OCR + normalized markers, excludes headers/footers/pictures and the first page, detects question/subpart markers, clusters them, and emits hierarchy.json + segmented_questions.json per paper.
- msplitter/ms_parser parses mark-scheme tables (Marker or fitz tables) into question/answer/marks rows, normalizes markers, and writes hierarchical mark-scheme JSON; optional debug images require Pillow.
- analysis/diagnostics and pseudocode_tools consume qsplitter/msplitter outputs for inspection, refinement, and export workflows.

## Key conventions

- Treat normalized marker JSON as derived artifacts; update raw marker/OCR inputs and re-run normalization instead of editing normalized files.
- Keep coordinate conversion centralized in `src/pipeline/msplitter/normalize_marker_output.py`; bbox/polygon normalization is intentionally recursive.
- qsplitter exclusion logic filters Picture/PageHeader/PageFooter blocks and excludes the first page bbox before marker detection; preserve when adjusting marker logic.
- Heuristic knobs for marker detection live in `src/pipeline/parser/qsplitter/builder.py` (for example, `REQUIRE_BOLD_MARKERS`, `QUESTION_MARKER_MAX_X`); adjust alongside tests.
- Use package imports under `src.pipeline` and invoke CLIs as modules (`python -m ...`).
- qsplitter debug artifacts are gated by `QSPLITTER_DEBUG=1` or `--debug-bboxes` and are written into the per-paper output directory.
