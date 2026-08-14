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

## Website deployment

The Vercel project uses the repository root as its Root Directory. Keep that
dashboard setting blank: the root `package.json` owns the JavaScript
dependencies, and `vercel.json` points Vite at
`src/website/frontend/vite.config.js` and serves `src/website/static`.

```bash
npm run build
```

This deployment build bundles the browser-ready JSON and WASM snapshots already
committed under `src/website/frontend/public`. It deliberately does not run the
corpus-dependent resource generator or Rust compiler, because their source
inputs and toolchains are not present in a clean Vercel checkout. After changing
those inputs, run `npm run build:website` locally and commit the updated public
artifacts before deploying. Generated question images are optional; when they
are not deployed, the frontend falls back to its positioned-text question view.

Vercel deploys the static frontend only. `/api/grade` remains the separately
deployed Firebase Function described in `functions/README.md`; configure a proxy
or migrate that endpoint before enabling AI grading on a Vercel domain.

## Main Workflows

Source inputs live under `resources/pdfs/` and `resources/ocr/`. Parser-created
artifacts live under `resources/generated/` so the website frontend can consume
them without depending on parser package internals. Shared defaults are defined
in `src.resources.paths`.

Normalize Marker coordinates:

```bash
python -m src.pipeline.msplitter.normalize_marker_output \
  --all \
  --marker-output-dir resources/generated/marker_output \
  --ocr-dir resources/ocr/surya_output \
  --normalized-output-dir resources/generated/normalized_marker_output
```

Build question-paper hierarchy and segmented text:

```bash
python -m src.pipeline.runners.qsplitter_batch \
  --pdf-dir resources/pdfs/cs_papers \
  --ocr-dir resources/ocr/surya_output \
  --marker-dir resources/generated/normalized_marker_output \
  --output-dir resources/generated/qp_output
```

Parse mark schemes:

```bash
python -m src.pipeline.msplitter.ms_parser \
  --pdf-dir resources/pdfs/cs_papers \
  --marker-dir resources/generated/normalized_marker_output \
  --output-dir resources/generated/ms_output
```

Select pseudocode-writing prompts:

```bash
python -m src.pipeline.pseudocode_tools.select_pseudocode_writing \
  --segments resources/generated/qp_output \
  --output-dir resources/generated/pseudocode_writing_hits \
  --rules-file src/pipeline/analysis/diagnostics/pseudocode_custom_rules.json
```

Build canonical question records (joins selection with generated `qp_output` and
`ms_output`, extracts structured marking points, reuses screenshots):

```bash
python -m src.pipeline.pseudocode_tools.build_final_records \
  --selected-json resources/generated/pseudocode_writing_hits/pseudocode_writing_selected.json \
  --qp-dir resources/generated/qp_output \
  --ms-dir resources/generated/ms_output \
  --output-json resources/generated/pseudocode_writing_hits/pseudocode_question_records.json
```

Validate generated artifacts (no model or network calls):

```bash
python -m src.pipeline.analysis.diagnostics.validate_extraction \
  --qp-dir resources/generated/qp_output \
  --ms-dir resources/generated/ms_output \
  --final-json resources/generated/pseudocode_writing_hits/pseudocode_question_records.json \
  --output-json resources/generated/pseudocode_writing_hits/extraction_validation.json
```

Audit marking-point quality (read-only; a severity-ranked scope baseline and
regression gate for grading-safety of the extracted marking points):

```bash
python -m src.pipeline.analysis.diagnostics.validate_marking_points \
  --records resources/generated/pseudocode_writing_hits/pseudocode_question_records.json \
  --output-json resources/generated/pseudocode_writing_hits/marking_point_validation.json
```

### Syllabus tags

Every record carries a `syllabus_tags` list of 4-5 entries describing what the
question asks the candidate to implement (`bubble-sort`, `text-files`,
`records`, ...). Tags come from a controlled vocabulary in
`src/pipeline/pseudocode_tools/syllabus_tags.py`, where each entry is bound to a
numbered subsection of `Computer Science Syllabus.pdf` (9618, for exams from
2027). The per-question assignments were made by hand from the question, its
context, and the mark scheme, and live in
`src/pipeline/pseudocode_tools/question_tag_assignments.py`, keyed by
`segment_key` so record renumbering cannot desynchronise them.

`build_final_records` expands each slug into `{slug, label, syllabus_ref,
description}` on the record and reports coverage in the run summary
(`records_with_syllabus_tags`, `syllabus_tag_counts`). A segment with no entry
gets an empty list plus a `no_syllabus_tags` diagnostic rather than a guess.

To retag a question, edit its tuple in `question_tag_assignments.py` and rerun
`build_final_records`; `tags_for_segment` validates against the vocabulary and
the 4-5 tag rule on the way out, so a typo fails the build instead of shipping.
`python -m unittest tests.test_syllabus_tags` checks the vocabulary, the
assignments, and the generated records.

### Tag and filter UI

`src/website/frontend/src/services/tags.js` owns all filtering as pure
functions (facet counts, query parsing, URL encoding); both list surfaces call
it, so search behaviour cannot drift between them. `TagChips.vue` renders one
chip style in three modes — static label, deep link, filter toggle — and
`FilterPanel.vue` combines the search box, an Any/All match switch, and tag
facets grouped by syllabus section.

- **Problems table** (`/problems`): panel open, filter state mirrored into the
  URL as `?q=&tags=&match=`, so a filtered view is linkable and Back steps
  through filters.
- **IDE explorer**: same panel with `variant="compact"` — facets collapsed
  behind a `<details>` and capped at 14rem so they never push the problem list
  off screen. Each row shows its first two tags.
- **Question panel**: tags sit behind a toggle beside *Show context*. A tag
  names the technique under assessment, so it stays opt-in on an unattempted
  problem for the same reason the mark scheme does.

