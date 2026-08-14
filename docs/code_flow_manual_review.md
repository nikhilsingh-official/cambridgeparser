# Code Flow Manual Review Guide

This document is written for a manual review of code that was heavily AI-assisted. It describes how data moves through the repository, what each source file owns, and what the important functions/classes do. It focuses on maintained source code under `src/`, the Rust parser wrapper, and root parser files. Source PDFs/OCR live under `resources/`; parser-created corpus trees live under `resources/generated/` and are described by role rather than enumerated file-by-file.

## End-To-End Flow

The repository builds a Cambridge Computer Science pseudocode-question corpus and uses it for review/grading.

```text
PDFs + OCR + Marker layout JSON
  -> normalize Marker coordinates
  -> split question papers into question/subpart segments
  -> parse mark-scheme tables into answer/marks hierarchy
  -> select pseudocode-writing prompts
  -> join QP segment + MS answer + marking points into canonical records
  -> optionally render screenshots/layouts for review
  -> parse student answer with Rust parser
  -> grade point-by-point through OpenRouter, or dry-run without API key
  -> view/debug in stdlib web app
```

The main production commands are:

```bash
python -m src.pipeline.msplitter.normalize_marker_output --all \
  --marker-output-dir resources/generated/marker_output \
  --ocr-dir resources/ocr/surya_output \
  --normalized-output-dir resources/generated/normalized_marker_output

python -m src.pipeline.runners.qsplitter_batch \
  --pdf-dir resources/pdfs/cs_papers \
  --ocr-dir resources/ocr/surya_output \
  --marker-dir resources/generated/normalized_marker_output \
  --output-dir resources/generated/qp_output

python -m src.pipeline.msplitter.ms_parser \
  --pdf-dir resources/pdfs/cs_papers \
  --marker-dir resources/generated/normalized_marker_output \
  --output-dir resources/generated/ms_output

python -m src.pipeline.pseudocode_tools.select_pseudocode_writing \
  --segments resources/generated/qp_output \
  --output-dir resources/generated/pseudocode_writing_hits \
  --rules-file src/pipeline/analysis/diagnostics/pseudocode_custom_rules.json

python -m src.pipeline.pseudocode_tools.build_final_records \
  --selected-json resources/generated/pseudocode_writing_hits/pseudocode_writing_selected.json \
  --qp-dir resources/generated/qp_output \
  --ms-dir resources/generated/ms_output \
  --screenshots-dir resources/generated/pseudocode_writing_hits/pseudocode_question_screenshots \
  --output-json resources/generated/pseudocode_writing_hits/pseudocode_question_records.json
```

## Data Contracts

The code mostly passes JSON dictionaries rather than dataclasses. Review should pay special attention to field names and coordinate spaces.

- OCR input: `resources/ocr/surya_output/<paper>/results.json`, keyed by paper code, where each page has `image_bbox` and `text_lines`.
- Marker input: `resources/generated/normalized_marker_output/<paper>/<paper>.json`, whose page/block `bbox` values have been scaled into the same image coordinate system as OCR.
- Question-paper output: `resources/generated/qp_output/<paper>/hierarchy.json` and `segmented_questions.json`.
- Mark-scheme output: `resources/generated/ms_output/<ms_paper>/mark_scheme.json` and `hierarchy.json`.
- Selection output: `pseudocode_writing_selected.json`, `review`, `rejected`, `superseded`, and rule report JSON files.
- Canonical final output: `pseudocode-question-record/v1` in `resources/generated/pseudocode_writing_hits/pseudocode_question_records.json`.
- Student parse output: `parsed-answer/v1` from `src.pipeline.grading.ast_adapter`.
- Grading output: `grading-result/v1` from `src.pipeline.grading.openrouter_client`.

Coordinate assumption: most Python extraction/review code expects the normalized 794x1123-ish image space, not raw PDF points. PyMuPDF rendering functions explicitly scale between PDF points and that image space.

## High-Risk Review Areas

- Coordinate transforms: `normalize_marker_output`, qsplitter `fitz_backend`, `ms_parser._scale_bbox_between_spaces`, screenshot renderers, and web figure rendering.
- Marker heuristics: bold detection, header/footer exclusion, page-0 exclusion, ambiguous `(i)` as alpha vs roman, same-line marker tolerance, and hard-coded exclusion overrides.
- Table parsing: `ms_parser` relies on PyMuPDF table detection and rebuilds text from deduplicated characters to handle fake-bold double rendering.
- Record joining: `build_final_records` matches QP and MS nodes by normalized marker strings; failures are discarded with reasons.
- Marking-point extraction: rubric formats vary heavily. Manual overrides are intentionally narrow and should stay justified.
- Legacy paths: `extract_question_text.py`, `classify_pseudocode.py`, and some screenshot/export scripts consume older payload shapes.

## Repository Top Level

- `README.md`: current workflow, commands, grading stack notes, and maintenance notes.
- `requirements.txt`: Python runtime dependencies: PyMuPDF, Pillow, pylatexenc.
- `AGENTS.md`: repo instructions for coding style, tests, structure, and security.
- `ast.rs`: root Rust AST definitions used by the parser crate through `#[path]`.
- `parser.rs`: root Rust parser implementation used by the parser crate through `#[path]`.
- `prompt.md`: prompt/reference material; not read by the main pipeline.
- `docs/`: design and roadmap docs. This file belongs here.
- `src/`: Python pipeline package.
- `src/resources/`: shared filesystem defaults for source and generated resources.
- `src/website/`: website frontend for generated pseudocode-question resources.
- `resources/generated/`: ignored parser-created artifacts consumed by the website.
- `pseudocode-parser/`: Cargo crate that wraps the root Rust parser with lexer, CLI, JSON output, and tests.
- `tests/`: Python `unittest` coverage for parser/selection/grading/webapp helpers.

## Resource Helpers: `src/resources`

- `paths.py`: canonical defaults for source inputs and generated artifacts.
- `question_segments.py`: public helpers for locating QP question and subpart
  nodes inside generated `segmented_questions.json` payloads.

## Question-Paper Splitter: `src/pipeline/parser/qsplitter`

### Flow

`process_paper()` is the normal entry point. It:

