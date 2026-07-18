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
- Mark-scheme parsing is table-first. A full audit on the checked-in corpus
  leaves some older 2015/2016 mark schemes with empty question lists; treat that
  as parser coverage work, not as a hidden fallback path.