Multiple tags default to **Any**; with 4-5 tags per question, defaulting to All
empties the table on the user's second click. Facet counts are computed against
the *search*, not the tag selection, so they stay steady while sibling tags are
toggled. Search requires every whitespace-separated term to match, `"quoted
phrases"` are kept whole, and tag labels are part of the haystack.

`python -m unittest tests.test_tag_ui` covers the wiring and runs the filter
module itself under node against the real corpus (skipped when node is absent).

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
python -m src.website \
  --records resources/generated/pseudocode_writing_hits/pseudocode_question_records.json \
  --port 8000
```

Each record renders the cropped question image as the canonical view with a
"Text" toggle that reconstructs the on-page layout from the qsplitter word
boxes: words keep their original positions (selectable and copyable), Marker
figure/diagram/table regions are shown as crisp crops taken straight from the
PDF (`--pdf-dir`) rather than garbled text, and dotted/underscored blanks become
interactive input fields whose contents can be copied into the answer box. The
layout draws on `--qp-dir` (segmented questions) and `--marker-root` (normalized
Marker regions); see `src/website/question_layout.py` and `marker_regions.py`.

Evaluate grading quality against hand-authored answers (15 questions across
fill-in / short / long types, each with high/medium/low candidates and the marks
a human examiner would award). Dry-run without a key only exercises the harness;
set `OPENROUTER_API_KEY` to measure how closely a model tracks the predicted marks:

```bash
python -m src.pipeline.grading.eval \
  --records resources/generated/pseudocode_writing_hits/pseudocode_question_records.json \
  --output-json resources/generated/pseudocode_writing_hits/grading_eval_results.json
```

OpenRouter configuration (grading falls back to a deterministic dry run when
no key is set):

```bash
export OPENROUTER_API_KEY=...                       # user-provided secret
export OPENROUTER_MODEL=google/gemini-2.5-flash   # optional override (this is the default; needs structured-output support)
export OPENROUTER_PROVIDER_ONLY=mistral            # optional provider pin; comma-separate multiple values
export OPENROUTER_PROVIDER_SORT=price              # optional provider routing hint
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
  --marker-dir resources/generated/normalized_marker_output \
  --output-dir /tmp/pseudocode_solving_prod_audit/qp_output
```

## Maintenance Notes

- `src.pipeline.parser.qsplitter` keeps compatibility modules for `geometry`,
  `io`, `markers`, and `type_definitions`; the shared implementations live in
  `src.pipeline.msplitter`.
- `src.resources.paths` owns the canonical filesystem defaults for source inputs
  and generated artifacts. Pipeline modules create artifacts there; website code
  reads them from there.
- `src.website` owns the grading/review web app.
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
- A row whose question cell is a *relative* subpart marker ("(b)", "(ii)") rather
  than a full "3(b)" is resolved against the current question number before it is
  treated as a continuation of the previous cell. Some papers (the 2016 9608
  schemes) print continuation subparts this way; without this the (b)/(c) content
  — and its underlines — leaks into (a)'s cell. Only an empty question cell now
  counts as a genuine page-break continuation.
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
- Marking guidance that references points by number ("Mark points 7 and 8 must
  not be nested") is a note about how the listed marks combine, not a criterion,
  so a line beginning "Mark point(s) <n>" closes the current point rather than
  extending it. The digit distinguishes it from the "Mark points as circled"
  rubric header, which never leads with a number.
- Some schemes list more criteria than marks ("One mark per point (Max 8):" above
  nine items). That cap is recorded as `marking_points_max`, enforced by the
  grading layer, and reported by the audit as `declared_max_list` rather than as
  an extraction defect. The cap is also written without a bracket — "Note: Max 7
  marks" on a trailing line, or "Mark as follows Max 6 marks:" above the list —
  and a bare "Max n" is only read as a cap on a line that is *about* the marking,
  never inside a marking point ("compare with Max 255"). "Note: Max 7 if
  CharCount not used" is a conditional penalty, not a cap, so it is ignored.
- A handful of papers over-list without declaring any cap at all (10 criteria for
  [8] marks, MP1-MP8 for [7], or a "Mark points as circled" scheme with 7
  descriptions for [6] where the 7th is conditional on the 1st). Their points were
  read against the mark scheme by hand and are correct, so they are named in
  `_VERIFIED_OVER_LIST` and audited as `verified_over_list`. That set is an
  *annotation*, not an override: it supplies no marking points, so those records
  still track the extractor as it improves. Note that "Mark points as circled,
  descriptions as below" is not a styled-span convention — the circled digits
  annotate the example code and index the numbered descriptions, which are the
  real rubric — so it does not trigger `rubric_selection_mismatch`.
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
- `ms_parser` rebuilds row text from a deduplicated character set (Cambridge
  emulates bold by drawing glyphs twice, so clip extraction interleaves both
  layers). Genuine inter-word space glyphs are *kept* through that dedup rather
  than dropped and re-guessed from horizontal gaps: on fonts whose space is
  narrower than the gap threshold (the 9618_w25 schemes) guessing collapsed
  words together ("Count-controlledloop withBREAK"). Duplicate spaces left by
  the double-draw are folded back to one. `_region_text_from_chars` still
  synthesises a separator across an unusually wide gap (a spurious table column)
  when neither side already carries a space.
- `ms_parser` records underlined answer spans (`answer_underlined_spans`) via
  PyMuPDF `TEXT_COLLECT_STYLES` (`char_flags & 2`). `build_final_records` turns
  them into marking points for the "one mark per underlined word / expression"
  schemes when no text rubric exists, using the node's mark value to decide how
  finely to split runs (`marking_points_from_underlined_spans`).
