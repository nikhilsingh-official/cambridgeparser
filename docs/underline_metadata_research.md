# Underline metadata in Surya, Marker, and PyMuPDF

Research date: 2026-07-19.

Primary sources checked:

- Surya official repository at commit `0b16e8e32237bc91ce8d76af551b9e7ed748b54a`.
- Marker official repository at commit `ef16c2caa29d76f3ca3126944d2e1be79f560bda`.
- PyMuPDF official repository/docs at commit `48a3b636ca0f25218ac76e42c75eadbd0ff5f687`.

## Summary

Surya OCR output does not expose underline as structured text-style metadata. Its OCR CLI writes `page.model_dump()` into `results.json`, and the current `PageOCRResult` / `BlockOCRResult` models contain layout label, reading order, HTML, geometry, confidence, and error/skipped fields, but no `underline`, `formats`, `style`, or equivalent field. The HTML string may contain model-produced markup, but the first-party schema does not define underline metadata as a structured output contract. Sources: Surya OCR CLI writes page model dumps to `results.json` ([`surya/scripts/ocr_text.py`](https://github.com/datalab-to/surya/blob/0b16e8e32237bc91ce8d76af551b9e7ed748b54a/surya/scripts/ocr_text.py#L33-L42)); `BlockOCRResult` and `PageOCRResult` fields ([`surya/recognition/schema.py`](https://github.com/datalab-to/surya/blob/0b16e8e32237bc91ce8d76af551b9e7ed748b54a/surya/recognition/schema.py#L8-L19)); shared geometry/confidence fields ([`surya/common/polygon.py`](https://github.com/datalab-to/surya/blob/0b16e8e32237bc91ce8d76af551b9e7ed748b54a/surya/common/polygon.py#L9-L57)).

Marker has an internal span schema that can represent underline, and `Span.assemble_html()` can render underlined spans as `<u>...</u>`. However, Marker JSON output does not expose span `formats` as a separate metadata field: regular JSON exposes block `html`, geometry, identifiers, hierarchy, images, and children; OCR JSON exposes line HTML plus per-character text and geometry. Sources: Marker `Span.formats` includes `"underline"` and has an `underline` property ([`marker/schema/text/span.py`](https://github.com/datalab-to/marker/blob/ef16c2caa29d76f3ca3126944d2e1be79f560bda/marker/schema/text/span.py#L16-L44), [`marker/schema/text/span.py`](https://github.com/datalab-to/marker/blob/ef16c2caa29d76f3ca3126944d2e1be79f560bda/marker/schema/text/span.py#L78-L80)); `Span.assemble_html()` emits `<u>` for underline ([`marker/schema/text/span.py`](https://github.com/datalab-to/marker/blob/ef16c2caa29d76f3ca3126944d2e1be79f560bda/marker/schema/text/span.py#L120-L143)); JSON output model fields ([`marker/renderers/json.py`](https://github.com/datalab-to/marker/blob/ef16c2caa29d76f3ca3126944d2e1be79f560bda/marker/renderers/json.py#L12-L27), [`marker/renderers/json.py`](https://github.com/datalab-to/marker/blob/ef16c2caa29d76f3ca3126944d2e1be79f560bda/marker/renderers/json.py#L50-L90)); OCR JSON output model fields ([`marker/renderers/ocr_json.py`](https://github.com/datalab-to/marker/blob/ef16c2caa29d76f3ca3126944d2e1be79f560bda/marker/renderers/ocr_json.py#L10-L38), [`marker/renderers/ocr_json.py`](https://github.com/datalab-to/marker/blob/ef16c2caa29d76f3ca3126944d2e1be79f560bda/marker/renderers/ocr_json.py#L81-L120)); README JSON field description ([`README.md`](https://github.com/datalab-to/marker/blob/ef16c2caa29d76f3ca3126944d2e1be79f560bda/README.md#L319-L338)).

Current Marker source checked here does not show PDF extraction populating underline formats from PDF text. Its PDF provider maps font flags / font names to `plain`, `italic`, and `bold`, then passes those formats into `Span`. Since PyMuPDF documents underline as a decoration drawn separately from font properties, this provider path would not discover underline through font flags alone. Sources: Marker PDF provider format mapping ([`marker/providers/pdf.py`](https://github.com/datalab-to/marker/blob/ef16c2caa29d76f3ca3126944d2e1be79f560bda/marker/providers/pdf.py#L150-L187)); provider passes those formats to `Span` ([`marker/providers/pdf.py`](https://github.com/datalab-to/marker/blob/ef16c2caa29d76f3ca3126944d2e1be79f560bda/marker/providers/pdf.py#L228-L265)); PyMuPDF documents underline as text decoration, not a font property ([`docs/vars.rst`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/docs/vars.rst#L274-L276)).

PyMuPDF / `fitz` can expose detected underline styling on text spans when text extraction is run with `TEXT_COLLECT_STYLES`. In `dict` / `rawdict` span output, `char_flags` is an integer whose bit 1 means underline. This is available in PyMuPDF documentation as `char_flags`, new in v1.25.2. Sources: `TEXT_COLLECT_STYLES` requests text decoration properties including underlining and strikeout ([`docs/vars.rst`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/docs/vars.rst#L274-L276)); span dictionaries include `char_flags` ([`docs/textpage.rst`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/docs/textpage.rst#L303-L326)); `char_flags` bit 1 means underline ([`docs/textpage.rst`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/docs/textpage.rst#L377-L389)); PyMuPDF source defines `TEXT_COLLECT_STYLES` and stores `char_flags` in output spans ([`src/__init__.py`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/src/__init__.py#L17773-L17776), [`src/__init__.py`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/src/__init__.py#L20784-L20835)).

PyMuPDF can also expose underline-related geometry, but through separate mechanisms. For ordinary drawn underlines, `Page.get_drawings()` returns vector paths with drawing commands, colors, opacity, line width, rectangles, sequence numbers, and stroke/fill type. This exposes line geometry, but the path output is generic vector geometry and is not semantically labeled as an underline; associating a line path with text requires inference against nearby text. Sources: `Page.get_drawings()` returns vector graphics / line art ([`docs/page.rst`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/docs/page.rst#L1578-L1584)); path keys include `items`, `rect`, `seqno`, `type`, and `width` ([`docs/page.rst`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/docs/page.rst#L1584-L1605)); item types include line commands (`"l"`) and quads / rectangles ([`docs/page.rst`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/docs/page.rst#L1616-L1623)).

For underline annotations specifically, PyMuPDF can enumerate annotations and expose their geometry as QuadPoints. `PDF_ANNOT_UNDERLINE` is annotation type 9, `Page.annots(types=...)` can filter annotation types, and `Annot.vertices` returns QuadPoints for text markup annotations. Sources: `PDF_ANNOT_UNDERLINE` constant ([`docs/vars.rst`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/docs/vars.rst#L433-L446)); `Page.annots(types=...)` filter ([`docs/page.rst`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/docs/page.rst#L677-L684)); `Annot.vertices` returns QuadPoints for text markup annotations ([`docs/annot.rst`](https://github.com/pymupdf/PyMuPDF/blob/48a3b636ca0f25218ac76e42c75eadbd0ff5f687/docs/annot.rst#L493-L503)).

## Practical conclusion for this repo

Do not expect normalized Surya OCR or Marker layout JSON to contain a reliable structured `underline` field. Marker regular JSON may contain underlining only as rendered HTML (`<u>`) if an upstream span actually has the underline format, but the current source paths checked here do not make that a reliable PDF-derived signal.

For underline detection from Cambridge PDFs, the strongest first-party route is PyMuPDF text extraction with `TEXT_COLLECT_STYLES`, checking `span["char_flags"] & 2` for underline. A geometry fallback can inspect `page.get_drawings()` for horizontal stroke paths near text baselines, and annotation geometry can be obtained from underline annotations via `page.annots(types=(fitz.PDF_ANNOT_UNDERLINE,))` and `annot.vertices`.

## Local experiment results

Environment: PyMuPDF / MuPDF `1.27.2.3`, local PDFs under `resources/pdfs/cs_papers`, generated mark-scheme output under `ms_output`.

The repository's current `ms_output` schema does not carry underline fields. A key scan over generated `mark_scheme.json` records found text/span/word geometry and font metadata (`text`, `bbox`, `pdf_bbox`, `font_name`, `font_size`, `flags`, `is_bold`) but no `underline`, `formats`, or equivalent field. This matches the parser code in `src/pipeline/msplitter/ms_parser.py`, where `_extract_pdf_font_metadata()` stores word and span text/font/bold metadata only.

Legacy Marker JSON is also not enough. A scan over legacy mark-scheme Marker JSON found block-level `html`, `polygon`, `bbox`, `children`, `section_hierarchy`, and `images`. Some HTML contains the word `underlined`, but not stable `<u>` markup for the actual marked tokens.

Plain `page.get_text("dict")` is not enough either. Without explicit style collection, target spans such as `breakpoint` in `9618_s23_ms_21`, `FUNCTION ModuleB` in `9608_s20_ms_23`, and `DECLARE Item ...` in `9618_s24_ms_22` had `char_flags` values like `16` / `24`, with no underline bit.

With explicit style collection, PyMuPDF does expose the underlined runs:

```python
flags = fitz.TEXTFLAGS_DICT | fitz.TEXT_COLLECT_STYLES
page.get_text("dict", flags=flags, clip=answer_cell_rect)
```

Examples observed locally:

- `9618_s23_ms_21`, q1(a): underlined spans `breakpoint`, `report/watch window`, `single stepping`.
- `9618_s23_ms_21`, q2(b): underlined spans `DECLARE StartDate`, `DATE`, `StartDate`, `←`, `SETDATE (15, 11, 2005)`.
- `9608_s20_ms_23`, q2(b)(i): underlined spans `FUNCTION ModuleB`, `ParX : INTEGER)`, `RETURNS BOOLEAN`.
- `9618_s24_ms_22`, q3(a)(ii): underlined declaration alternatives are returned as underlined spans.
- `9608_s17_ms_22`, q5(a)(ii): underlined spans `LogArray : ARRAY[1 : 20]` and `STRING`.

Across the 42 generated mark-scheme records whose answer text contains `underlin`, `TEXT_COLLECT_STYLES` found underlined spans in 40 records. The two misses were:

- `9608_s18_ms_22`, q5(b): the word `underlined` appears in the ordinary answer text, not as the scheme convention "one mark per underlined ...".
- `9618_s23_ms_12`, q7(c): the extracted answer text mentions multiple terms but did not expose styled underline spans in the answer cell with the local PDF/style probe.

`page.get_drawings()` also works as a fallback for many of the same records. Horizontal stroke paths near text baselines recovered terms such as `breakpoint`, `report/watch window`, `single stepping`, `FUNCTION ModuleB`, `(ParX : INTEGER)`, and `DECLARE Item : ARRAY [1:2000]`. This route is more heuristic because the vector paths are generic drawings, not semantically labeled underlines.

Recommended implementation direction: add a PDF style pass to `src/pipeline/msplitter/ms_parser.py` alongside `_extract_pdf_font_metadata()`. For each answer cell bbox, call `page.get_text("dict", flags=fitz.TEXTFLAGS_DICT | fitz.TEXT_COLLECT_STYLES, clip=rect)`, collect spans where `span["char_flags"] & 2`, scale their `bbox` / `pdf_bbox` the same way existing span metadata is scaled, and attach them as `answer_underlined_spans` or `answer_style_spans`. Use `get_drawings()` only as a fallback for records matching an underlined-mark convention but returning no styled spans.