1. Loads one paper through `load_paper_context()`.
2. Extracts candidate question, subpart, and marks markers.
3. Builds a hierarchy with `build_hierarchical_structure()`.
4. Writes `hierarchy.json`.
5. Uses `segmentation.build_segmented_questions()` to attach text, per-page bboxes, and word boxes.
6. Writes `segmented_questions.json`.
7. Optionally writes reading-order/debug images.

### `builder.py`

This is the main question-paper orchestration file.

- Constants such as `QUESTION_MARKER_MAX_X`, `SUBPART_MARKER_LEEWAY_VAL`, `MARKS_MARKER_LEEWAY`, `FITZ_TEXT_PRIMARY`, and `REQUIRE_BOLD_MARKERS`: corpus-tuned heuristics. Review changes here against a batch run because small shifts can reclassify content.
- `candidate_position(candidate)`: returns `(page_index, y, x)` for reading-order sorting.
- `_leading_nonempty_count(chars, upto_index)`: counts visible chars up to a marker to reject markers that are not near the start of a line.
- `marker_key(marker)`: builds a stable key from page and `line_id`; used to associate primaries and secondaries.
- `_build_candidate(...)`: creates the normalized candidate dictionary used throughout qsplitter.
- `_has_visible_digit_char(text_line)`: detects real digit glyphs; helps avoid treating math-rendered markers and actual digits as the same signal.
- `_marker_has_bold_signal(...)`: optionally requires marker chars to include a bold font signal when such metadata exists.
- `_marker_uses_monospace_font(...)`: detects Courier/monospace markers so code line numbers are not mistaken for question markers.
- `_extract_question_candidate_from_math_line(...)`: handles OCR `<math>` question numbers, requiring left-column position, bold signal, no visible digit glyph, and no exclusion-region hit.
- `_extract_question_candidate_from_digit_run(...)`: handles ordinary leading numeric markers, rejecting bracketed marks, code fonts, late-line digits, far-right digits, and excluded regions.
- `extract_question_candidates(data, excluded_bboxes_by_page, require_bold=None)`: scans all pages/lines for numeric question markers and returns them sorted.
- `extract_subpart_candidates(data, excluded_bboxes_by_page, require_bold=None)`: scans parenthesized markers such as `(a)` and `(i)`, classifies alpha/roman/ambiguous, applies bold/exclusion filters, and records right-edge `x` anchors for column clustering.
- `extract_marks_candidates(data, excluded_bboxes_by_page)`: finds `[n]` mark totals, allowing marks-like lines even in excluded regions when the line looks like a marks pattern.
- `split_subpart_candidates(question_candidates, subpart_candidates)`: clusters subpart candidates by x-position, decides primary vs secondary columns, resolves ambiguous `(i)`, and scopes subparts to the current question segment.
- `select_marks_candidates(marks_candidates)`: clusters right-side `[n]` markers and keeps the largest/rightmost marks column.
- `load_paper_context(paper_code, pdf_dir, ocr_dir, marker_dir)`: validates required input paths, loads OCR/Marker JSON, builds page text from PyMuPDF with OCR fallback, creates exclusion regions, applies paper-specific override drops, extracts candidates, and returns the `PaperContext`.
- `find_previous_marker(markers, target)`: finds the nearest preceding marker with same-line y tolerance.
- `build_hierarchical_structure(...)`: assigns primaries to previous questions and secondaries to previous primaries, then emits nested `questions -> primary_subparts -> secondary_subparts`.
- `build_output_payload(paper_code, pdf_dir, ocr_dir, marker_dir)`: env-var-compatible wrapper around hierarchy building.
- `process_paper(...)`: writes `hierarchy.json` and `segmented_questions.json`, with optional reading-order/debug artifacts.
- `process_all_papers(...)`: processes each per-paper marker directory and skips failures.

### `segmentation.py`

This file turns marker hierarchy into actual question content.

- Regex constants detect Cambridge running headers, page numbers, `[Turn over]`, blank pages, and copyright boilerplate.
- `_is_edge_noise_line(line, page_bounds)`: drops common header/footer/noise lines near page edges.
- `_marker_key(marker)`: key based on page, line id, and rounded bbox; used for end-boundary lookup.
- `_candidate_position(marker)`: returns marker position from bbox.
- `_marker_sort_key(marker)`: prefers line order when `line_id` exists, otherwise bbox order.
- `_collect_segment_markers(hierarchy_payload)`: flattens questions/primaries/secondaries with hierarchy levels.
- `_build_end_marker_map(hierarchy_payload)`: maps each marker to the next marker at the same or higher level; this is why a primary ends at the next primary/question rather than at its first secondary.
- `_combine_bboxes(bboxes)`: bounding union helper.
- `_page_bounds(data, page_index)`: returns image-space page bounds, or zero fallback.
- `_resolve_line_index(data, marker, page_index)`: maps a marker to a text-line index through `line_id` or y-position fallback.
- `_iter_lines_between(data, start_page, start_line, end_page, end_line)`: returns all lines between two marker line positions across pages.
- `_slice_line_text_and_words(...)`: filters chars in one line by x/y boundaries, page exclusions, top/bottom noise bands, and control-code noise; returns sliced text, word boxes, and content bbox.
- `_content_from_bounds(...)`: extracts visible text/words/content pages between a start marker and its end marker; stops at copyright boilerplate and tracks per-page bboxes.
- `_segment_page_bbox(...)`: computes the full-width vertical content band for one page of a segment.
- `_build_segment(...)`: attaches `content_bbox`, `content_text`, `content_source`, `content_pages`, and `content_word_boxes` to one marker.
- `build_segmented_questions(...)`: applies `_build_segment()` to every question, primary, and secondary node.

### `markers.py`

Compatibility re-export of `src.pipeline.msplitter.markers`. Qsplitter and msplitter intentionally share marker heuristics.

### `fitz_backend.py`

- `_span_is_bold(span)`: identifies bold spans from font name or PyMuPDF flags.
- `build_text_lines_from_fitz(pdf_page, image_bbox)`: reads raw PyMuPDF text chars, scales char/line bboxes into image space, and records bold/font metadata.
- `build_pages_from_fitz(pdf_path, image_bbox_by_page, ocr_pages=None)`: builds all qsplitter pages from PyMuPDF, falling back to OCR text lines for pages where PyMuPDF yields no text.

### `cluster.py`

