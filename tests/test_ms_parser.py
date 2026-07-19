import unittest

from src.pipeline.msplitter.ms_parser import (
    _append_row_to_node,
    _extract_table_rows,
    _get_or_create_question_tree,
    _parse_marker_with_context,
    _region_text_from_chars,
    _split_marks_from_text,
    _sort_question_entries,
    paper_year_from_code,
    parse_question_marker,
)


def make_char(text, x0, y0, x1, y1):
    return {
        "c": text,
        "bbox": [x0, y0, x1, y1],
        "cx": (x0 + x1) / 2.0,
        "cy": (y0 + y1) / 2.0,
        "height": y1 - y0,
    }


def chars_for_word(word, x, y, width=4.0, height=8.0):
    chars = []
    for offset, ch in enumerate(word):
        x0 = x + offset * width
        chars.append(make_char(ch, x0, y, x0 + width, y + height))
    return chars


def make_cell(text, bbox):
    return {
        "block_type": "TableCell",
        "html": f"<p>{text}</p>",
        "bbox": bbox,
    }


def make_row(page_index, question, answer, marks):
    return {
        "page_index": page_index,
        "table_index": 0,
        "row_index": 0,
        "table_bbox": [0.0, 0.0, 300.0, 100.0],
        "row_bbox": [0.0, 10.0, 300.0, 20.0],
        "question_cell_text": question,
        "answer_cell_text": answer,
        "marks_cell_text": marks,
        "question_cell_bbox": [0.0, 10.0, 50.0, 20.0],
        "answer_cell_bbox": [50.0, 10.0, 250.0, 20.0],
        "marks_cell_bbox": [250.0, 10.0, 300.0, 20.0],
    }


