import unittest

from src.pipeline.pseudocode_tools.select_pseudocode_writing import (
    _compile_rules,
    _extract_records_from_payload,
    DEFAULT_NEGATIVE_RULES,
    DEFAULT_POSITIVE_RULES,
)


def node(text, content_text):
    return {
        "text": text,
        "bbox": [0.0, 0.0, 10.0, 10.0],
        "page_index": 0,
        "content_text": content_text,
        "content_bbox": [0.0, 0.0, 100.0, 100.0],
        "content_source": "text",
    }


def decisions_by_key(records):
    result = {}
    for record in records:
        key = (
            record["segment_kind"],
            record["question_marker"],
            record["primary_marker"],
            record["secondary_marker"],
        )
        result[key] = record["decision"]
    return result


class SupersedeAncestorTests(unittest.TestCase):
    def setUp(self):
        self.positive = _compile_rules(DEFAULT_POSITIVE_RULES)
        self.negative = _compile_rules(DEFAULT_NEGATIVE_RULES)

    def _run(self, payload):
        return decisions_by_key(
            _extract_records_from_payload(payload, self.positive, self.negative)
        )

    def test_question_level_is_superseded_by_selected_primary(self):
        # A whole-question content_text concatenates its subparts, so a
        # pseudocode-writing subpart (b) makes the question node match the same
        # positive phrase. Only the specific subpart should remain selected.
        payload = {
            "paper_code": "9608_s17_qp_21",
            "questions": [
                {
                    "question": node(
                        "4",
                        "(a) A structure chart is a tool used in modular program design.\n"
                        "State three pieces of information...\n"
                        "(b) Use pseudocode to write the function CardPayment.",
                    ),
                    "primary_subparts": [
                        {
                            "primary": node(
                                "(a)",
                                "A structure chart is a tool used in modular program design.\n"
                                "State three pieces of information...",
                            ),
                            "secondary_subparts": [],
                        },
                        {
                            "primary": node(
                                "(b)",
                                "Use pseudocode to write the function CardPayment.",
                            ),
                            "secondary_subparts": [],
                        },
                    ],
                }
            ],
        }

        decisions = self._run(payload)

        self.assertEqual(decisions[("question", "4", None, None)], "superseded")
        self.assertEqual(decisions[("primary", "4", "(b)", None)], "selected")
        self.assertEqual(decisions[("primary", "4", "(a)", None)], "rejected")

    def test_flat_question_without_subparts_stays_selected(self):
        payload = {
            "paper_code": "9608_s17_qp_21",
            "questions": [
                {
                    "question": node(
                        "3",
                        "A string conversion function, StringClean, is to be written.\n"
                        "Complete the pseudocode using relevant built-in functions.",
                    ),
                    "primary_subparts": [],
                }
            ],
        }

        decisions = self._run(payload)

        self.assertEqual(decisions[("question", "3", None, None)], "selected")

    def test_primary_is_superseded_by_selected_secondary(self):
        payload = {
            "paper_code": "9618_s21_qp_21",
            "questions": [
                {
                    "question": node("5", "Stem with no write intent."),
                    "primary_subparts": [
                        {
                            "primary": node(
                                "(a)",
                                "Some context.\n(ii) Write pseudocode for the loop.",
                            ),
                            "secondary_subparts": [
                                {
                                    "secondary": node("(i)", "Some context."),
                                    "secondary_subparts": [],
                                },
                                {
                                    "secondary": node(
                                        "(ii)", "Write pseudocode for the loop."
                                    ),
                                    "secondary_subparts": [],
                                },
                            ],
                        }
                    ],
                }
            ],
        }

        decisions = self._run(payload)

        self.assertEqual(decisions[("primary", "5", "(a)", None)], "superseded")
        self.assertEqual(decisions[("secondary", "5", "(a)", "(ii)")], "selected")

    def test_review_ancestor_is_not_touched(self):
        # An ancestor that only reaches "review" (a negative phrase from another
        # subpart) is already excluded from final records, so it stays as-is
        # rather than being relabelled superseded.
        payload = {
            "paper_code": "9608_s17_qp_21",
            "questions": [
                {
                    "question": node(
                        "1",
                        "(b) Describe the purpose of the loop.\n"
                        "(c) Using pseudocode, write a pre-condition loop.",
                    ),
                    "primary_subparts": [
                        {
                            "primary": node(
                                "(b)", "Describe the purpose of the loop."
                            ),
                            "secondary_subparts": [],
                        },
                        {
                            "primary": node(
                                "(c)", "Using pseudocode, write a pre-condition loop."
                            ),
                            "secondary_subparts": [],
                        },
                    ],
                }
            ],
        }

        decisions = self._run(payload)

        self.assertEqual(decisions[("question", "1", None, None)], "review")
        self.assertEqual(decisions[("primary", "1", "(c)", None)], "selected")


if __name__ == "__main__":
    unittest.main()
