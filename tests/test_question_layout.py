import unittest

from src.website.question_layout import (
    BLANK_RUN,
    _split_token,
    build_question_layout,
)


def word(text, x0, y0, x1, y1, page=0, line=0):
    return {
        "page_index": page,
        "line_id": [page, line],
        "text": text,
        "bbox": [x0, y0, x1, y1],
    }


class SplitTokenTests(unittest.TestCase):
    def test_pure_dot_run_is_one_blank(self):
        parts = _split_token(word("..............", 0.0, 0.0, 140.0, 10.0))
        self.assertEqual([p["kind"] for p in parts], ["blank"])

    def test_embedded_blank_splits_into_text_blank_text(self):
        parts = _split_token(word("AB......CD", 0.0, 0.0, 100.0, 10.0))
        self.assertEqual([p["kind"] for p in parts], ["text", "blank", "text"])
        self.assertEqual(parts[0]["text"], "AB")
        self.assertEqual(parts[2]["text"], "CD")
        # Uniform char width = 100/10 = 10; blank spans chars 2..8.
        self.assertAlmostEqual(parts[1]["_bbox"][0], 20.0)
        self.assertAlmostEqual(parts[1]["_bbox"][2], 80.0)

    def test_short_dot_run_is_not_a_blank(self):
        # Three dots (an ellipsis) must stay as ordinary text.
        parts = _split_token(word("hi...", 0.0, 0.0, 50.0, 10.0))
        self.assertEqual([p["kind"] for p in parts], ["text"])

    def test_blank_run_pattern_matches_dotted_leaders(self):
        self.assertTrue(BLANK_RUN.search("...................."))
        self.assertTrue(BLANK_RUN.search("____"))
        self.assertIsNone(BLANK_RUN.search("..."))


class BuildLayoutTests(unittest.TestCase):
    def _node(self):
        return {
            "content_pages": [{"page_index": 0, "bbox": [0.0, 0.0, 400.0, 400.0]}],
            "content_word_boxes": [
                word("Write", 10.0, 10.0, 50.0, 26.0, line=0),
                word("code:", 54.0, 10.0, 90.0, 26.0, line=0),
                word("x", 10.0, 30.0, 20.0, 46.0, line=1),
                word("...........", 24.0, 30.0, 120.0, 46.0, line=1),
                word("INSIDEFIG", 200.0, 200.0, 280.0, 216.0, line=5),
            ],
        }

    def test_lines_grouping_and_reading_order(self):
        layout = build_question_layout(self._node(), {}, {})
        self.assertEqual(len(layout["pages"]), 1)
        tokens = layout["pages"][0]["tokens"]
        texts = [(t["line"], t.get("text"), t["kind"]) for t in tokens]
        self.assertEqual(texts[0], (0, "Write", "text"))
        self.assertEqual(texts[1], (0, "code:", "text"))
        self.assertEqual(texts[2][0], 1)  # x on next line
        self.assertEqual(texts[2][1], "x")

    def test_blank_counted_and_split(self):
        layout = build_question_layout(self._node(), {}, {})
        self.assertEqual(layout["blank_count"], 1)
        self.assertTrue(layout["has_blanks"])
        blanks = [t for t in layout["pages"][0]["tokens"] if t["kind"] == "blank"]
        self.assertEqual(len(blanks), 1)
        self.assertEqual(blanks[0]["chars"], len("..........."))

    def test_words_inside_figures_are_excluded_and_figure_emitted(self):
        figures = {0: [{"block_type": "Picture", "bbox": [180.0, 180.0, 300.0, 300.0]}]}
        layout = build_question_layout(self._node(), figures, {})
        self.assertEqual(layout["figure_count"], 1)
        texts = [t.get("text") for t in layout["pages"][0]["tokens"]]
        self.assertNotIn("INSIDEFIG", texts)
        fig = layout["pages"][0]["figures"][0]
        self.assertEqual(fig["index"], 0)
        self.assertEqual(fig["block_type"], "Picture")

    def test_code_region_marks_tokens_mono(self):
        code = {0: [{"block_type": "Code", "bbox": [0.0, 25.0, 400.0, 50.0]}]}
        layout = build_question_layout(self._node(), {}, code)
        by_text = {t.get("text"): t for t in layout["pages"][0]["tokens"] if t["kind"] == "text"}
        self.assertNotIn("mono", by_text["Write"])  # line 0, above the code region
        self.assertTrue(by_text["x"].get("mono"))  # line 1, inside the code region

    def test_local_coordinates_are_relative_to_canvas(self):
        layout = build_question_layout(self._node(), {}, {})
        page = layout["pages"][0]
        # Canvas origin is the min word corner minus padding, so the first token
        # never sits at a negative offset.
        self.assertGreaterEqual(min(t["x"] for t in page["tokens"]), 0.0)
        self.assertGreaterEqual(min(t["y"] for t in page["tokens"]), 0.0)


if __name__ == "__main__":
    unittest.main()
