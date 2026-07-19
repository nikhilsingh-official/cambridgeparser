import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from src.pipeline.webapp.app import make_server


def make_records_payload():
    return {
        "summary": {"record_count": 2},
        "records": [
            {
                "schema_version": "pseudocode-question-record/v1",
                "id": 1,
                "paper_code": "9618_s23_qp_23",
                "segment_key": {
                    "question_marker": "4",
                    "primary_marker": None,
                    "secondary_marker": None,
                    "segment_kind": "question",
                },
                "question_text": "Write pseudocode for function MakeString(). [6]",
                "question_context_text": "Write pseudocode for function MakeString(). [6]",
                "qp_marks_value": 6,
                "mark_scheme": {
                    "ms_level": "question",
                    "answer_text": "FUNCTION MakeString ...",
                    "marks_text": "6",
                    "marks_value": 6,
                    "max_marks": 6,
                    "marking_points": [
                        {"id": "mp1", "text": "Function heading and end", "marks": 1,
                         "confidence": "high", "style": "mp_label"},
                        {"id": "mp2", "text": "Declaration of locals", "marks": 1,
                         "confidence": "high", "style": "mp_label"},
                    ],
                },
                "provenance": {"screenshots": {}},
                "diagnostics": [],
            },
            {
                "schema_version": "pseudocode-question-record/v1",
                "id": 2,
                "paper_code": "9608_s17_qp_21",
                "segment_key": {
                    "question_marker": "3",
                    "primary_marker": "(a)",
                    "secondary_marker": None,
                    "segment_kind": "primary",
                },
                "question_text": "Write pseudocode for part (a). [4]",
                "question_context_text": "Question 3 context",
                "qp_marks_value": 4,
                "mark_scheme": {
                    "ms_level": "primary",
                    "answer_text": "",
                    "marks_text": "",
                    "marks_value": None,
                    "max_marks": 4,
                    "marking_points": [],
                },
                "provenance": {"screenshots": {}},
                "diagnostics": ["ms_answer_text_empty"],
            },
        ],
        "discarded": [],
    }


class WebAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        records_path = Path(cls.tmp.name) / "records.json"
        records_path.write_text(json.dumps(make_records_payload()))
        cls.server = make_server(records_path, host="127.0.0.1", port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def fetch(self, path, data=None, headers=None):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            headers=headers or {},
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8")

    def test_root_redirects_to_first_record(self):
        status, body = self.fetch("/")
        self.assertEqual(status, 200)
        self.assertIn("MakeString", body)

    def test_records_page_lists_all_records(self):
        status, body = self.fetch("/records")
        self.assertEqual(status, 200)
        self.assertIn("9618_s23_qp_23", body)
        self.assertIn("9608_s17_qp_21", body)

    def test_record_page_shows_question_and_marking_points(self):
        status, body = self.fetch("/record/1")
        self.assertEqual(status, 200)
        self.assertIn("Write pseudocode for function MakeString()", body)
        self.assertIn("Function heading and end", body)
        self.assertIn("answer-input", body)
        self.assertIn("Submit for grading", body)

    def test_record_without_marking_points_shows_notice(self):
        status, body = self.fetch("/record/2")
        self.assertEqual(status, 200)
        self.assertIn("No structured marking points", body)
        self.assertIn("no mark-scheme answer text", body)

    def test_missing_record_is_404(self):
        status, _ = self.fetch("/record/99")
        self.assertEqual(status, 404)

    def test_grade_endpoint_returns_parse_and_grading(self):
        payload = json.dumps({"answer": "OUTPUT 1"}).encode()
        status, body = self.fetch(
            "/record/1/grade", data=payload,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result["record_id"], 1)
        self.assertIn("parse", result["parsed_answer"])
        self.assertIn("ok", result["grading"])
        # Without an API key in tests the grader must fall back to dry-run.
        if result["grading"]["dry_run"]:
            self.assertTrue(result["grading"]["ok"])
            self.assertEqual(len(result["grading"]["result"]["points"]), 2)

    def test_grade_endpoint_rejects_empty_answer(self):
        payload = json.dumps({"answer": "   "}).encode()
        status, body = self.fetch(
            "/record/1/grade", data=payload,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertIn("empty", json.loads(body)["error"])


if __name__ == "__main__":
    unittest.main()
