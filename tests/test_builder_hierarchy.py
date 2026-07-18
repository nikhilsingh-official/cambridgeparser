import unittest
from pathlib import Path

from src.pipeline.parser.qsplitter.builder import build_hierarchical_structure


def make_marker(text: str, page_index: int, x: float, y: float, line_index: int):
    return {
        "text": text,
        "bbox": [x, y, x + 10, y + 10],
        "page_index": page_index,
        "x": x,
        "y": y,
        "line_id": (page_index, line_index),
    }


class BuildHierarchyTests(unittest.TestCase):
    def build(self, questions, primaries, secondaries):
        context = {
            "question_candidates": questions,
            "primary_subpart_markers": primaries,
            "secondary_subpart_markers": secondaries,
        }
        return build_hierarchical_structure(
            "paper",
            Path("."),
            Path("."),
            Path("."),
            context=context,
        )

    def test_assigns_question_primary_and_secondary_on_same_line(self):
        hierarchy = self.build(
            [make_marker("1", 0, 10, 100, 0)],
            [make_marker("(a)", 0, 30, 100, 0)],
            [make_marker("(i)", 0, 50, 100, 0)],
        )

        question = hierarchy["questions"][0]
        self.assertEqual(question["question"]["text"], "1")
        self.assertEqual(len(question["primary_subparts"]), 1)
        self.assertEqual(question["primary_subparts"][0]["primary"]["text"], "(a)")
        self.assertEqual(
            [entry["secondary"]["text"] for entry in question["primary_subparts"][0]["secondary_subparts"]],
            ["(i)"],
        )

    def test_assigns_secondary_when_primary_and_secondary_share_line(self):
        hierarchy = self.build(
            [make_marker("1", 0, 10, 100, 0)],
            [make_marker("(a)", 0, 30, 140, 1)],
            [make_marker("(i)", 0, 50, 140, 1)],
        )

        question = hierarchy["questions"][0]
        self.assertEqual(len(question["primary_subparts"]), 1)
        self.assertEqual(
            [entry["secondary"]["text"] for entry in question["primary_subparts"][0]["secondary_subparts"]],
            ["(i)"],
        )

    def test_assigns_secondary_to_latest_preceding_primary_across_pages(self):
        hierarchy = self.build(
            [make_marker("1", 0, 10, 10, 0)],
            [
                make_marker("(a)", 0, 30, 100, 1),
                make_marker("(b)", 1, 30, 50, 2),
            ],
            [make_marker("(ii)", 1, 50, 20, 0)],
        )

        question = hierarchy["questions"][0]
        self.assertEqual(
            [entry["primary"]["text"] for entry in question["primary_subparts"]],
            ["(a)", "(b)"],
        )
        self.assertEqual(
            [entry["secondary"]["text"] for entry in question["primary_subparts"][0]["secondary_subparts"]],
            ["(ii)"],
        )
        self.assertEqual(question["primary_subparts"][1]["secondary_subparts"], [])


if __name__ == "__main__":
    unittest.main()
