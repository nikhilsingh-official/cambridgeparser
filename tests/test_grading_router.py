"""Google AI Studio client + provider routing.

The fallback rule under test: OpenRouter is used when Google rate-limits us,
and *only* then.
"""

from __future__ import annotations

import json
import unittest
import urllib.error

from src.pipeline.grading.google_ai_client import (
    GoogleAIConfig,
    grade_answer_google,
    is_rate_limit,
    to_gemini_request,
)
from src.pipeline.grading.openrouter_client import OpenRouterConfig
from src.pipeline.grading.router import grade_answer_routed


RECORD = {
    "id": "q1",
    "mark_scheme": {
        "marking_points": [
            {"id": "mp1", "text": "declares the array", "marks": 1},
            {"id": "mp2", "text": "loops over it", "marks": 1},
        ],
        "total_marks": 2,
    },
}
PARSED = {"source": "DECLARE a : ARRAY", "parse": {"ok": True}, "answer_kind": "pseudocode"}

GOOD_PAYLOAD = {
    "total_awarded": 1,
    "max_marks": 2,
    "points": [
        {
            "marking_point_id": "mp1",
            "awarded": True,
            "marks_awarded": 1,
            "confidence": "high",
            "evidence": "line 1 declares it",
            "concerns": [],
        },
        {
            "marking_point_id": "mp2",
            "awarded": False,
            "marks_awarded": 0,
            "confidence": "high",
            "evidence": "no loop present",
            "concerns": [],
        },
    ],
    "overall_explanation": "one of two points met",
}


def gemini_response(payload):
    return json.dumps(
        {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}
    )


def openrouter_response(payload):
    return json.dumps(
        {"choices": [{"message": {"content": json.dumps(payload)}}]}
    )


def http_error(code, body=b"{}"):
    def transport(url, headers, request_body, timeout):
        raise urllib.error.HTTPError(url, code, "err", {}, __import__("io").BytesIO(body))

    return transport


class GeminiRequestShapeTests(unittest.TestCase):
    def test_system_message_becomes_system_instruction(self):
        request = to_gemini_request(
            [{"role": "system", "content": "you grade"}, {"role": "user", "content": "q"}]
        )
        self.assertEqual(request["systemInstruction"]["parts"], [{"text": "you grade"}])
        self.assertEqual(request["contents"][0]["role"], "user")
        self.assertEqual(request["contents"][0]["parts"], [{"text": "q"}])

    def test_json_mode_and_schema_are_requested(self):
        config = to_gemini_request([{"role": "user", "content": "q"}])["generationConfig"]
        self.assertEqual(config["responseMimeType"], "application/json")
        self.assertEqual(config["temperature"], 0)
        self.assertIn("total_awarded", config["responseSchema"]["properties"])

    def test_schema_omits_additional_properties(self):
        """Gemini rejects JSON Schema's additionalProperties outright."""
        schema = json.dumps(
            to_gemini_request([{"role": "user", "content": "q"}])["generationConfig"][
                "responseSchema"
            ]
        )
        self.assertNotIn("additionalProperties", schema)

    def test_thinking_config_is_omitted_unless_asked_for(self):
        default = to_gemini_request([{"role": "user", "content": "q"}])
        self.assertNotIn("thinkingConfig", default["generationConfig"])
        budgeted = to_gemini_request([{"role": "user", "content": "q"}], thinking_budget=0)
        self.assertEqual(budgeted["generationConfig"]["thinkingConfig"]["thinkingBudget"], 0)


