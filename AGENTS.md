# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python pipeline for parsing Computer Science past-paper PDFs, OCR outputs, mark schemes, and pseudocode-writing results.

- `src/pipeline/parser/qsplitter/` contains question splitting, hierarchy building, segmentation, debug helpers, and the CLI.
- `src/pipeline/msplitter/` contains mark-scheme parsing, marker extraction, JSON IO, and normalization scripts.
- `src/pipeline/analysis/diagnostics/` contains diagnostics CLIs and pseudocode refinement rules.
- `src/pipeline/pseudocode_tools/`, `src/pipeline/runners/`, and `src/pipeline/scripts/` contain batch and export utilities.
- `src/resources/` contains shared path defaults for source inputs and parser-created generated artifacts.
- `src/website/` contains the website frontend for browsing and grading generated resources.
- `tests/` and `src/pipeline/msplitter/tests/` contain `unittest` test modules.
- `resources/pdfs/cs_papers/` stores source PDFs. `resources/generated/` is the default home for parser-created artifacts such as `qp_output/`, `ms_output/`, normalized Marker output, and `pseudocode_writing_hits/`. Root-level `qp_output/`, `ms_output/`, `pseudocode_writing_hits/`, `normalize/`, and `legacy/` are legacy generated or historical data.

Use package paths under `src.pipeline` for parser imports and CLIs, `src.resources.paths` for filesystem defaults, and `src.website` for frontend imports and CLIs. Do not add root-level symlinks back as module shortcuts.

## Build, Test, and Development Commands

- `python -m unittest discover -s tests -p 'test_*.py'` runs the main test suite.
- `python -m unittest src.pipeline.msplitter.tests.test_markers` runs the msplitter package test currently outside `tests/`.
- `python -m src.pipeline.parser.qsplitter --paper 9618_w25_qp_12 --pdf-dir resources/pdfs/cs_papers --ocr-dir <ocr_dir> --marker-dir <marker_dir> --output-dir resources/generated/qp_output` processes one paper.
- `python -m src.pipeline.parser.qsplitter --all --pdf-dir resources/pdfs/cs_papers --ocr-dir <ocr_dir> --marker-dir <marker_dir> --output-dir resources/generated/qp_output` processes all available marker inputs.

No packaging file or dependency lockfile is present. Document new runtime dependencies when adding them; current code imports `fitz`/PyMuPDF and optionally Pillow for debug rendering.

## Coding Style & Naming Conventions

Use standard Python style: 4-space indentation, `snake_case` functions and variables, `PascalCase` classes, and lowercase module names with underscores. Prefer `pathlib.Path` for paths and local JSON helpers over ad hoc file handling. Keep CLI arguments explicit, matching names such as `--pdf-dir` and `--output-dir`.

## Testing Guidelines

Tests use Python `unittest`; name files `test_*.py` and methods `test_<behavior>`. Add focused tests beside the affected area or in `tests/` for cross-module behavior. Parser and segmentation changes should cover marker hierarchy, page boundaries, and mark extraction.

## Commit & Pull Request Guidelines

This checkout has no readable Git history, so no local convention can be inferred. Use concise imperative subjects, for example `Fix qsplitter secondary marker assignment`. Pull requests should include the problem, paper codes used for validation, commands run, and screenshots or debug output paths for bbox rendering changes.

## Security & Configuration Tips

Do not commit private OCR exports, credentials, or large generated batches unless they are intentional fixtures or reviewed production assets required under `src/website/frontend/public`. Prefer small JSON fixtures over whole PDF-derived output trees for tests.
