import unittest

from src.pipeline.msplitter.ms_parser import (
    _append_row_to_node,
    _extract_table_rows,
    _get_or_create_question_tree,
    _parse_marker_with_context,
    _split_marks_from_text,
    _sort_question_entries,
    paper_year_from_code,
    parse_question_marker,
)


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

    def test_split_marks_from_text_extracts_trailing_square_bracket_marks(self):
        answer, marks = _split_marks_from_text("C = data bus [3]")

        self.assertEqual(answer, "C = data bus")
        self.assertEqual(marks, "[3]")


if __name__ == "__main__":
    unittest.main()
