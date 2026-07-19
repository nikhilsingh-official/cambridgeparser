import json
import unittest

from src.pipeline.grading.openrouter_client import (
    OpenRouterConfig,
    build_grading_messages,
    dry_run_result,
    grade_answer,
    validate_grading_payload,
)


def make_record():
    return {
        "id": 1,
        "question_text": "Write pseudocode for function MakeString(). [6]",
        "question_context_text": "context",
        "mark_scheme": {
            "answer_text": "FUNCTION ...",
            "marks_value": 6,
            "max_marks": 6,
            "marking_points": [
                {"id": "mp1", "text": "Function heading and end", "marks": 1},
                {"id": "mp2", "text": "Declaration of locals", "marks": 1},
            ],
        },
    }


def make_parsed_answer(ok=True):
    return {
        "schema_version": "parsed-answer/v1",
        "source_text": "FUNCTION MakeString() RETURNS STRING\nENDFUNCTION",
        "parse": {
            "ok": ok,
            "ast_version": "cambridge-pseudocode-ast/v1",
            "ast": {"statements": []},
            "diagnostics": [],
        },
    }


def valid_model_payload():
    return {
        "total_awarded": 1,
        "max_marks": 6,
        "points": [
            {
                "marking_point_id": "mp1",
                "awarded": True,
                "marks_awarded": 1,
                "confidence": "high",
                "evidence": "Function header present",
                "concerns": [],
            }
        ],
        "overall_explanation": "Partial credit.",
    }


def fake_transport_returning(content):
    def transport(url, headers, body, timeout):
        return json.dumps({"choices": [{"message": {"content": content}}]})

    return transport


class OpenRouterClientTests(unittest.TestCase):
    def test_dry_run_is_default_without_api_key(self):
        config = OpenRouterConfig(api_key=None, model="test-model")
        config.api_key = None

        result = grade_answer(make_record(), make_parsed_answer(), config=config)

        self.assertTrue(result["dry_run"])
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["result"]["points"]), 2)
        self.assertEqual(result["result"]["max_marks"], 6)

    def test_dry_run_result_is_deterministic(self):
        first = dry_run_result(make_record(), make_parsed_answer())
        second = dry_run_result(make_record(), make_parsed_answer())

        self.assertEqual(first, second)

    def test_valid_model_response_is_accepted(self):
        config = OpenRouterConfig(api_key="test-key", model="test-model")
        transport = fake_transport_returning(json.dumps(valid_model_payload()))

        result = grade_answer(
            make_record(), make_parsed_answer(), config=config, dry_run=False,
            transport=transport,
        )

        self.assertTrue(result["ok"])
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["result"]["total_awarded"], 1)
        self.assertEqual(result["model"], "test-model")

    def test_fenced_json_response_is_accepted(self):
        config = OpenRouterConfig(api_key="test-key")
        content = "```json\n" + json.dumps(valid_model_payload()) + "\n```"

        result = grade_answer(
            make_record(), make_parsed_answer(), config=config, dry_run=False,
            transport=fake_transport_returning(content),
        )

        self.assertTrue(result["ok"])

    def test_invalid_model_json_is_rejected_with_raw_response(self):
        config = OpenRouterConfig(api_key="test-key")

        result = grade_answer(
            make_record(), make_parsed_answer(), config=config, dry_run=False,
            transport=fake_transport_returning("the answer deserves 3 marks"),
        )

        self.assertFalse(result["ok"])
        self.assertIn("invalid grading JSON", result["error"])
        self.assertEqual(result["raw_response"], "the answer deserves 3 marks")

    def test_schema_violations_are_named(self):
        payload = valid_model_payload()
        payload["points"][0]["marks_awarded"] = "one"

        error = validate_grading_payload(payload)

        self.assertIn("marks_awarded", error)

    def test_network_error_is_reported_not_raised(self):
        config = OpenRouterConfig(api_key="test-key")

        def failing_transport(url, headers, body, timeout):
            raise OSError("connection refused")

        result = grade_answer(
            make_record(), make_parsed_answer(), config=config, dry_run=False,
            transport=failing_transport,
        )

        self.assertFalse(result["ok"])
        self.assertIn("network error", result["error"])

    def test_messages_include_packet_fields(self):
        messages = build_grading_messages(make_record(), make_parsed_answer())

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("STRICT JSON", messages[0]["content"])
        user = messages[1]["content"]
        self.assertIn("MakeString", user)
        self.assertIn("mp1", user)
        self.assertIn("student_ast", user)

    def test_messages_without_marking_points_ask_for_derived_points(self):
        record = make_record()
        record["mark_scheme"]["marking_points"] = []

        messages = build_grading_messages(record, make_parsed_answer())

        self.assertIn("auto1", messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
