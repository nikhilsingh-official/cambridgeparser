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

Audit marking-point quality (read-only; a severity-ranked scope baseline and
regression gate for grading-safety of the extracted marking points):

```bash
python -m src.pipeline.analysis.diagnostics.validate_marking_points \
  --records pseudocode_writing_hits/pseudocode_question_records.json \
  --output-json pseudocode_writing_hits/marking_point_validation.json
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

Evaluate grading quality against hand-authored answers (15 questions across
fill-in / short / long types, each with high/medium/low candidates and the marks
a human examiner would award). Dry-run without a key only exercises the harness;
set `OPENROUTER_API_KEY` to measure how closely Qwen tracks the predicted marks:

```bash
python -m src.pipeline.grading.eval \
  --records pseudocode_writing_hits/pseudocode_question_records.json \
  --output-json pseudocode_writing_hits/grading_eval_results.json
```

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
- Cambridge mark schemes often print several *alternative* solutions for one
  question. `extract_structured_marking_points` tags each point with an
  `alt_group` (a new group opens only when the rubric numbering restarts, so an
  aside like "ALTERNATIVE using nested IFs:" does not split a list), and
  deduplicates only *within* a group. The grading prompt lists the groups as
  separate, mutually exclusive blocks — they are never merged into one additive
  list — and `apply_max_marks_cap` clamps `total_awarded` to the question's
  marks as a final safety net. `validate_marking_points` counts per group for
  the same reason.
- A "one mark per underlined part" header or declaration usually arrives as a
  single continuous underlined run — the styling never changes across it, so the
  PDF offers no sub-span structure — even though it carries several marks. When
  merging cannot reach the mark total (it only ever reduces), the run is divided
  at the declaration's own syntax breaks: the `RETURNS` clause, then each
  parameter, then the `OF` of an array type. Splitting is skipped when any
  alternative group already has its marks, so a supplementary `VB:`/`Pascal:`
  restatement is not split as if it were the whole question.
- The code guard that skips example-solution lines is relaxed for items that
  continue a rubric list's numbering (and for bullets under a header), because
  marking points routinely *name* the construct they mark — "FOR loop", "CASE OF
  ThisMark ... ENDCASE", "OUTPUT statement". Out-of-sequence numbers still face
  the guard, so circled mark digits printed inside the example code are rejected.
- A few mark schemes number points 1-7 then print the eighth flush-left with no
  "8." (verified against the rendered PDF and the OCR — the number is absent from
  the source, not dropped in extraction). That flush-left line is indistinguishable
  from a wrapped description by position, so the extractor attaches it and comes
  up one point short. This is a mark-scheme formatting error, not a parsing
  problem, so the four affected records (`9608_w17` q5(a) papers 21/23, `9618_w21`
  q6(b) papers 21/23) are transcribed in `marking_point_overrides` with
  `replaces_parse` rather than reconstructed by a heuristic that guesses which
  wraps are really lost items.
- Some schemes list more criteria than marks ("One mark per point (Max 8):" above
  nine items). That cap is recorded as `marking_points_max`, enforced by the
  grading layer, and reported by the audit as `declared_max_list` rather than as
  an extraction defect. The cap is also written without a bracket — "Note: Max 7
  marks" on a trailing line, or "Mark as follows Max 6 marks:" above the list —
  and a bare "Max n" is only read as a cap on a line that is *about* the marking,
  never inside a marking point ("compare with Max 255"). "Note: Max 7 if
  CharCount not used" is a conditional penalty, not a cap, so it is ignored.
- Three papers over-list without declaring any cap at all (10 criteria for [8]
  marks, MP1-MP8 for [7]). Their points were read against the mark scheme by hand
  and are correct, so they are named in `_VERIFIED_OVER_LIST` and audited as
  `verified_over_list`. That set is an *annotation*, not an override: it supplies
  no marking points, so those records still track the extractor as it improves.
- When a scheme declares that its marks *are* the styled spans ("One mark for
  each part-statement, shown underlined and bold"), the underline recovery wins
  over any text list found in the same cell. On a few 2016 papers a mark-scheme
  row spans a page break and swallows the next question's rubric, and that
  foreign list would otherwise be extracted as the answer's marking points.
- `marking_point_overrides` entries normally apply only when nothing parsed. An
  entry may set `replaces_parse` to win over a *bad* parse, for schemes whose
  marks live in a layout the scanner cannot read (an expression table, a
  highlight convention, bold gaps tagged with inline `MP n`). That flag silences
  the extractor for the record permanently, so it stays rare and justified.
- `ms_parser` records underlined answer spans (`answer_underlined_spans`) via
  PyMuPDF `TEXT_COLLECT_STYLES` (`char_flags & 2`). `build_final_records` turns
  them into marking points for the "one mark per underlined word / expression"
  schemes when no text rubric exists, using the node's mark value to decide how
  finely to split runs (`marking_points_from_underlined_spans`).
