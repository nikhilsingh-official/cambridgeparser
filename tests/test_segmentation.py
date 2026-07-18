import unittest
from pathlib import Path

from src.pipeline.parser.qsplitter.segmentation import build_segmented_questions


def make_line(text: str, y: float, start_x: float = 0.0):
    chars = []
    x = start_x
    for ch in text:
        chars.append(
            {
                "text": ch,
                "bbox": [x, y, x + 1.0, y + 1.0],
                "bbox_valid": True,
            }
        )
        x += 1.0
    return {
        "text": text,
        "bbox": [start_x, y, x, y + 1.0],
        "chars": chars,
    }


def make_marker(text: str, page_index: int, x: float, y: float, line_index: int, width: float = 3.0):
    return {
        "text": text,
        "bbox": [x, y, x + width, y + 1.0],
        "page_index": page_index,
        "x": x,
        "y": y,
        "line_id": (page_index, line_index),
    }


class SegmentationTests(unittest.TestCase):
    def setUp(self):
        self.data = [
            {
                "image_bbox": [0.0, 0.0, 100.0, 200.0],
                "text_lines": [
                    make_line("1 Intro", 10.0),
                    make_line("(a) alpha words", 20.0),
                    make_line("(i) roman words", 30.0),
                    make_line("(b) beta words", 60.0),
                    make_line("tail before page break", 90.0),
                ],
            },
            {
                "image_bbox": [0.0, 0.0, 120.0, 250.0],
                "text_lines": [
                    make_line("2 Next question", 10.0),
                    make_line("after two", 30.0),
                ],
            },
        ]

        q1 = make_marker("1", 0, 0.0, 10.0, 0, width=1.0)
        p_a = make_marker("(a)", 0, 0.0, 20.0, 1)
        s_i = make_marker("(i)", 0, 0.0, 30.0, 2)
        p_b = make_marker("(b)", 0, 0.0, 60.0, 3)
        q2 = make_marker("2", 1, 0.0, 10.0, 0, width=1.0)

        self.hierarchy = {
            "paper_code": "paper",
            "questions": [
                {
                    "question": q1,
                    "primary_subparts": [
                        {
                            "primary": p_a,
                            "secondary_subparts": [{"secondary": s_i}],
                        },
                        {
                            "primary": p_b,
                            "secondary_subparts": [],
                        },
                    ],
                },
                {
                    "question": q2,
                    "primary_subparts": [],
                },
            ],
        }

        self.segmented = build_segmented_questions(
            paper_code="paper",
            hierarchy_payload=self.hierarchy,
            pdf_dir=Path("."),
            ocr_dir=Path("."),
            context={"data": self.data},
        )

    def test_primary_ends_at_next_primary_not_secondary(self):
        primary_a = self.segmented["questions"][0]["primary_subparts"][0]["primary"]
        self.assertEqual(primary_a["content_bbox"][3], 60.0)
        self.assertIn("roman words", primary_a["content_text"])

    def test_cross_page_end_uses_dynamic_page_bottom(self):
        primary_b = self.segmented["questions"][0]["primary_subparts"][1]["primary"]
        self.assertEqual(primary_b["content_bbox"][3], 200.0)

    def test_word_boxes_are_emitted_flat_and_per_page(self):
        primary_a = self.segmented["questions"][0]["primary_subparts"][0]["primary"]

        self.assertTrue(primary_a["content_word_boxes"])
        self.assertTrue(any(word["text"] == "alpha" for word in primary_a["content_word_boxes"]))

        content_pages = primary_a["content_pages"]
        self.assertTrue(content_pages)
        self.assertIn("words", content_pages[0])
        self.assertTrue(content_pages[0]["words"])

    def test_excluded_lines_are_ignored_for_content_text_and_words(self):
        data = [
            {
                "image_bbox": [0.0, 0.0, 100.0, 200.0],
                "text_lines": [
                    make_line("1 prompt", 10.0),
                    make_line("(a) keep this line", 40.0),
                    make_line("[4]", 150.0),
                    make_line("noisy header/footer", 180.0),
                ],
            }
        ]
        hierarchy = {
            "paper_code": "paper",
            "questions": [
                {
                    "question": make_marker("1", 0, 0.0, 10.0, 0, width=1.0),
                    "primary_subparts": [
                        {
                            "primary": make_marker("(a)", 0, 0.0, 40.0, 1),
                            "secondary_subparts": [],
                        }
                    ],
                }
            ],
        }
        segmented = build_segmented_questions(
            paper_code="paper",
            hierarchy_payload=hierarchy,
            pdf_dir=Path("."),
            ocr_dir=Path("."),
            context={
                "data": data,
                "excluded_bboxes_by_page": [[{"bbox": [0.0, 140.0, 120.0, 200.0], "block_type": "PageFooter"}]],
            },
        )
        primary = segmented["questions"][0]["primary_subparts"][0]["primary"]
        self.assertEqual(primary["content_pages"][0]["bbox"], [0.0, 40.0, 100.0, 200.0])
        self.assertIn("keep this line", primary["content_text"])
        self.assertIn("[4]", primary["content_text"])
        self.assertNotIn("noisy header/footer", primary["content_text"])


if __name__ == "__main__":
    unittest.main()