- `cluster_candidates(candidates, leeway, x_key="x")`: groups marker candidates by similar x-position, computes cluster id/mean/std/quality, and writes `cluster_id` into each candidate.
- `select_column_clusters(clusters)`: picks the two strongest subpart columns and returns left/right cluster ids.
- `select_marks_cluster(clusters)`: picks the largest marks cluster, using rightmost x as tie-break.

### `debug.py`

- `write_reading_order_file(pages, output_path)`: writes every extracted text line with page/line/bbox/text for manual review.

### `cli.py`, `__main__.py`, `__init__.py`

- `cli.parse_args()`: defines `--paper`/`--all`, input dirs, output dir, and debug bbox flag.
- `cli.main()`: calls `process_paper()` or `process_all_papers()` and prints a summary.
- `__main__.py`: executes `cli.main()` for `python -m src.pipeline.parser.qsplitter`.
- `__init__.py`: exports qsplitter functions and lazy compatibility wrappers for mark-scheme parser functions.

### `extract_question_text.py`

Legacy helper kept for older `question_texts.json` experiments. The maintained path uses `segmented_questions.json`.

- `extract_text_from_bbox_fitz(...)`: clips text from a PDF bbox with PyMuPDF.
- `extract_text_from_ocr(...)`: parses old `reading_order.txt` output and returns lines overlapping a bbox.
- `_bbox_overlap(...)`: tolerance-based bbox overlap.
- `extract_text_from_bbox(...)`: tries PyMuPDF first, then OCR fallback.
- `extract_text_for_questions(...)`: legacy hierarchy-based text expansion for questions/primaries/secondaries.
- `batch_extract_all_papers(...)`: runs legacy extraction for every hierarchy file and writes `question_texts.json`.

### `geometry.py`, `io.py`, `type_definitions.py`

These are compatibility re-exports to the shared implementations in `src.pipeline.msplitter`. New shared geometry/type changes should be made in `msplitter`, not duplicated here.

## Mark-Scheme Splitter: `src/pipeline/msplitter`

### Flow

`process_mark_scheme_paper()` calls `parse_mark_scheme_paper()`, writes `mark_scheme.json`, then writes a cleaned `hierarchy.json`. The parser is table-first and uses PyMuPDF table detection rather than Marker text.

### `normalize_marker_output.py`

Normalizes raw Marker geometry into OCR image coordinates.

- `load_json(path)` / `write_json(path, document)`: local JSON helpers.
- `scale_point(point, source_page_bbox, target_page_bbox)`: maps one point from raw Marker page space to OCR image space.
- `scale_bbox(bbox, source_page_bbox, target_page_bbox)`: maps bbox corners through `scale_point()`.
- `normalize_geometry(node, source_page_bbox, target_page_bbox)`: recursively scales all `bbox` and `polygon` values in a subtree.
- `normalize_marker_document(marker_document, ocr_pages)`: normalizes every page of the main Marker document.
- `normalize_marker_meta(meta_document, marker_document, ocr_pages)`: normalizes meta output such as table-of-contents polygons.
- `normalize_paper(paper_code, marker_output_dir, ocr_output_dir, normalized_output_dir)`: normalizes one paper if both OCR and Marker inputs exist.
- `parse_args()` / `main()`: CLI for one paper or all papers.

### `markers.py`

Shared marker-detection utilities.

- `can_cast_to_int(x)`: broad int-conversion guard.
- `_latex_converter()` / `convert_latex_to_text()` / `replace_math_tags()`: optional pylatexenc support for OCR math tags.
- `find_prev_nonempty(chars, start_index)` / `find_next_nonempty(chars, start_index)`: locate visible neighboring chars.
- `is_bracketed_digit_run(chars, start_index, end_index)`: rejects `[1]`-style marks as question numbers.
- `extract_question_number_from_math_text(text_line)`: extracts a pure numeric question marker rendered as `<math>`.
- `classify_subpart_marker(marker_text)`: classifies `(a)` as alpha, `(iv)` as roman, and `(i)` as ambiguous.
- `extract_leading_question_number(chars)`: extracts a leading one/two-digit question marker with punctuation/spacing safeguards.
- `_has_following_alnum_before_whitespace(chars, start_index)`: rejects glued prefixes such as `1abc`.
- `_looks_like_question_prefix(prefix)`: allows subpart markers after a leading question number prefix.
- `extract_parenthetical_markers(text_line, chars)`: returns bbox-backed `(a)`/`(i)` marker candidates near line starts or after question prefixes.
- `extract_bracketed_marks(text_line, chars)`: returns bbox-backed `[n]` marks candidates.
- `looks_like_marks_pattern(line_text)`: identifies lines likely to contain marks.
- `_bbox_area()` / `_bbox_intersection_area()`: geometry helpers for exclusion overlap.
- `collect_marker_exclusion_bboxes(marker_document, excluded_types)`: builds per-page exclusion bboxes from Marker blocks, always excluding page 0.
- `is_in_excluded_region(char_bbox, excluded_bboxes)`: tests bbox against exclusions with overlap thresholds for picture/header/footer blocks.

### `ms_parser.py`

This is the mark-scheme table parser and hierarchy builder.

