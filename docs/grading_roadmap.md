# AST-Based Grading Roadmap

## Goal

Build an end-to-end system that grades Cambridge pseudocode answers by combining deterministic extraction, Rust AST parsing, mark-scheme marking points, and model reasoning through Qwen2.5 Coder 7b on OpenRouter.

The intended grading flow is:

```text
PDF/OCR/Marker inputs
  -> qsplitter question segments
  -> msplitter mark-scheme hierarchy
  -> pseudocode-writing selection
  -> final question + mark-scheme records
  -> student answer ingestion
  -> Rust AST parsing
  -> grading packet assembly
  -> OpenRouter model call
  -> point-by-point marks and audit output
```

## Phase 0: Baseline The Current Corpus

Deliverables:

- Document current corpus counts from `qp_output`, `ms_output`, and `pseudocode_writing_hits`.
- Add a script that validates final records:
  - every retained record has a question-paper segment;
  - every retained record has a mark-scheme entry;
  - screenshot paths exist where expected;
  - `marks_value` is present when the mark scheme exposes one;
  - marking-point coverage is reported.
- Store validation output as JSON and a concise Markdown report.

Acceptance criteria:

- The final record count and discarded count are reproducible from source artifacts.
- Missing screenshots and missing mark-scheme matches are reported with record IDs.
- The validation can run without calling any model or network service.

## Phase 1: Make Final Record Assembly First-Class

Current state:

- The checkout contains joined generated files such as `pseudocode_writing_final_qp_ms_context.json`.
- The scripts can select pseudocode questions, render screenshots, and extract marking points.
- The code path that creates the final joined record should be made explicit and tested.

Deliverables:

- `src.pipeline.pseudocode_tools.build_final_records` or equivalent.
- Canonical schema for `PseudocodeQuestionRecord`.
- Unit tests for matching:
  - question-level records;
  - primary subpart records;
  - secondary subpart records;
  - discarded records where QP or MS nodes are missing;
  - legacy 9608 and newer 9618 paper codes.

Suggested record shape:

```json
{
  "schema_version": "pseudocode-question-record/v1",
  "id": 1,
  "paper_code": "9618_w25_qp_21",
  "ms_paper_code": "9618_w25_ms_21",
  "segment_key": {
    "question_marker": "3",
    "primary_marker": "(a)",
    "secondary_marker": null,
    "segment_kind": "primary"
  },
  "question_text": "...",
  "question_context_text": "...",
  "mark_scheme": {
    "answer_text": "...",
    "marks_text": "6",
    "marks_value": 6,
    "marking_points": []
  },
  "provenance": {
    "qp_pages": [],
    "ms_pages": [],
    "screenshots": {}
  }
}
```

Acceptance criteria:

- The final record builder can regenerate the final JSON from selected records, `qp_output`, and `ms_output`.
- The generated schema is documented and versioned.
- The builder does not depend on hand-edited generated JSON.

## Phase 2: Improve Rubric Extraction

Current state:

- `extract_marking_points.py` extracts explicit MP labels and some numbered lists.
- In the sampled generated artifact, only 9 of 270 records have marking points.

Deliverables:

- `MarkingPoint` schema:

```json
{
  "id": "mp1",
  "text": "Initialise the return string",
  "marks": 1,
  "source": {
    "paper_code": "9618_w25_ms_21",
    "question_key": "q3|(a)",
    "field": "answer_text",
    "page_index": 4,
    "bbox": null
  },
  "confidence": "high",
  "relationships": []
}
```

- Extraction support for:
  - `MP1` / `MP 1` / `M1` variants;
  - MP ranges such as `MP1 to MP3`;
  - explicit numbered lists;
  - bullet lists under answer text;
  - "max" caps and alternative groups;
  - code examples plus explanatory prose.
- Coverage report by paper and by parser pattern.

Acceptance criteria:

- Rubric extraction coverage materially improves on the 270-record generated set.
- Low-confidence or implicit points are flagged for review instead of silently accepted.
- Each marking point has a stable ID and source field.

## Phase 3: Expose Rust AST JSON

Current state:

- `ast.rs` defines AST structs/enums for expressions, statements, blocks, file I/O, and type definitions.
- `parser.rs` parses token streams into those AST nodes.
- The AST currently has debug/prefix output but no stable JSON API in this checkout.

Deliverables:

- Add `serde::Serialize` support or explicit serializers.
- Add AST schema versioning.
- Add a CLI or library boundary callable from Python.
- Return parse diagnostics in JSON.
- Add Rust golden tests for Cambridge pseudocode examples.

Suggested CLI:

```bash
pseudocode-parser --format json --source-file answer.txt
```

Suggested success output:

```json
{
  "ok": true,
  "ast_version": "cambridge-pseudocode-ast/v1",
  "statements": [],
  "diagnostics": []
}
```

Suggested failure output:

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

Acceptance criteria:

- Python can call the parser on a text file and receive JSON.
- Parser failures are represented as data, not as crashes.
- AST JSON is deterministic for equivalent source.
- AST fields are stable enough for prompt construction and future evals.

## Phase 4: Add Python Parser Adapter

Deliverables:

- `src.pipeline.pseudocode_tools.parse_submissions` or equivalent.
- Adapter that runs the Rust parser with timeout and captures:
  - stdout JSON;
  - stderr;
  - exit code;
  - duration;
  - parser version;
  - normalized source text.
- Storage schema for `ParsedAnswer`.

Suggested shape:

```json
{
  "schema_version": "parsed-answer/v1",
  "student_answer_id": "answer-001",
  "record_id": 1,
  "source_text": "...",
  "normalization": {
    "rules_applied": []
  },
  "parse": {
    "ok": true,
    "ast_version": "cambridge-pseudocode-ast/v1",
    "ast": {},
    "diagnostics": []
  }
}
```

Acceptance criteria:

- The adapter has tests for success, parser error, invalid JSON, timeout, and missing parser binary.
- The rest of the grading pipeline can consume `ParsedAnswer` without knowing process details.

## Phase 5: Extract And Parse Mark-Scheme Example Solutions

Deliverables:

- Code-block detection in mark-scheme `answer_text`.
- Example solution extraction with confidence.
- Rust parsing for extracted examples.
- Attachment of example text and ASTs to final records.

Acceptance criteria:

- Example ASTs are included only when extracted with enough confidence.
- Failed example parses remain visible as diagnostics.
- The model packet can include zero, one, or many example solution ASTs.

## Phase 6: Build Grading Packets

Deliverables:

- `GradingPacket` schema.
- Packet builder that combines:
  - `PseudocodeQuestionRecord`;
  - `ParsedAnswer`;
  - optional parsed mark-scheme examples;
  - marking-point list;
  - text and screenshot references.

Suggested shape:

```json
{
  "schema_version": "grading-packet/v1",
  "record_id": 1,
  "student_answer_id": "answer-001",
  "question": {
    "text": "...",
    "context_text": "..."
  },
  "rubric": {
    "max_marks": 6,
    "marking_points": []
  },
  "student_answer": {
    "source_text": "...",
    "ast": {},
    "parse_diagnostics": []
  },
  "examples": [],
  "provenance": {}
}
```

Acceptance criteria:

- Packet generation is deterministic.
- Packets are valid JSON and small enough for the target model context window.
- Missing ASTs or missing marking points are explicit packet states.

## Phase 7: Add OpenRouter Grading Client

Deliverables:

- OpenRouter client behind a testable interface.
- Environment-based configuration for API key and model name.
- Dry-run mode that writes packets without network calls.
- Strict JSON response validation.
- Retry policy for transient failures.
- Persisted raw request/response metadata for audit.

Default model target:

```text
qwen/qwen2.5-coder-7b-instruct
```

The exact OpenRouter model ID should be configurable because provider model names can change.

Acceptance criteria:

- Unit tests mock the client.
- Invalid model JSON is rejected and stored for review.
- The grader can run on a small fixture set without touching the full corpus.

## Phase 8: Evaluate Before Bulk Use

Deliverables:

- Human-reviewed evaluation set.
- Metrics:
  - marking-point exact match;
  - total-mark absolute error;
  - over-award rate;
  - under-award rate;
  - parse success rate;
  - rubric extraction coverage;
  - model invalid JSON rate.
- Error taxonomy:
  - extraction error;
  - rubric error;
  - parser error;
  - model reasoning error;
  - prompt/schema error.

Acceptance criteria:

- The system can explain whether a wrong grade came from extraction, parsing, rubric extraction, or model judgment.
- Bulk grading is gated behind an evaluation report.

## Key Risks

- OCR and segmentation errors can cause the model to grade the wrong prompt.
- Mark-scheme answer text often mixes examples, alternatives, and notes instead of clean MP lines.
- Some valid student answers may not parse cleanly until the Rust parser accepts enough Cambridge pseudocode variants.
- AST-only grading can miss examiner intent; text and screenshots should remain available.
- Model output must be schema-validated and auditable.
- OpenRouter model identifiers and behavior can change; keep model selection configurable.

## Recommended Next Ticket Order

1. Build and test final record assembly.
2. Add corpus validation and coverage reporting.
3. Expand marking-point extraction.
4. Add Rust AST JSON serialization.
5. Add Python parser adapter.
6. Build grading packet schema and fixtures.
7. Add OpenRouter dry-run and mocked client.
8. Run a small human-reviewed evaluation set.

