import json
import unittest

from src.pipeline.grading.openrouter_client import (
    OpenRouterConfig,
    apply_max_marks_cap,
    build_grading_messages,
    dry_run_result,
    grade_answer,
    resolve_max_marks,
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


def alt_record():
    """A record whose mark scheme prints two mutually exclusive 2-mark rubrics."""
    record = make_record()
    record["mark_scheme"]["marks_value"] = 2
    record["mark_scheme"]["max_marks"] = 2
    record["mark_scheme"]["marking_points"] = [
        {"id": "mp1", "text": "Iterative loop over the array", "marks": 1, "alt_group": 0},
        {"id": "mp2", "text": "Returns the running total", "marks": 1, "alt_group": 0},
        {"id": "mp3", "text": "Recursive call on the tail", "marks": 1, "alt_group": 1},
        {"id": "mp4", "text": "Base case on the empty array", "marks": 1, "alt_group": 1},
    ]
    return record


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

    def test_fill_blank_sheet_is_gradable_without_parser_ast(self):
        answer = make_parsed_answer(ok=False)
        answer["answer_kind"] = "fill_blank_sheet"
        answer["source_text"] = "Blank 1 (IF [blank] THEN): SP = 30"

        result = dry_run_result(make_record(), answer)

        self.assertGreater(result["result"]["total_awarded"], 0)

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

    def test_messages_compact_exam_answer_lines(self):
        record = make_record()
        record["question_text"] = (
            "Write pseudocode.\n"
            "........................................................................\n"
            "........................................................................\n"
            ",\t,\n"
            "Continue here."
        )

        user = build_grading_messages(record, make_parsed_answer())[1]["content"]

        self.assertIn("[answer space]", user)
        self.assertEqual(user.count("[answer space]"), 1)
        self.assertNotIn("................................", user)
        self.assertNotIn(",\t,", user)

    def test_messages_without_marking_points_ask_for_derived_points(self):
        record = make_record()
        record["mark_scheme"]["marking_points"] = []

        messages = build_grading_messages(record, make_parsed_answer())

        self.assertIn("auto1", messages[1]["content"])


class AlternativeSolutionSafetyTests(unittest.TestCase):
    def test_alternative_groups_are_listed_separately_and_never_merged(self):
        record = alt_record()

        messages = build_grading_messages(record, make_parsed_answer())
        user = messages[1]["content"]
        system = messages[0]["content"]

        self.assertIn("ALTERNATIVE SOLUTION 1", user)
        self.assertIn("ALTERNATIVE SOLUTION 2", user)
        # Every point survives into the prompt, inside its own group.
        for point_id in ("mp1", "mp2", "mp3", "mp4"):
            self.assertIn(point_id, user)
        self.assertIn("mutually exclusive", system)

    def test_single_group_keeps_the_flat_point_list(self):
        messages = build_grading_messages(make_record(), make_parsed_answer())

        self.assertNotIn("ALTERNATIVE SOLUTION", messages[1]["content"])

    def test_resolve_max_marks_uses_best_group_not_the_sum(self):
        record = alt_record()
        record["mark_scheme"].pop("max_marks")
        record["mark_scheme"].pop("marks_value")

        # 4 points across 2 alternatives of 2 marks each -> cap is 2, not 4.
        self.assertEqual(resolve_max_marks(record), 2)

    def test_total_is_capped_at_max_marks(self):
        result = apply_max_marks_cap(
            {
                "total_awarded": 9,
                "max_marks": 9,
                "points": [],
                "overall_explanation": "Everything matched.",
            },
            3,
        )

        self.assertEqual(result["total_awarded"], 3)
        self.assertEqual(result["max_marks"], 3)
        self.assertEqual(result["cap_applied"], {"reported_total": 9, "max_marks": 3})
        self.assertIn("capped", result["overall_explanation"])

    def test_total_within_cap_is_untouched(self):
        result = apply_max_marks_cap(
            {"total_awarded": 2, "max_marks": 6, "points": [], "overall_explanation": "ok"},
            6,
        )

        self.assertEqual(result["total_awarded"], 2)
        self.assertNotIn("cap_applied", result)
        self.assertEqual(result["overall_explanation"], "ok")

    def test_graded_result_is_capped(self):
        config = OpenRouterConfig(api_key="test-key")
        record = alt_record()
        record["mark_scheme"]["max_marks"] = 2
        payload = valid_model_payload()
        payload["total_awarded"] = 4
        payload["max_marks"] = 4

        result = grade_answer(
            record,
            make_parsed_answer(),
            config=config,
            dry_run=False,
            transport=lambda *args: json.dumps(
                {"choices": [{"message": {"content": json.dumps(payload)}}]}
            ),
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["total_awarded"], 2)

    def test_provider_routing_is_sent_to_openrouter(self):
        config = OpenRouterConfig(
            api_key="test-key",
            model="qwen/qwen3-coder-30b-a3b-instruct",
            provider_only=["novita/fp8"],
            provider_sort="price",
        )
        bodies = []

        def transport(url, headers, body, timeout):
            bodies.append(json.loads(body.decode("utf-8")))
            return json.dumps(
                {"choices": [{"message": {"content": json.dumps(valid_model_payload())}}]}
            )

        result = grade_answer(
            make_record(),
            make_parsed_answer(),
            config=config,
            dry_run=False,
            transport=transport,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(
            bodies[0]["provider"],
            {
                "require_parameters": True,
                "only": ["novita/fp8"],
                "sort": "price",
            },
        )

    def test_dry_run_result_is_capped(self):
        record = alt_record()
        record["mark_scheme"]["max_marks"] = 1

        result = dry_run_result(record, make_parsed_answer())

        self.assertLessEqual(result["result"]["total_awarded"], 1)


if __name__ == "__main__":
    unittest.main()