- `_render_table_debug_image(...)`: renders a PDF page with detected table rows/cells/columns overlaid for debugging.
- `parse_args()`: CLI args for paper, dirs, output, and debug images.
- `paper_year_from_code(paper_code)`: extracts `20xx` from Cambridge code.
- `_strip_html_text(value)`: normalizes Marker/PyMuPDF cell HTML/text to plain text.
- `_bbox_center_y()` / `_bbox_center_x()`: cell sorting helpers.
- `_combine_bboxes(bboxes)`: union of valid bboxes.
- `_bbox_intersection_width(left, right)`: horizontal-overlap score for column assignment.
- `_cluster_rows(cells, tolerance=6.0)`: groups table cells into visual rows by y-center.
- `_find_header_row_index(rows)`: picks the top row that looks like Question/Answer/Marks headers.
- `_infer_column_bboxes(header_row, table_bbox)`: infers question/answer/marks column regions from header cells or fallback ratios.
- `_assign_column(cell_bbox, col_bboxes)`: assigns a cell to the column with greatest horizontal overlap.
- `_page_visible_chars(page)`: collects non-empty page chars while removing fake-bold duplicate glyphs and preserving real spaces.
- `_region_text_from_chars(page_chars, bbox)`: reconstructs line-major text inside a bbox from deduplicated chars.
- `_fitz_table_to_cells(fitz_table, page)`: converts PyMuPDF table rows/cells to internal cell dicts with reconstructed text.
- `_extract_table_rows(table, page_index, table_index, fitz_page=None)`: turns a detected table into row records with question, answer, marks text and bboxes. Question-column cells define row boundaries; orphan answer/marks cells become continuation rows.
- `parse_question_marker(marker_text)`: parses full markers like `3(a)(ii)` into normalized key parts.
- `_parse_marks_value(marks_text)`: extracts numeric mark value, using the maximum number seen.
- `_split_marks_from_text(text)`: splits trailing `[n]` marks from text.
- `_combine_text(existing, addition)`: appends non-empty row text with newline separation.
- `_span_is_bold(font_name, flags)`: detects bold from PDF font metadata.
- `_bbox_intersects(left, right)`: bbox overlap.
- `_scale_bbox_between_spaces(bbox, source_page_bbox, target_page_bbox)`: maps bboxes between Marker/image and PDF coordinate systems.
- `_extract_pdf_font_metadata(pdf_document, page_index, bbox, marker_page_bbox=None)`: captures words, spans, bold flags, and underlined spans for a row region.
- `_marker_dict(...)`: builds normalized marker metadata.
- `_parse_marker_with_context(text, current_marker)`: resolves relative mark-scheme markers such as `(b)` or `(ii)` against the current question context.
- `_new_node(marker_text, parsed, row)`: creates one question/primary/secondary node with answer/marks/span accumulator fields.
- `_get_or_create_question_tree(questions_map, parsed, row)`: creates or finds the nested node corresponding to a parsed marker.
- `_append_row_to_node(node, row, answer_metadata, marks_metadata)`: appends row text, max mark value, content page info, word boxes, spans, and underline spans to a node.
- `_roman_to_int(value)`: roman-number sort helper.
- `_sort_question_entries(questions_map)`: sorts questions numerically, primaries alphabetically, secondaries by roman value, while removing internal maps.
- `_build_questions_from_rows(extracted_rows, pdf_document, page_bboxes_by_index)`: parses all rows into hierarchy, handles continuation rows, extracts PDF metadata, and returns unresolved rows separately.
- `_build_mark_scheme_hierarchy(mark_scheme)`: strips internal row/span fields to create a smaller `hierarchy.json`.
- `parse_mark_scheme_paper(paper_code, pdf_dir, marker_dir, debug_tables=False)`: opens the PDF, detects tables on each page, extracts rows, builds hierarchy, and returns the full mark-scheme payload.
- `resolve_pdf_path(paper_code, pdf_dir)`: tries direct, sibling shared, and default shared PDF locations.
- `iter_ms_papers(marker_dir)`: yields marker directories whose names contain `_ms_`.
- `process_mark_scheme_paper(...)`: writes `mark_scheme.json` and cleaned `hierarchy.json`.
- `process_all_mark_scheme_papers(...)`: processes every mark-scheme input directory, logging and skipping failures.
- `main()`: CLI dispatcher.

### `geometry.py`, `io.py`, `type_definitions.py`

- `geometry.combine_bboxes(bboxes)`: bbox union.
- `geometry.bbox_intersects(left, right)`: strict intersection test.
- `geometry.scale_pdf_bbox(pdf_bbox, pdf_rect, image_bbox)`: maps PDF points to image-space bbox.
- `io.load_json(path)` / `io.write_json(path, document)`: shared JSON helpers.
- `type_definitions.py`: `TypedDict` definitions for chars, text lines, pages, candidates, exclusions, contexts, and hierarchy payloads.

## Pseudocode Tools: `src/pipeline/pseudocode_tools`

### `select_pseudocode_writing.py`

Current production selector. It is phrase-first rather than keyword-score based.

- `DEFAULT_POSITIVE_RULES` / `DEFAULT_NEGATIVE_RULES`: regex rules for write-intent vs trace/explain/describe-style prompts.
- `parse_args()`: CLI args for segmented input path, output dir, optional rules JSON.
- `_load_rules(rules_file)`: merges default and custom positive/negative rules.
- `_compile_rules(patterns)`: compiles case-insensitive regexes.
- `_iter_segmented_files(path)`: yields one file or every `segmented_questions.json` under a directory.
- `_match_patterns(text, patterns)`: returns matched snippets for diagnostics.
- `_segment_record(...)`: classifies one segment as `selected`, `review`, or `rejected`.
- `_supersede_ancestors_with_selected_descendant(q_record, primary_groups)`: demotes question/primary hits when a more specific selected descendant exists.
- `_extract_records_from_payload(payload, positive_patterns, negative_patterns)`: classifies every question, primary, and secondary in one segmented payload.
- `_write_json(path, payload)`: writes indented JSON.
- `run_selection(...)`: processes all sources and writes selected/review/rejected/superseded/all-record reports.
- `main()`: CLI runner.

### `build_final_records.py`

Joins selected hits with authoritative QP/MS data and extracts marking points.

- `parse_args()`: CLI args for selected JSON, QP/MS dirs, screenshots dir, output path.
- `_load_json(path)` / `_write_json(path, payload)`: JSON helpers.
- `_norm_marker(value)`: lowercases and strips surrounding parentheses for matching.
- `ms_paper_code_for(paper_code)`: maps `_qp_` to `_ms_`.
- `_find_ms_question(ms_payload, question_marker)`: finds the matching MS question by parsed question number.
- `_find_ms_node(ms_question, segment_kind, primary_marker, secondary_marker)`: finds the exact MS node.
- `_aggregate_question_answer(ms_question)`: question-level fallback that aggregates subpart MS answers/marks when the question node itself is empty.
- `_qp_marks_value(question_text)`: extracts trailing `[n]` from question text.
- `_marker_slug(hit)`: creates screenshot-safe marker slug.
- `_find_screenshot(screenshots_dir, paper_code, slug, kind)`: locates pre-rendered selected/context screenshots.
- `_content_pages_summary(node)`: reduces QP content page provenance.
- `_ms_pages_summary(node)`: reduces MS row/page provenance.
- `build_records(selected_hits, qp_dir, ms_dir, screenshots_dir=None)`: core join. It caches QP/MS payloads, discards missing matches with reasons, extracts structured or underlined marking points, applies curated overrides, computes mark caps, builds `pseudocode-question-record/v1` records, and returns summary/discard metadata.
- `_count_by(items, key_fn)`: summary counter helper.
- `main()`: validates input shape, builds records, writes output, prints summary.

