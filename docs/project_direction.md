# Project Direction

## Purpose

This project is a pipeline for building a Cambridge Computer Science pseudocode-question corpus and using it as the foundation for automated grading.

The near-term job is extraction:

1. Read Cambridge question-paper PDFs, OCR output, Marker layout JSON, and mark-scheme PDFs.
2. Split question papers into a stable hierarchy of questions, primary subparts, and secondary subparts.
3. Extract the text and source bounding boxes for each segment.
4. Select the segments where students are asked to write pseudocode or program code.
5. Match those question-paper segments to mark-scheme entries.
6. Extract mark-scheme marking points where they are written as MP-style rubric points.
7. Render screenshots where text extraction is not enough or where visual review is needed.

The long-term job is grading:

1. Parse student pseudocode/program-code submissions into an AST.
2. Parse example solutions from mark schemes into ASTs when they are present.
3. Send the model a structured grading packet containing the question text, mark-scheme points, student AST, optional example ASTs, and source snippets.
4. Ask Qwen2.5 Coder 7b through OpenRouter to grade each marking point independently.
5. Return structured marks, rationale, uncertainty, and audit artifacts.

## Current System

### Inputs

The repository expects these corpus inputs:

- `resources/pdfs/cs_papers/`: Cambridge question-paper and mark-scheme PDFs.
- `resources/ocr/surya_output/`: OCR output in per-paper `results.json` folders.
- `legacy/marker_output/` or `normalize/normalized_marker_output/`: Marker layout output before or after coordinate normalization.

The code deliberately requires explicit input directories. It does not hide missing files behind root-level module shortcuts or loose fallbacks.

### Extraction Pipeline

The current production path is:

1. Normalize Marker output into OCR/PDF coordinate space with `src.pipeline.msplitter.normalize_marker_output`.
2. Build question-paper hierarchy and segment text with `src.pipeline.runners.qsplitter_batch` or `src.pipeline.parser.qsplitter`.
3. Parse mark schemes with `src.pipeline.msplitter.ms_parser`.
4. Select pseudocode-writing prompts with `src.pipeline.pseudocode_tools.select_pseudocode_writing`.
5. Export screenshots and enriched pseudocode records with the scripts under `src.pipeline.pseudocode_tools`.
6. Extract MP-style marking points with `src.pipeline.pseudocode_tools.extract_marking_points`.

### Question-Paper Parser

`src/pipeline/parser/qsplitter/` is responsible for question papers.

Important modules:

- `builder.py`: Loads paper context, extracts question/subpart/marks marker candidates, clusters marker columns, builds hierarchy, and writes output artifacts.
- `segmentation.py`: Converts hierarchy markers into segment text, content bounding boxes, per-page content slices, and word boxes.
- `cluster.py`: Clusters candidate markers by x-position to separate primary markers, secondary markers, and marks columns.
- `fitz_backend.py`: Uses PyMuPDF text extraction as the primary text source while preserving OCR page geometry.
- `debug.py` and diagnostics renderers: Emit reading-order and bbox review artifacts.

Key outputs per question paper:

- `hierarchy.json`: Marker-only question/primary/secondary structure.
- `segmented_questions.json`: Hierarchy plus `content_text`, `content_bbox`, `content_pages`, and `content_word_boxes`.

This layer is heuristic-heavy by design. It handles bold marker signals, page headers/footers, picture exclusions, same-line markers, old paper exceptions, page boundaries, and ambiguous `(i)` markers.

### Mark-Scheme Parser

`src/pipeline/msplitter/` is responsible for mark schemes and shared marker helpers.

Important modules:

- `ms_parser.py`: Uses PyMuPDF table detection, reconstructs Question/Answer/Marks rows, builds a question hierarchy, and writes mark-scheme outputs.
- `markers.py`: Shared routines for detecting leading question numbers, parenthetical subparts, bracketed marks, math-tag markers, and exclusion regions.
- `normalize_marker_output.py`: Scales Marker geometry into OCR image coordinates.
- `type_definitions.py`: Shared typed dictionaries for OCR pages, text lines, candidates, exclusions, contexts, and hierarchy payloads.