class MarkSchemeParserTests(unittest.TestCase):
    def test_paper_year_from_code_extracts_year(self):
        self.assertEqual(paper_year_from_code("9608_w17_ms_21"), 2017)
        self.assertEqual(paper_year_from_code("9618_s25_ms_21"), 2025)
        self.assertIsNone(paper_year_from_code("unknown_ms"))

    def test_parse_question_marker_normalizes_hierarchy(self):
        parsed = parse_question_marker(" 12 (B) (ii) ")

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["question_number"], "12")
        self.assertEqual(parsed["primary_marker"], "b")
        self.assertEqual(parsed["secondary_marker"], "ii")
        self.assertEqual(parsed["normalized_key"], "q12|(b)|(ii)")

    def test_extract_table_rows_uses_named_header_columns(self):
        table = {
            "bbox": [0.0, 0.0, 300.0, 80.0],
            "children": [
                make_cell("Question", [0.0, 0.0, 50.0, 10.0]),
                make_cell("Answer", [50.0, 0.0, 250.0, 10.0]),
                make_cell("Marks", [250.0, 0.0, 300.0, 10.0]),
                make_cell("1(a)", [0.0, 20.0, 50.0, 30.0]),
                make_cell("identifier", [50.0, 20.0, 250.0, 30.0]),
                make_cell("1", [250.0, 20.0, 300.0, 30.0]),
            ],
        }

        rows = _extract_table_rows(table, page_index=4, table_index=0)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["question_cell_text"], "1(a)")
        self.assertEqual(rows[0]["answer_cell_text"], "identifier")
        self.assertEqual(rows[0]["marks_cell_text"], "1")

    def test_extract_table_rows_keeps_internal_answer_columns_together(self):
        table = {
            "bbox": [0.0, 0.0, 500.0, 100.0],
            "children": [
                make_cell("Question", [0.0, 0.0, 80.0, 10.0]),
                make_cell("", [80.0, 0.0, 160.0, 10.0]),
                make_cell("Answer", [160.0, 0.0, 320.0, 10.0]),
                make_cell("", [320.0, 0.0, 420.0, 10.0]),
                make_cell("Marks", [420.0, 0.0, 500.0, 10.0]),
                make_cell("1(a)", [0.0, 20.0, 80.0, 30.0]),
                make_cell("Example", [80.0, 20.0, 160.0, 30.0]),
                make_cell("Explanation", [160.0, 20.0, 320.0, 30.0]),
                make_cell("Data type", [320.0, 20.0, 420.0, 30.0]),
                make_cell("4", [420.0, 20.0, 500.0, 30.0]),
            ],
        }

        rows = _extract_table_rows(table, page_index=4, table_index=0)

        self.assertEqual(rows[0]["question_cell_text"], "1(a)")
        self.assertEqual(rows[0]["answer_cell_text"], "Example\nExplanation\nData type")
        self.assertEqual(rows[0]["marks_cell_text"], "4")

    def test_extract_table_rows_shared_borders_keep_answers_on_their_row(self):
        # Cambridge mark-scheme grids share horizontal borders between rows and
        # emit thin empty spacer cells in the question column. Cells touching a
        # boundary (answer y1 == previous row y2) must stay with the row below;
        # a first-touch tolerance test shifted every answer up one question.
        table = {
            "bbox": [0.0, 0.0, 300.0, 130.0],
            "children": [
                make_cell("Question", [0.0, 0.0, 50.0, 10.0]),
                make_cell("Answer", [50.0, 0.0, 250.0, 10.0]),
                make_cell("Marks", [250.0, 0.0, 300.0, 10.0]),
                # thin spacer row under the header, as fitz emits for grid lines
                make_cell("", [0.0, 10.0, 50.0, 16.0]),
                make_cell("", [50.0, 10.0, 250.0, 16.0]),
                make_cell("", [250.0, 10.0, 300.0, 16.0]),
                make_cell("1(a)", [0.0, 16.0, 50.0, 60.0]),
                make_cell("first answer", [50.0, 16.0, 250.0, 60.0]),
                make_cell("3", [250.0, 16.0, 300.0, 60.0]),
                make_cell("1(b)", [0.0, 60.0, 50.0, 130.0]),
                make_cell("second answer", [50.0, 60.0, 250.0, 130.0]),
                make_cell("2", [250.0, 60.0, 300.0, 130.0]),
            ],
        }

        rows = _extract_table_rows(table, page_index=2, table_index=0)

        by_question = {row["question_cell_text"]: row for row in rows}
        self.assertEqual(by_question["1(a)"]["answer_cell_text"], "first answer")
        self.assertEqual(by_question["1(a)"]["marks_cell_text"], "3")
        self.assertEqual(by_question["1(b)"]["answer_cell_text"], "second answer")
        self.assertEqual(by_question["1(b)"]["marks_cell_text"], "2")

    def test_extract_table_rows_orphan_answer_band_becomes_continuation_row(self):
        # Answer content with no question-column cell in its band (e.g. a
        # continuation at the top of a table) must surface as a marker-less
        # row instead of being dropped.
        table = {
            "bbox": [0.0, 0.0, 300.0, 130.0],
            "children": [
                make_cell("Question", [0.0, 0.0, 50.0, 10.0]),
                make_cell("Answer", [50.0, 0.0, 250.0, 10.0]),
                make_cell("Marks", [250.0, 0.0, 300.0, 10.0]),
                make_cell("continued code", [50.0, 10.0, 250.0, 60.0]),
                make_cell("5", [250.0, 10.0, 300.0, 60.0]),
                make_cell("2(a)", [0.0, 60.0, 50.0, 130.0]),
                make_cell("own answer", [50.0, 60.0, 250.0, 130.0]),
                make_cell("1", [250.0, 60.0, 300.0, 130.0]),
            ],
        }

        rows = _extract_table_rows(table, page_index=3, table_index=0)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["question_cell_text"], "")
        self.assertEqual(rows[0]["answer_cell_text"], "continued code")
        self.assertEqual(rows[0]["marks_cell_text"], "5")
        self.assertEqual(rows[1]["question_cell_text"], "2(a)")
        self.assertEqual(rows[1]["answer_cell_text"], "own answer")
        self.assertEqual(rows[1]["marks_cell_text"], "1")

    def test_extract_table_rows_without_header_is_ignored(self):
        table = {
            "bbox": [0.0, 0.0, 300.0, 80.0],
            "children": [
                make_cell("1(a)", [0.0, 20.0, 50.0, 30.0]),
                make_cell("identifier", [50.0, 20.0, 250.0, 30.0]),
                make_cell("1", [250.0, 20.0, 300.0, 30.0]),
            ],
        }

        rows = _extract_table_rows(table, page_index=4, table_index=0)

        self.assertEqual(rows, [])

    def test_blank_question_rows_continue_previous_marker(self):
        rows = [
            make_row(4, "1(a)", "first line", "1"),
            make_row(4, "", "continued line", ""),
        ]
        questions_map = {}
        current_marker = None

        for row in rows:
            parsed = parse_question_marker(row["question_cell_text"]) if row["question_cell_text"] else current_marker
            if row["question_cell_text"]:
                current_marker = parsed
            tree_ref = _get_or_create_question_tree(questions_map, parsed, row)
            _append_row_to_node(tree_ref["node"], row, {"words": [], "spans": []}, {"words": [], "spans": []})

        questions = _sort_question_entries(questions_map)
        primary = questions[0]["primary_subparts"][0]["primary"]
        self.assertEqual(primary["answer_text"], "first line\ncontinued line")
        self.assertEqual(primary["marks_value"], 1)

    def test_fallback_marker_parser_uses_relative_subparts(self):
        marker, remainder = _parse_marker_with_context("3 (b) (i) http answer", None)
        self.assertEqual(marker["normalized_key"], "q3|(b)|(i)")
        self.assertEqual(remainder, "http answer")

        marker, remainder = _parse_marker_with_context("(ii) second answer", marker)
        self.assertEqual(marker["normalized_key"], "q3|(b)|(ii)")
        self.assertEqual(remainder, "second answer")

        marker, remainder = _parse_marker_with_context("(c) primary answer", marker)
        self.assertEqual(marker["normalized_key"], "q3|(c)")
        self.assertEqual(remainder, "primary answer")

    def test_region_text_rebuilds_lines_and_word_gaps(self):
        chars = (
            chars_for_word("INPUT", 10.0, 10.0)
            + chars_for_word("StartPos", 34.0, 10.0)
            + chars_for_word("ENDFOR", 10.0, 24.0)
        )

        text = _region_text_from_chars(chars, [0.0, 0.0, 200.0, 40.0])

        self.assertEqual(text, "INPUT StartPos\nENDFOR")

    def test_region_text_merges_spurious_column_fragments_in_line_order(self):
        # Characters belonging to one visual line must be read left to right
        # even when table detection split the region into narrow columns.
        chars = chars_for_word("OUT", 10.0, 10.0) + chars_for_word("PUT", 22.0, 10.0)

        text = _region_text_from_chars(chars, [0.0, 0.0, 100.0, 30.0])

        self.assertEqual(text, "OUTPUT")

    def test_region_text_outside_bbox_is_excluded(self):
        chars = chars_for_word("VISIBLE", 10.0, 10.0) + chars_for_word(
            "HIDDEN", 10.0, 100.0
        )

        text = _region_text_from_chars(chars, [0.0, 0.0, 200.0, 30.0])

        self.assertEqual(text, "VISIBLE")

    def test_double_rendered_text_is_deduplicated(self):
        import fitz

        from src.pipeline.msplitter.ms_parser import _page_visible_chars

        document = fitz.open()
        page = document.new_page(width=595, height=842)
        # Fake-bold: same text drawn twice with a sub-point offset, as in
        # Cambridge mark-scheme marking tables.
        page.insert_text((100, 100), "Answer", fontsize=10)
        page.insert_text((100.3, 100.2), "Answer", fontsize=10)

        chars = _page_visible_chars(page)
        text = _region_text_from_chars(chars, [0.0, 0.0, 595.0, 842.0])
        document.close()

        self.assertEqual(text, "Answer")

    def test_split_marks_from_text_extracts_trailing_square_bracket_marks(self):
        answer, marks = _split_marks_from_text("C = data bus [3]")

        self.assertEqual(answer, "C = data bus")
        self.assertEqual(marks, "[3]")


if __name__ == "__main__":
    unittest.main()
