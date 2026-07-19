import json
import tempfile
import unittest
from pathlib import Path

from src.pipeline.pseudocode_tools.build_final_records import (
    build_records,
    ms_paper_code_for,
)


def qp_node(text, content_text):
    return {
        "text": text,
        "bbox": [0.0, 0.0, 10.0, 10.0],
        "page_index": 0,
        "content_text": content_text,
        "content_bbox": [0.0, 0.0, 100.0, 100.0],
        "content_pages": [{"page_index": 0, "bbox": [0.0, 0.0, 100.0, 100.0]}],
    }


def ms_node(question_number, primary, secondary, answer_text, marks_value):
    return {
        "text": f"({secondary})" if secondary else (f"({primary})" if primary else question_number),
        "parsed_marker": {
            "question_number": question_number,
            "primary_marker": primary,
            "secondary_marker": secondary,
            "normalized_key": f"q{question_number}",
        },
        "answer_text": answer_text,
        "marks_text": str(marks_value) if marks_value is not None else "",
        "marks_value": marks_value,
        "content_pages": [{"page_index": 1, "table_index": 0, "row_index": 0}],
    }


def make_hit(paper_code, question_marker, segment_kind, primary=None, secondary=None):
    return {
        "paper_code": paper_code,
        "question_marker": question_marker,
        "primary_marker": primary,
        "secondary_marker": secondary,
        "segment_kind": segment_kind,
        "matched_positive": ["write pseudocode"],
        "decision_reason": "test",
    }


class BuildFinalRecordsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.qp_dir = root / "qp_output"
        self.ms_dir = root / "ms_output"

        qp_payload = {
            "paper_code": "9618_s23_qp_21",
            "questions": [
                {
                    "question": qp_node("2", "Question two context [6]"),
                    "primary_subparts": [
                        {
                            "primary": qp_node("(a)", "Write pseudocode for part a [4]"),
                            "secondary_subparts": [
                                {"secondary": qp_node("(i)", "Write pseudocode for part a i [2]")}
                            ],
                        }
                    ],
                },
                {
                    "question": qp_node("4", "Write pseudocode for function MakeString() [6]"),
                    "primary_subparts": [],
                },
            ],
        }
        qp_path = self.qp_dir / "9618_s23_qp_21" / "segmented_questions.json"
        qp_path.parent.mkdir(parents=True)
        qp_path.write_text(json.dumps(qp_payload))

        ms_payload = {
            "paper_code": "9618_s23_ms_21",
            "questions": [
                {
                    "question": ms_node("2", "a", None, "", None),
                    "primary_subparts": [
                        {
                            "primary": ms_node(
                                "2", "a", None, "MP1\nInitialise the total\nMP2\nLoop 10 times", 4
                            ),
                            "secondary_subparts": [
                                {
                                    "secondary": ms_node(
                                        "2", "a", "i", "MP1\nOutput the result", 2
                                    )
                                }
                            ],
                        }
                    ],
                },
                {
                    "question": ms_node(
                        "4",
                        None,
                        None,
                        "FUNCTION MakeString() RETURNS STRING\nMP1\nFunction heading and end\nMP2\nDeclaration of locals",
                        6,
                    ),
                    "primary_subparts": [],
                },
            ],
        }
        ms_path = self.ms_dir / "9618_s23_ms_21" / "mark_scheme.json"
        ms_path.parent.mkdir(parents=True)
        ms_path.write_text(json.dumps(ms_payload))

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, hits):
        return build_records(hits, qp_dir=self.qp_dir, ms_dir=self.ms_dir)

    def test_ms_paper_code_mapping(self):
        self.assertEqual(ms_paper_code_for("9618_s23_qp_21"), "9618_s23_ms_21")
        self.assertEqual(ms_paper_code_for("9608_w15_qp_23"), "9608_w15_ms_23")

    def test_question_level_record_matches_question_node(self):
        payload = self.build([make_hit("9618_s23_qp_21", "4", "question")])

        self.assertEqual(payload["summary"]["record_count"], 1)
        record = payload["records"][0]
        self.assertEqual(record["schema_version"], "pseudocode-question-record/v1")
        self.assertEqual(record["segment_key"]["segment_kind"], "question")
        self.assertIn("MakeString", record["question_text"])
        self.assertEqual(record["mark_scheme"]["marks_value"], 6)
        self.assertEqual(record["mark_scheme"]["max_marks"], 6)
        point_texts = [p["text"] for p in record["mark_scheme"]["marking_points"]]
        self.assertIn("Function heading and end", point_texts)
        self.assertEqual(record["qp_marks_value"], 6)

    def test_primary_level_record_matches_primary_node(self):
        payload = self.build([make_hit("9618_s23_qp_21", "2", "primary", primary="(a)")])

        record = payload["records"][0]
        self.assertEqual(record["segment_key"]["primary_marker"], "(a)")
        self.assertIn("part a", record["question_text"])
        self.assertEqual(record["question_context_text"], "Question two context [6]")
        self.assertEqual(record["mark_scheme"]["marks_value"], 4)
        self.assertEqual(len(record["mark_scheme"]["marking_points"]), 2)

    def test_secondary_level_record_matches_secondary_node(self):
        payload = self.build(
            [make_hit("9618_s23_qp_21", "2", "secondary", primary="(a)", secondary="(i)")]
        )

        record = payload["records"][0]
        self.assertEqual(record["segment_key"]["secondary_marker"], "(i)")
        self.assertIn("part a i", record["question_text"])
        self.assertEqual(record["mark_scheme"]["marks_value"], 2)
        self.assertEqual(
            record["mark_scheme"]["marking_points"][0]["text"], "Output the result"
        )

    def test_missing_ms_question_is_discarded_with_reason(self):
        payload = self.build([make_hit("9618_s23_qp_21", "9", "question")])

        self.assertEqual(payload["summary"]["record_count"], 0)
        self.assertEqual(payload["summary"]["discarded_count"], 1)
        self.assertEqual(payload["discarded"][0]["reason"], "qp_question_not_found")

    def test_missing_ms_paper_is_discarded_with_reason(self):
        hit = make_hit("9618_s23_qp_21", "4", "question")
        hit["paper_code"] = "9618_s23_qp_21"
        # Point at a QP paper with no matching mark scheme by renaming ms dir file
        payload = build_records(
            [hit], qp_dir=self.qp_dir, ms_dir=Path(self.tmp.name) / "nonexistent"
        )

        self.assertEqual(payload["summary"]["record_count"], 0)
        self.assertEqual(payload["discarded"][0]["reason"], "ms_output_missing")

    def test_ids_are_sequential_and_stable(self):
        payload = self.build(
            [
                make_hit("9618_s23_qp_21", "4", "question"),
                make_hit("9618_s23_qp_21", "2", "primary", primary="(a)"),
            ]
        )

        self.assertEqual([r["id"] for r in payload["records"]], [1, 2])


if __name__ == "__main__":
    unittest.main()