### `extract_marking_points.py`

Rubric parser for mark-scheme answer text.

- Regex constants define MP labels, numbered items, rubric headers, stop/meta boundaries, max-mark caps, code lines, and underline conventions.
- `parse_args()`: legacy CLI args for adding `marking_points` to older joined records.
- `_read_json()` / `_write_json()`: JSON helpers.
- `_normalize_marker(value)`: marker normalizer for legacy lookups.
- `_is_header(stripped)`: detects a rubric-list header.
- `_is_code_line(stripped)`: detects example solution code that should not become a marking point.
- `_mp_item(stripped)`: extracts a real `MPn` rubric item and rejects inline/cross-reference MP tokens.
- `_numbered_item(stripped, in_sequence=False)`: extracts numbered rubric items while guarding against code-line numbers.
- `_bullet_item(raw, in_list=False)`: extracts bullet rubric items, relaxing code guard under a header.
- `_scan_rubric_items(lines)`: single-pass scanner that creates provisional MP/numbered/bullet items, handles continuations, alternative groups, headers, stops, and numbering restarts.
- `_clean_item_text(text)`: removes annotation glyphs and normalizes whitespace.
- `_detect_max_marks(lines)`: extracts declared max caps from appropriate marking-context lines.
- `_extract_marking_points(text)`: legacy list-of-strings wrapper around structured extraction.
- `_select_items(items, header_seen)`: chooses the style that likely carries the rubric: MP labels, then numbered list, then bullets.
- `extract_structured_marking_points(text)`: main text-rubric extractor. Returns structured `{points, max_marks, alt_group_count}` with stable ids, confidence, style, and alternative group tags.
- `_clean_underline_text(text)`: replaces private-use pseudocode glyphs and cleans underlined span text.
- `declares_style_convention(answer_text)`: detects "one mark per underlined/bold/highlighted part" conventions.
- `_valid_span_bbox(bbox)`: validates span bbox shape.
- `_split_declarations(runs, parts)`: splits underlined declaration runs at `RETURNS`, commas, and `OF` syntax boundaries to reach target marks.
- `_comment_only_texts(answer_text)`: identifies underlined fragments that appear only inside comments and should be dropped.
- `_alt_boundary_lines(answer_text)`: detects answer lines that begin alternative solution groups.
- `marking_points_from_underlined_spans(spans, target_marks=None, line_tolerance=6.0, answer_text=None)`: converts PDF underline spans into marking points, merging/splitting based on visual lines, mark total, comments, and alternatives.
- `_find_primary_node(ms_entry, primary_marker)`, `_find_ms_node(record)`, `_apply_marking_points(records)`: legacy CLI helpers for older record shape.
- `main()`: legacy mutating CLI path.

### `marking_point_overrides.py`

Manual curated exceptions for one-off mark-scheme conventions.

- `_OVERRIDES`: per-record transcriptions. Most are fallback-only; entries with `replaces_parse` intentionally override a bad parse.
- `_VERIFIED_OVER_LIST`: records whose parsed list has more points than marks but was manually checked as correct.
- `_override_key(...)`: normalizes record key tuple.
- `is_verified_over_list(...)`: true when a record is annotated as verified over-listed.
- `override_marking_points(...)`: returns structured manual points plus optional max marks/replacement flag.

### `render_pseudocode_question_screenshots.py`

Renders selected/context screenshots from final-record bbox data. Some field names reflect an older record shape, so verify compatibility before using it with newly generated canonical records.

- `parse_args()`: CLI options for input JSON, PDFs, output dir, zoom, blank-page handling.
- `_read_json()` / `_write_json()`: JSON helpers.
- `_safe_marker()` / `_record_slug()`: file-safe naming helpers.
- `_marker_pages(marker)`: returns content pages or fallback bbox for a marker.
- `_iter_record_markers(record)`: yields selected/context markers from legacy record fields.
- `_infer_paper_canvas(records)`: infers render canvas size from bboxes.
- `_render_pdf_page(...)`: rasterizes one PDF page into the inferred image-space canvas.
- `_normalise_notice_text()` / `_page_has_centered_blank_notice()`: identify centered `BLANK PAGE` notices.
- `_scaled_bbox()` / `_clamp_bbox()`: zoom and clamp bbox to image bounds.
- `_draw_marker_highlight(...)`: draws a red marker rectangle inside a crop.
- `_is_blank_crop(...)`: pixel-ratio blank detector.
- `_stitch_chunks(chunks, label)`: vertically stitches multi-page crops with a label header.
- `_render_marker(...)`: renders one selected/context marker across pages, optionally skipping blank chunks.
- `render_screenshots(...)`: renders screenshots for all records, writes screenshot paths into the input JSON summary.
- `main()`: CLI runner.

### Export/Legacy Helpers

- `export_pseudocode_writing_hits.py`: exports paper-2 selected hits with cropped images.
  - `_paper2()`: detects paper 2 codes.
  - `_safe_text()`: filename-safe marker text.
  - `_clamp_bbox()`: validates crop bounds.
  - `export_hits(...)`: groups selected hits by paper, loads qsplitter context, renders/crops selected bboxes, and writes `hits.json` plus summary.
- `export_pseudocode_full_questions.py`: exports paper-2 questions where every subpart is selected.
  - `_selected_key()`, `_load_selected()`, `_segment_key()`: normalize selected-hit keys.
  - `_question_is_full(...)`: tests whether a question and all nested subparts are selected.
  - `export_full_questions(...)`: renders/crops full selected question/subpart pages and writes per-paper hit metadata.
- `classify_pseudocode.py`: legacy keyword scoring for older `question_texts.json`.
  - `count_pseudocode_keywords()`: weighted keyword count.
  - `find_starter_match()`: starter phrase detection.
  - `check_exclusion()`: excludes describe/explain/list-style prompts.
  - `classify_text()`: scores text as pseudocode-heavy or not.
  - `classify_question()`: applies text classifier to a question hierarchy.
  - `batch_classify_papers()`: writes classifications for old text extraction output.
  - `generate_summary_report()`: writes a text summary report.

## Diagnostics: `src/pipeline/analysis/diagnostics`

