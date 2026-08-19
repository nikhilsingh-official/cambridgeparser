# Repository Guidelines

## Project Structure & Module Organization

This repository holds everything behind **cambridgeparser.com**: a Python pipeline that turns Cambridge CS past papers into structured records, a Rust pseudocode parser, the Vue pseudocode IDE served from that data, and the Soluer paper solver.

- `apps/solver/` is the Soluer MCQ paper solver (Vue 3 + TypeScript + Supabase). It has its own `README.md`, `package.json`, and `docs/`; it was merged in from a separate repository with full history and does not share the root `package.json`.

- `src/pipeline/parser/qsplitter/` contains question splitting, hierarchy building, segmentation, debug helpers, and the CLI.
- `src/pipeline/msplitter/` contains mark-scheme parsing, marker extraction, JSON IO, and normalization scripts.
- `src/pipeline/analysis/diagnostics/` contains diagnostics CLIs and pseudocode refinement rules.
- `src/pipeline/pseudocode_tools/`, `src/pipeline/runners/`, and `src/pipeline/scripts/` contain batch and export utilities.
- `src/resources/` contains shared path defaults for source inputs and parser-created generated artifacts.
- `src/website/` contains the website frontend for browsing and grading generated resources.
- `tests/` and `src/pipeline/msplitter/tests/` contain `unittest` test modules.
- `resources/pdfs/cs_papers/` stores source PDFs and `resources/ocr/` the OCR exports. `resources/generated/` holds every parser-created artifact — `qp_output/`, `ms_output/`, `normalized_marker_output/`, `pseudocode_writing_hits/` — and `resources/legacy/` holds superseded historical output. `src/resources/paths.py` is the single source of truth for these locations; never hardcode a path that it already names.
- `supabase/` is the one Supabase project both apps share: `migrations/` (applied in filename order), `seeds/`, the `fetch-pdf` edge function, and `config.toml`. Connection details for both apps live in a single `.env` at the repository root — see `.env.example`.
- `docs/` holds the planning documents; `docs/roadmap.md` is the combined outstanding-work list for both apps and `docs/reference/` the syllabus and pseudocode-guide PDFs.

Use package paths under `src.pipeline` for parser imports and CLIs, `src.resources.paths` for filesystem defaults, and `src.website` for frontend imports and CLIs. Do not add root-level symlinks back as module shortcuts.

## Build, Test, and Development Commands

- `python -m unittest discover -s tests -p 'test_*.py'` runs the main test suite (257 tests).
- `npm run test:frontend` runs the IDE frontend tests; `cd apps/solver && npm test` runs the solver's.
- `npm run supabase:start` brings up the local stack and `npm run supabase:reset` applies `supabase/migrations/` plus the seeds. The `.sql` files under `tests/` are assertion scripts run with `psql` against that stack; they are not part of the `unittest` suite.
- `python -m unittest src.pipeline.msplitter.tests.test_markers` runs the msplitter package test currently outside `tests/`.
- `python -m src.pipeline.parser.qsplitter --paper 9618_w25_qp_12 --pdf-dir resources/pdfs/cs_papers --ocr-dir <ocr_dir> --marker-dir <marker_dir> --output-dir resources/generated/qp_output` processes one paper.
- `python -m src.pipeline.parser.qsplitter --all --pdf-dir resources/pdfs/cs_papers --ocr-dir <ocr_dir> --marker-dir <marker_dir> --output-dir resources/generated/qp_output` processes all available marker inputs.

Python dependencies are pinned in `requirements.txt`; JavaScript for the IDE in the root `package-lock.json` and for the solver in `apps/solver/package-lock.json`. npm is the package manager — there is no pnpm workspace. Document new runtime dependencies when adding them; current code imports `fitz`/PyMuPDF and optionally Pillow for debug rendering.

## Coding Style & Naming Conventions

Use standard Python style: 4-space indentation, `snake_case` functions and variables, `PascalCase` classes, and lowercase module names with underscores. Prefer `pathlib.Path` for paths and local JSON helpers over ad hoc file handling. Keep CLI arguments explicit, matching names such as `--pdf-dir` and `--output-dir`.

## Testing Guidelines

Tests use Python `unittest`; name files `test_*.py` and methods `test_<behavior>`. Add focused tests beside the affected area or in `tests/` for cross-module behavior. Parser and segmentation changes should cover marker hierarchy, page boundaries, and mark extraction.

## Commit & Pull Request Guidelines

Use concise imperative subjects, optionally scoped — `solver: sync highlight mode across UI`, `Fix qsplitter secondary marker assignment`. Explain *why* in the body.

AI-generated code must be marked as such: a header block on wholly-generated files, an `// ` (or `# `) comment on generated lines inside hand-written ones. This is a hard requirement across both apps. Pull requests should include the problem, paper codes used for validation, commands run, and screenshots or debug output paths for bbox rendering changes.

## Security & Configuration Tips

Do not commit private OCR exports, credentials, or large generated batches unless they are intentional fixtures or reviewed production assets required under `src/website/frontend/public`. Prefer small JSON fixtures over whole PDF-derived output trees for tests.
