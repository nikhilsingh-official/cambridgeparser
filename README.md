# Pseudocode Solving Pipeline

Python tools for turning Cambridge CS question-paper PDFs, OCR output, Marker
layout JSON, and mark schemes into structured question/answer artifacts.

## Install

```bash
python -m pip install -r requirements.txt
```

`PyMuPDF` provides the `fitz` module used by parser and renderer entry points.
`Pillow` is used for debug and review screenshots. `pylatexenc` is only needed
when OCR lines contain `<math>...</math>` markers.

## Main Workflows

Normalize Marker coordinates:

```bash
python -m src.pipeline.msplitter.normalize_marker_output \
  --all \
  --marker-output-dir legacy/marker_output \
  --ocr-dir resources/ocr/surya_output \
  --normalized-output-dir normalize/normalized_marker_output
```

Build question-paper hierarchy and segmented text:

```bash
python -m src.pipeline.runners.qsplitter_batch \
  --pdf-dir resources/pdfs/cs_papers \
  --ocr-dir resources/ocr/surya_output \
  --marker-dir normalize/normalized_marker_output \
  --output-dir qp_output
```

Parse mark schemes:

```bash
python -m src.pipeline.msplitter.ms_parser \
  --pdf-dir resources/pdfs/cs_papers \
  --marker-dir normalize/normalized_marker_output \
  --output-dir ms_output
```

Select pseudocode-writing prompts:

```bash
python -m src.pipeline.pseudocode_tools.select_pseudocode_writing \
  --segments qp_output \
  --output-dir pseudocode_writing_hits \
  --rules-file src/pipeline/analysis/diagnostics/pseudocode_custom_rules.json
```

Build canonical question records (joins selection with `qp_output` and
`ms_output`, extracts structured marking points, reuses screenshots):

```bash
python -m src.pipeline.pseudocode_tools.build_final_records \
  --selected-json pseudocode_writing_hits/pseudocode_writing_selected.json \
  --qp-dir qp_output \
  --ms-dir ms_output \
  --output-json pseudocode_writing_hits/pseudocode_question_records.json
```

Validate generated artifacts (no model or network calls):

```bash
python -m src.pipeline.analysis.diagnostics.validate_extraction \
  --qp-dir qp_output \
  --ms-dir ms_output \
  --final-json pseudocode_writing_hits/pseudocode_question_records.json \
  --output-json pseudocode_writing_hits/extraction_validation.json
```

## Grading Stack

Build the Rust pseudocode parser (wraps the root `ast.rs`/`parser.rs`):

```bash
cd pseudocode-parser && cargo build --release && cargo test
```

The binary emits `cambridge-pseudocode-ast/v1` JSON:

```bash
pseudocode-parser/target/release/pseudocode-parser --format json --source-file answer.txt
```

`src.pipeline.grading.ast_adapter` invokes it from Python with a timeout and
returns `parsed-answer/v1` payloads. Set `PSEUDOCODE_PARSER_BIN` to override
binary discovery.

Run the grading web app (stdlib only, no framework):

```bash
python -m src.pipeline.webapp \
  --records pseudocode_writing_hits/pseudocode_question_records.json \
  --port 8000
```

Each record renders the cropped question image as the canonical view with a
"Text" toggle that reconstructs the on-page layout from the qsplitter word
boxes: words keep their original positions (selectable and copyable), Marker
figure/diagram/table regions are shown as crisp crops taken straight from the
PDF (`--pdf-dir`) rather than garbled text, and dotted/underscored blanks become
interactive input fields whose contents can be copied into the answer box. The
layout draws on `--qp-dir` (segmented questions) and `--marker-root` (normalized
Marker regions); see `src/pipeline/webapp/question_layout.py` and
`marker_regions.py`.

OpenRouter configuration (grading falls back to a deterministic dry run when
no key is set):

```bash
export OPENROUTER_API_KEY=...                       # user-provided secret
export OPENROUTER_MODEL=qwen/qwen2.5-coder-7b-instruct   # optional override
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1  # optional override
```

## Planning Docs

- `docs/project_direction.md` describes the current extraction pipeline and the intended AST-backed grading direction.
- `docs/grading_roadmap.md` breaks that direction into implementation phases and acceptance criteria.

## Verification

```bash
python -m unittest discover -s tests -p 'test_*.py'
python -m unittest src.pipeline.msplitter.tests.test_markers
python -m py_compile $(find src tests -path '*/__pycache__/*' -prune -o -name '*.py' -print)
```

For corpus-level checks, run into a temporary output directory first:

```bash
python -m src.pipeline.runners.qsplitter_batch \
  --pdf-dir resources/pdfs/cs_papers \
  --ocr-dir resources/ocr/surya_output \
  --marker-dir normalize/normalized_marker_output \
  --output-dir /tmp/pseudocode_solving_prod_audit/qp_output
```

## Maintenance Notes

- `src.pipeline.parser.qsplitter` keeps compatibility modules for `geometry`,
  `io`, `markers`, and `type_definitions`; the shared implementations live in
  `src.pipeline.msplitter`.
- `src/pipeline/parser/qsplitter/extract_question_text.py` and
  `src/pipeline/pseudocode_tools/classify_pseudocode.py` are legacy standalone
  helpers. The current production path uses `segmented_questions.json` plus
  `select_pseudocode_writing.py`.
- `select_pseudocode_writing.py` matches every question/subpart level. Because a
  question node's `content_text` concatenates its subparts, a pseudocode-writing
  subpart also makes the whole question match; the selector supersedes such
  ancestors (written to `pseudocode_writing_superseded.json`) so only the specific
  pseudocode subpart is graded and the whole question remains as context.
- Mark-scheme parsing is table-first. A full audit on the checked-in corpus
  leaves some older 2015/2016 mark schemes with empty question lists; treat that
  as parser coverage work, not as a hidden fallback path.