### `diagnostics.py`

Structural qsplitter diagnostics.

- `_bbox_area()` / `_bbox_intersection_area()` / `_find_exclusion_entry()`: exclusion-overlap helpers.
- `_strip_parens()` / `_alpha_index()` / `_roman_to_int()`: marker normalization and ordering helpers.
- `_is_consecutive()` / `_validate_consecutive()`: sequence validation helpers.
- `validate_question_order(questions, issues)`: checks top-level numeric question order.
- `validate_reading_order(markers, label, issues)`: checks marker list sort order.
- `primary_markers(question)` / `secondary_markers(primary)`: hierarchy accessors.
- `validate_hierarchy(hierarchy)`: validates non-empty hierarchy, question ordering, primary sequence, secondary roman sequence, and reading order.
- `validate_exclusion_anomalies(context, issues)`: detects large exclusion regions that may hide real markers.
- `run_diagnostics_for_paper(...)`: builds context/hierarchy and returns all issues.

### `debug_renderer.py`

Renders debug page images.

- `render_pdf_page(pdf_document, page_index, image_bbox)`: renders a page scaled to image space.
- `draw_labeled_bbox(draw, bbox, label, color, font)`: draws a labeled rectangle.
- `build_hierarchical_marks_map(context)`: associates `[n]` marks markers with nearest marker above on the same page.
- `_collect_segment_bbox_overlays(segmented_payload)`: collects segment content page bboxes for overlay mode.
- `write_debug_page_images(...)`: writes per-page debug PNGs for candidate markers/exclusions/marks or segment content boxes.

### `validate_extraction.py`

Read-only artifact validation.

- `iter_qp_segments(payload)`: yields all QP segment nodes.
- `validate_qp_dir(qp_dir, max_items)`: reports empty hierarchies, empty/short/garbage text, bad bboxes, and bad page refs.
- `iter_ms_nodes(payload)`: yields all MS hierarchy nodes.
- `validate_ms_dir(ms_dir, max_items)`: reports empty MS question lists, unresolved rows, garbage answers, missing answer/marks combinations.
- `_ms_matched_node(record)` / `_node_answer_text(record, node)`: legacy final-record resolution helpers.
- `validate_final_records(final_json, max_items)`: checks canonical or legacy final records for missing MS answers, marking points, screenshots, and question text.
- `build_report(...)`: combines QP/MS/final checks.
- `print_summary(report)`: console summary.
- `main()`: writes JSON report and prints summary.

### `validate_marking_points.py`

Read-only quality audit for final-record marking points.

- Pattern constants define high/medium/low flag families.
- `_alpha_count()`, `_count_rubric_headers()`, `_count_numbered_items()`, `_distinct_solution_names()`, `_by_alt_group()`: feature extraction helpers.
- `audit_record(record)`: assigns marking-point flags and severity for one record.
- `_flag_severity(flag)` / `_worst(a, b)`: severity helpers.
- `run(records_path)`: audits all records and returns counts plus sorted rows.
- `_print_report(report, limit)`: console table.
- `main()`: CLI runner.

### CLI Files

- `cli.py`: runs structural diagnostics for one paper.
- `debug_cli.py`: writes hierarchy, reading order, and debug images for one paper.
- JSON rule files: `pseudocode_refine_rules*.json` and `pseudocode_custom_rules.json` hold selection/refinement patterns.

## Grading: `src/pipeline/grading`

### `ast_adapter.py`

Python boundary around the Rust parser.

- `find_parser_binary()`: checks `PSEUDOCODE_PARSER_BIN`, release binary, then debug binary.
- `_failure_parse(message, hint)`: creates a structured parse failure block.
- `parse_answer(source_text, timeout=10.0, binary=None)`: runs the parser subprocess with stdin and `--format json`, captures timeout/nonzero/invalid JSON as data, and returns `parsed-answer/v1`.

### `openrouter_client.py`

OpenRouter/Qwen grading client.

- `OpenRouterConfig`: reads API key, model, and base URL from args/env; `has_api_key` controls dry-run default.
- `_default_transport(url, headers, body, timeout)`: stdlib POST implementation.
- `group_marking_points(marking_points)`: groups points by `alt_group`.
- `_group_marks(group)`: sums marks in one alternative group.
- `resolve_max_marks(record)`: chooses max mark cap from `max_marks`, `marks_value`, or best alternative group.
- `apply_max_marks_cap(result, cap)`: clamps model totals to the question maximum and annotates the result if capped.
- `build_grading_messages(record, parsed_answer)`: builds strict JSON grading prompt with question text, context, mark scheme, marking points, student source, AST, and diagnostics.
- `_extract_json_object(text)`: parses raw JSON or fenced JSON from model output.
- `validate_grading_payload(payload)`: schema checks model response.
- `dry_run_result(record, parsed_answer)`: deterministic fake grading result for local UI/testing without an API key.
- `grade_answer(record, parsed_answer, config=None, dry_run=None, transport=None, timeout=120)`: runs dry-run or OpenRouter call with retry on transient errors, validates response, applies cap, and returns `grading-result/v1`.

### `eval/__main__.py` and `eval/cases.py`

- `cases.py`: hand-authored grading eval cases. Tests require 15 cases across fill-in, short, and long answers, each with high/medium/low candidates.
- `_record_key(record)`: maps final record to case key.
- `run(records_path, parse_timeout)`: parses each candidate answer and grades it.
- `_summarise(results)`: computes exact/within-1/MAE/over/under summary.
- `_print_report(payload)`: prints a compact results table.
- `main()`: CLI runner with optional full JSON output.

## Web Review App: `src/website`

The web app is stdlib `http.server`, not a framework. It displays records, screenshots/layouts, marking points, answer input, parse JSON, and grading JSON.

### `app.py`