Key outputs per mark scheme:

- `mark_scheme.json`: Parsed table rows, hierarchical questions, answer text, marks text, marks values, word boxes, and spans.
- `hierarchy.json`: Cleaned mark-scheme hierarchy.

Known gap: the mark-scheme parser is table-first. Older 2015/2016 mark schemes can produce empty question lists or unmatched entries. Treat this as parser coverage work, not as a reason to reintroduce stale hidden fallbacks.

### Pseudocode Selection And Review

`src/pipeline/pseudocode_tools/` narrows extracted questions to the grading target.

Important modules:

- `select_pseudocode_writing.py`: Current production selector. It uses positive and negative regex rules against `segmented_questions.json` and emits selected, review, rejected, and full record JSON.
- `classify_pseudocode.py`: Legacy keyword-scoring classifier kept for comparison with older runs.
- `export_pseudocode_writing_hits.py`: Exports paper-2 selected segments with cropped images.
- `export_pseudocode_full_questions.py`: Exports full paper-2 questions when every required subpart is a pseudocode-writing prompt.
- `render_pseudocode_question_screenshots.py`: Renders selected segments and full question context from stored bboxes.
- `extract_marking_points.py`: Extracts MP-style marking points from matched mark-scheme answer text.

The generated `pseudocode_writing_hits/pseudocode_writing_final_qp_ms_marking_points.json` currently contains a useful joined artifact:

- 270 retained records.
- 50 question papers.
- 140 primary records, 88 question records, and 42 secondary records.
- 270 selected-segment screenshots and 270 context screenshots rendered.
- 9 records with extracted marking points and 261 without MP extraction.

The low marking-point coverage is an important next-stage signal: MP extraction needs to support more mark-scheme styles before model grading can be broadly reliable.

### Rust Pseudocode Parser

The root Rust files are the current compiler/parser surface:

- `ast.rs`: Defines AST nodes for expressions, statements, file modes, binary expressions, type definitions, case conditions, and blocks.
- `parser.rs`: Parses tokens into AST nodes for expressions, assignment, declarations, constants, input/output, loops, case, procedures, functions, calls, file I/O, array types, and type declarations.

This parser is already more than a sketch. The future work is to expose it as a stable service or CLI that can return machine-readable AST JSON and diagnostics to the Python pipeline.

## Target Architecture

The target architecture should separate five responsibilities:

1. Corpus extraction
   - Question-paper segmentation, mark-scheme parsing, pseudocode selection, screenshots, and provenance.
2. Rubric extraction
   - Marking-point extraction, marks totals, example solution capture, and rubric normalization.
3. Pseudocode parsing
   - Student solution parsing and optional mark-scheme solution parsing into AST JSON.
4. Grading packet assembly
   - A deterministic JSON packet for each student answer and rubric item.
5. Model grading
   - OpenRouter/Qwen calls, point-by-point decisions, evidence, retry logic, and audit output.

The AST should become the shared contract between parser/compiler work and model grading. Text and screenshots remain important as fallback context and audit evidence, but the grader should not depend only on OCR text when ASTs are available.

## Future Direction

### 1. Stabilize Corpus Records

Define a canonical `PseudocodeQuestionRecord` schema that joins:

- Paper code and mark-scheme paper code.
- Question/primary/secondary markers.
- Stable segment ID.
- Question text.
- Parent question context text.
- Segment screenshots and context screenshots.
- Mark-scheme answer text.
- Mark-scheme marks value.
- Extracted marking points.
- Source bboxes, pages, and word boxes.

The existing final JSON is close to this but is generated by ad hoc workflow steps. Make the join and final export a first-class script with tests.

### 2. Improve Marking-Point Extraction

The MP extractor currently handles explicit `MP1`, `MP2`, ranges, and simple numbered lists after "mark as follows". Future extraction should also handle:

- Bullet lists without explicit MP labels.
- Mark schemes where the marks column has the mark total but the answer column contains implicit point bullets.
- Pseudocode examples followed by prose guidance.
- Alternative answers and max-mark constraints.
- Carry-forward and independent/dependent marking relationships.