class GoogleClientTests(unittest.TestCase):
    def test_successful_grade_reports_the_google_provider(self):
        captured = {}

        def transport(url, headers, body, timeout):
            captured["url"] = url
            captured["headers"] = headers
            return gemini_response(GOOD_PAYLOAD)

        result = grade_answer_google(
            RECORD,
            PARSED,
            config=GoogleAIConfig(api_key="k", model="gemini-2.5-flash-lite"),
            transport=transport,
        )
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["provider"], "google-ai-studio")
        self.assertEqual(result["model"], "gemini-2.5-flash-lite")
        self.assertEqual(result["result"]["total_awarded"], 1)
        self.assertIn("gemini-2.5-flash-lite:generateContent", captured["url"])

    def test_api_key_travels_in_the_header_not_the_url(self):
        captured = {}

        def transport(url, headers, body, timeout):
            captured["url"] = url
            captured["headers"] = headers
            return gemini_response(GOOD_PAYLOAD)

        grade_answer_google(
            RECORD, PARSED, config=GoogleAIConfig(api_key="secret-key"), transport=transport
        )
        self.assertEqual(captured["headers"]["x-goog-api-key"], "secret-key")
        self.assertNotIn("secret-key", captured["url"])

    def test_rate_limit_is_flagged_for_the_router(self):
        result = grade_answer_google(
            RECORD, PARSED, config=GoogleAIConfig(api_key="k"), transport=http_error(429)
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["rate_limited"])

    def test_other_errors_are_not_flagged_as_rate_limits(self):
        result = grade_answer_google(
            RECORD, PARSED, config=GoogleAIConfig(api_key="k"), transport=http_error(400)
        )
        self.assertFalse(result["ok"])
        self.assertFalse(result["rate_limited"])

    def test_resource_exhausted_body_counts_as_a_rate_limit(self):
        self.assertTrue(is_rate_limit(403, '{"error":{"status":"RESOURCE_EXHAUSTED"}}'))
        self.assertFalse(is_rate_limit(400, "bad request"))

    def test_invalid_model_json_is_rejected_not_passed_through(self):
        def transport(url, headers, body, timeout):
            return gemini_response({"total_awarded": "not-an-integer"})

        result = grade_answer_google(
            RECORD, PARSED, config=GoogleAIConfig(api_key="k"), transport=transport
        )
        self.assertFalse(result["ok"])
        self.assertIn("invalid grading JSON", result["error"])


class RouterTests(unittest.TestCase):
    def _openrouter_ok(self):
        def transport(url, headers, body, timeout):
            return openrouter_response(GOOD_PAYLOAD)

        return transport

    def test_google_is_preferred_when_both_keys_exist(self):
        def google(url, headers, body, timeout):
            return gemini_response(GOOD_PAYLOAD)

        def openrouter(url, headers, body, timeout):
            raise AssertionError("OpenRouter must not be called when Google succeeds")

        result = grade_answer_routed(
            RECORD,
            PARSED,
            google_config=GoogleAIConfig(api_key="g"),
            openrouter_config=OpenRouterConfig(api_key="o"),
            google_transport=google,
            openrouter_transport=openrouter,
        )
        self.assertEqual(result["provider"], "google-ai-studio")
        self.assertNotIn("fallback_from", result)

    def test_rate_limit_falls_back_to_openrouter(self):
        result = grade_answer_routed(
            RECORD,
            PARSED,
            google_config=GoogleAIConfig(api_key="g"),
            openrouter_config=OpenRouterConfig(api_key="o"),
            google_transport=http_error(429),
            openrouter_transport=self._openrouter_ok(),
        )
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["provider"], "openrouter")
        self.assertEqual(result["fallback_from"]["provider"], "google-ai-studio")

    def test_non_rate_limit_failure_does_not_fall_back(self):
        def openrouter(url, headers, body, timeout):
            raise AssertionError("a 400 is our bug; retrying elsewhere just burns money")

        result = grade_answer_routed(
            RECORD,
            PARSED,
            google_config=GoogleAIConfig(api_key="g"),
            openrouter_config=OpenRouterConfig(api_key="o"),
            google_transport=http_error(400),
            openrouter_transport=openrouter,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["provider"], "google-ai-studio")

    def test_openrouter_is_used_directly_when_no_google_key(self):
        result = grade_answer_routed(
            RECORD,
            PARSED,
            google_config=GoogleAIConfig(api_key=""),
            openrouter_config=OpenRouterConfig(api_key="o"),
            openrouter_transport=self._openrouter_ok(),
        )
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["provider"], "openrouter")

    def test_rate_limited_with_no_fallback_key_explains_itself(self):
        result = grade_answer_routed(
            RECORD,
            PARSED,
            google_config=GoogleAIConfig(api_key="g"),
            openrouter_config=OpenRouterConfig(api_key=""),
            google_transport=http_error(429),
        )
        self.assertFalse(result["ok"])
        self.assertIn("no OPENROUTER_API_KEY", result["error"])

    def test_dry_run_only_when_neither_key_is_set(self):
        result = grade_answer_routed(
            RECORD,
            PARSED,
            google_config=GoogleAIConfig(api_key=""),
            openrouter_config=OpenRouterConfig(api_key=""),
        )
        self.assertTrue(result["dry_run"])


if __name__ == "__main__":
    unittest.main()