- `RecordStore.__init__(...)`: loads canonical records, indexes them by id, and creates Marker/QP layout caches.
- `RecordStore.first_id()`: returns the lowest record id.
- `RecordStore._load_qp(paper_code)`: lazy-loads `segmented_questions.json`.
- `RecordStore.layout_for(record)`: reconstructs page layout for a record from QP word boxes plus Marker figure/code regions.
- `RecordStore.figure_region(record, figure_index)`: resolves figure metadata for `/figure/<id>/<index>`.
- `_page(title, body)`: wraps HTML/CSS shell.
- `_marker_label(record)`: formats `Qn(a)(i)` from `segment_key`.
- `render_records_page(store)`: renders record list table.
- `_render_question_viewer(record, layout, has_selected_image)`: renders image-first viewer with optional selectable text mode and blank fields.
- `render_record_page(record, parser_available, layout=None)`: renders one full record page, marking points, answer textarea, and grading script.
- `GradingRequestHandler.log_message(...)`: suppresses normal access logs.
- `_send_html()` / `_send_json()`: response helpers.
- `_record_or_none(record_id)`: record lookup.
- `do_GET()`: routes `/`, `/records`, `/record/<id>`, `/screenshot/<id>/<kind>`, and `/figure/<id>/<index>`.
- `_serve_screenshot(record_id, kind)`: serves only screenshot paths recorded in the loaded JSON.
- `_serve_figure(record_id, figure_index)`: renders figure/table/code region crop from the PDF.
- `do_POST()`: routes `/record/<id>/grade`, validates answer JSON, runs parser and grader, returns combined JSON.
- `make_server(...)`: binds a `ThreadingHTTPServer` with injected store/config/timeout.

### `question_layout.py`

Reconstructs a selectable page layout from word boxes.

- `find_segment_node(qp_payload, segment_key)`: finds the QP node for a final record.
- `build_question_layout(node, figure_regions_by_page, code_regions_by_page=None)`: returns pages with local coordinates, figure crops, text tokens, blank tokens, and counts.
- `_page_bboxes(node)`: indexes `content_pages` bboxes by page.
- `_ordered_pages(word_boxes)`: sorted page indices present in word boxes.
- `_figures_for_page(regions, words, content_bbox)`: keeps figure/table regions near the segment content band.
- `_canvas_extent(words, figures)`: computes local canvas origin and size.
- `_tokens_for_words(words, origin, code_regions)`: converts word boxes into positioned tokens and blank inputs, marking code tokens monospace.
- `_reading_key(word)`: line/x sort key.
- `_sequential_line_index(ordered)`: maps sorted words to consecutive line numbers.
- `_split_token(word)`: splits dotted/underscore blank runs from ordinary text.
- `_sub_token(...)`: creates token bbox fragments.
- `_local_rect(bbox, origin)`: converts absolute bbox to local x/y/w/h.
- `_inside_any(bbox, figures)`: center-point containment test.
- `_intersects(a, b)`: bbox intersection.
- `_valid_bbox(bbox)`: bbox shape/positivity validation.

### `marker_regions.py`

Loads normalized Marker layout regions for the web layout.

- `MarkerRegionStore.__init__(marker_root)`: initializes caches.
- `_marker_path(paper_code)`: expected Marker JSON path.
- `_ensure_loaded(paper_code)`: lazy-loads and caches regions/page sizes.
- `regions_by_page()`, `regions_for_page()`, `page_size()`: region accessors.
- `figures_by_page()`: returns picture/figure/table regions only.
- `code_by_page()`: returns code regions only.
- `_filter_by_page(regions_by_page, block_types)`: filters region map.
- `_is_header_or_footer(bbox)`: drops decorative header/footer regions.
- `extract_regions(document)`: recursively extracts kept regions and page sizes from Marker JSON.
- `_collect_blocks(block, out)`: recursive block walker; stops descending once a kept group is accepted.
- `_valid_bbox(bbox)`: bbox validation.

### `figure_render.py` and `__main__.py`

- `figure_render.render_region_png(...)`: maps image-space bbox back to PDF points and returns a PNG crop.
- `__main__.parse_args()`: web app CLI args.
- `__main__.main()`: validates record file, starts server, prints parser/grading mode.

## Runners And Scripts

### `src/pipeline/runners/qsplitter_batch.py`

- `parse_args()`: batch qsplitter CLI args.
- `has_required_inputs(paper_code, ocr_dir, marker_dir)`: validates OCR/Marker inputs for a paper.
- `main()`: finds all `_qp_` PDFs, filters complete inputs, processes each, reports errors.

### `src/pipeline/runners/qsplitter_diagnostics_batch.py`

- `parse_args()`: batch diagnostics CLI args.
- `has_required_inputs(...)`: same input check as qsplitter batch.
- `main()`: runs diagnostics across question papers, writes debug/hierarchy artifacts, and reports failures.

### `src/pipeline/scripts/render_qsplitter_screenshots.py`

Older renderer from `hierarchy.json` rather than segmented content pages.

- `load_json(path)`: JSON reader.
- `render_pdf_page(...)`: page renderer scaled to OCR image bbox.
- `marker_name(text)`: safe marker filename.
- `build_end_marker(page_index, y)`: synthetic marker for final segment end.
- `crop_segment(...)`: crops and stitches segment images between start/end markers.
- `render_paper(...)`: renders question/primary/secondary screenshots for one hierarchy.
- `parse_args()`: CLI args.
- `iter_papers(hierarchy_dir)`: yields hierarchy directories.
- `main()`: renders one or all papers.

## Rust Pseudocode Parser

### Flow

`pseudocode-parser/src/main.rs` reads source from `--source`, `--source-file`, or stdin, tokenizes it with `Lexer::tokenize`, parses statements with `Parser::parse_statements`, and prints JSON through `json_out::result_json`. Exit code 0 means the CLI ran; parse success/failure is inside JSON `ok`.

### Root `ast.rs`

Defines the AST that the parser returns.

- `FileMode`: `READ`, `WRITE`, `APPEND`.
- `Operator`, `Position`, `Associativity`, `Precedence`: parser operator metadata.
- `BinaryExpr`: left/operator/right expression node.
- `Ast`: wrapper enum for identifiers, expressions, and statements.
- `Expr`: binary expressions, literals, calls, array access, and EOF checks.
- `Stmt`: supported Cambridge pseudocode statements, including control flow, assignment, declarations, routines, calls, file I/O, and type definitions.
- `TypeDefinition`, `CaseArm`, `CaseCondition`, `BlockStmt`: supporting AST nodes.
- `BlockStmt::new(...)`: constructs a block.
- `Expr::to_prefix()`, `Stmt::to_prefix()`, `Ast::to_prefix()`, `Ast::print_prefix()`: debug/prefix rendering helpers, not the JSON contract.

### Root `parser.rs`