Each extracted marking point should have an ID, text, marks value, source span, confidence, and source node.

### 3. Turn Rust Parser Into A JSON AST Provider

Modify the Rust code so it can be called from the Python pipeline.

Minimum interface:

```text
pseudocode-parser --format json --source-file answer.txt
```

Expected output:

```json
{
  "ok": true,
  "ast_version": "cambridge-pseudocode-ast/v1",
  "source_kind": "student_answer",
  "statements": [],
  "diagnostics": []
}
```

On parse failure:

```json
{
  "ok": false,
  "ast_version": "cambridge-pseudocode-ast/v1",
  "statements": [],
  "diagnostics": [
    {
      "severity": "error",
      "message": "Expected ENDIF after if statement",
      "line": 12,
      "column": 1
    }
  ]
}
```

Implementation implications:

- Add `serde` derives or explicit serializers for AST, expressions, statements, types, and diagnostics.
- Preserve source spans wherever possible.
- Keep a stable AST version string.
- Distinguish parser failure from subprocess failure.
- Add golden tests for common Cambridge pseudocode constructs.

### 4. Parse Student And Example Solutions

Student submitted code should be normalized and parsed before model grading.

Pipeline:

1. Normalize OCR/manual-entry quirks and Cambridge pseudocode variants.
2. Run the Rust parser.
3. Store AST JSON plus diagnostics.
4. If parsing fails, still grade with text fallback, but label the parse failure in the grading packet.

Mark-scheme example solutions should use the same parser:

1. Detect code-like blocks inside `ms_entry.answer_text`.
2. Extract candidate example solution text.
3. Parse each candidate into AST.
4. Attach successful ASTs to the grading packet.

### 5. Build Model Grading Around Marking Points

The model should not produce a single opaque grade. It should judge each marking point independently.

For each marking point, send:

- Marking point ID and text.
- Question text and parent context.
- Student answer text.
- Student AST JSON.
- Optional mark-scheme example solution text and AST JSON.
- Relevant mark-scheme notes.
- Instructions to return strict JSON only.

Expected grading output:

```json
{
  "record_id": 123,
  "student_answer_id": "submission-abc",
  "total_awarded": 4,
  "max_marks": 6,
  "points": [
    {
      "marking_point_id": "mp1",
      "awarded": true,
      "marks_awarded": 1,
      "confidence": "high",
      "evidence": "Student initializes OutString before the loop.",
      "concerns": []
    }
  ],
  "model": "qwen/qwen2.5-coder-7b-instruct",
  "provider": "openrouter"
}
```

### 6. Add Evaluation Before Automation

Before trusting model marks, build a small reviewed set:

- 30 to 50 selected pseudocode questions across old and new syllabuses.
- At least 3 student answers per question: correct, partially correct, and flawed.
- Human marking-point decisions.
- Parser outcome for each answer.
- Model output comparison.

Track exact-match per marking point, total-mark error, parse failure rate, and examples where screenshots/text were required.

## Design Principles

- Keep extraction deterministic. The model should not decide where a question starts or which mark-scheme entry matches.
- Keep provenance. Every text field used for grading should point back to paper, page, bbox, and source artifact.
- Prefer AST for code semantics, but retain text and screenshots for ambiguous OCR, diagrams, incomplete code, and examiner wording.
- Treat mark-scheme points as the grading unit, not whole questions.
- Treat model output as auditable evidence, not an unstructured answer.
- Version every cross-component schema: extraction record, AST JSON, grading packet, and grading result.

## Immediate Priorities

1. Create a first-class final record builder that joins selected qsplitter records to mark-scheme entries and screenshots.
2. Expand marking-point extraction and report coverage by paper, question, and mark-scheme style.
3. Add AST JSON serialization to the Rust parser.
4. Add a Python adapter that invokes the Rust parser and attaches AST results to records.
5. Define and test grading packet JSON.
6. Add an OpenRouter client behind a dry-run/testable interface.
7. Build a reviewed evaluation set before enabling bulk grading.