Recursive-descent/precedence parser over lexer tokens.

- `Parser::new(tokens, source)`: initializes token stream, operator precedence table, source, and scope level.
- `peek(n)`, `peek_result(n)`, `advance()`: token navigation.
- `is_terminator(token_type)`, `is_operator(token_type)`: expression parsing guards.
- `parse_top_expr()`, `parse_primary()`, `parse_expr(min_precedence)`: expression parser.
- `parse_function_call_expr(name)`, `parse_array_access_expr(name)`: call and array indexing expressions.
- `parse_statements()`: loops until EOF or enclosing-block terminator.
- `parse_statement(token)`: dispatches by leading token.
- `parse_output()`, `parse_input()`: I/O statements.
- `parse_if_statement()`, `parse_case_statement()`, `parse_case_body()`, `is_case_terminator()`, `could_be_case_label()`: conditional parsing.
- `parse_while_statement()`, `parse_repeat_statement()`, `parse_for_statement()`: loop parsing.
- `parse_declaration()`, `parse_constant_declaration()`, `parse_array_type()`: declarations and type parsing.
- `ast_to_value(ast)`, `ast_to_expr(ast)`: conversions from generic AST wrapper to value/expression.
- `parse_assignment()`: variable or array assignment.
- `parse_procedure()`, `parse_function()`, `parse_return()`, `parse_call()`: routine parsing.
- `parse_close_file()`, `parse_open_file()`, `parse_writefile()`, `parse_readfile()`: file I/O parsing.
- `parse_type_declaration()`: enumerated, pointer, record, and set type declarations.

### `pseudocode-parser/src`

- `main.rs`: CLI argument parsing, source reading, tokenizer/parser invocation, JSON output.
  - `parse_cli_args()`: validates `--format`, `--source-file`, `--source`.
  - `read_source(args)`: reads source from arg/file/stdin.
  - `main()`: runs tokenize/parse and prints JSON.
- `Lexer/lexer.rs`: tokenization.
  - `TokenType`: all literals, operators, punctuation, and Cambridge keywords.
  - `Token::new(...)`: token constructor.
  - `keyword_token(word)`: maps uppercase words to keyword tokens.
  - `is_skipped_word(word)`: drops unsupported but common grammar words like `DO`, `BYREF`, `BYVAL`.
  - `Lexer::new(source)`: initializes lexer state.
  - `peek(n)`, `advance()`, `error(...)`: lexer helpers.
  - `Lexer::tokenize()`: scans source, handling comments, numbers, identifiers/keywords, string/char literals, arrows/comparison operators, and unexpected-char diagnostics.
  - `tokenize(source)`: convenience wrapper.
- `json_out.rs`: dependency-free JSON serialization.
  - `escape()`, `string()`: JSON string escaping helpers.
  - `operator_symbol()`, `value_json()`, `type_json()`, `array_type_json()`: expression/type serialization helpers.
  - `ast_json()`, `expr_json()`, `stmt_json()`: AST serialization.
  - `block_json()`, `optional_block_json()`, `case_condition_json()`, `file_mode_json()`, `parameters_json()`, `type_definition_json()`: nested serialization helpers.
  - `diagnostic_json()`, `result_json()`: final parser result JSON.
- `errortype.rs`: `ErrorType` and `CPSError` diagnostic structs.
- `Inter/cps.rs`: minimal `Value`, `Type`, and `ArrayType` model needed by root AST/parser.
- `Parser/mod.rs`, `Lexer/mod.rs`, `Inter/mod.rs`: module wrappers that expose root parser/AST or local lexer/intermediate modules.
- `tests/golden.rs`: dependency-light integration tests that execute the compiled CLI and assert JSON contract.

## Tests

The Python tests use `unittest`.

- `tests/test_builder_hierarchy.py`: qsplitter assignment of same-line and cross-page primaries/secondaries.
- `tests/test_segmentation.py`: segment end boundaries, page-bottom handling, word boxes, noise/exclusion filtering.
- `tests/test_ms_parser.py`: mark-scheme marker parsing, table row extraction, text reconstruction, continuation rows, underline metadata, and trailing marks splitting.
- `tests/test_select_pseudocode_writing.py`: descendant selection superseding ancestors.
- `tests/test_build_final_records.py`: QP/MS joining at question/primary/secondary levels, missing-data discard reasons, stable ids.
- `tests/test_extract_marking_points.py`: structured rubric extraction, underline extraction, alternatives, declaration splitting, caps, and boundary cases.
- `tests/test_marking_point_overrides.py`: manual override and verified-over-list behavior.
- `tests/test_validate_marking_points.py`: audit flag behavior.
- `tests/test_ast_adapter.py`: parser subprocess success/failure/timeout/missing binary behavior.
- `tests/test_openrouter_client.py`: dry-run, prompt building, JSON extraction/validation, cap logic, and alternatives.
- `tests/test_grading_eval_cases.py`: eval-case shape and monotonic predicted marks.
- `tests/test_webapp.py`: routing and grade endpoint behavior.
- `tests/test_question_layout.py`: text/blank token reconstruction and figure/code region handling.
- `tests/test_marker_regions.py`: Marker region extraction/filtering.
- `tests/test_pseudocode_renderer.py`: blank crop/page detection.
- `src/pipeline/msplitter/tests/test_markers.py`: shared marker extractor behavior outside the main `tests/` tree.

Recommended verification after code changes:

```bash
python -m py_compile $(find src tests -path '*/__pycache__/*' -prune -o -name '*.py' -print)
python -m unittest discover -s tests -p 'test_*.py'
python -m unittest src.pipeline.msplitter.tests.test_markers
cd pseudocode-parser && cargo test
```

## Suggested Manual Review Checklist

1. Regenerate a small sample paper and compare `hierarchy.json`, `segmented_questions.json`, and debug screenshots.
2. Review any hard-coded paper-specific overrides before changing general heuristics.
3. For mark schemes, inspect `unresolved_rows`, empty question lists, and table debug images before editing row logic.
4. When changing marking-point extraction, run `validate_marking_points` before and after and compare flag counts.
5. When changing record schema fields, check web app, screenshot renderer, final-record builder, diagnostics, and tests for stale legacy field names.
6. When changing Rust parser output, update `ast_adapter`, `openrouter_client.build_grading_messages`, Rust golden tests, and Python adapter tests together.
