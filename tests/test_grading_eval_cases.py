import unittest

from src.pipeline.grading.eval.cases import CASES


class GradingEvalCaseTests(unittest.TestCase):
    def test_fifteen_cases_across_three_types(self):
        self.assertEqual(len(CASES), 15)
        counts = {}
        for case in CASES:
            counts[case["type"]] = counts.get(case["type"], 0) + 1
        self.assertEqual(counts, {"fill_in": 5, "short": 5, "long": 5})

    def test_keys_are_unique(self):
        keys = [tuple(case["key"]) for case in CASES]
        self.assertEqual(len(keys), len(set(keys)))
        for key in keys:
            self.assertEqual(len(key), 4)  # paper, question, primary, secondary

    def test_each_case_has_high_medium_low(self):
        for case in CASES:
            qualities = [c["quality"] for c in case["candidates"]]
            self.assertEqual(qualities, ["high", "medium", "low"], case["title"])

    def test_predictions_are_monotonic_and_nonnegative(self):
        for case in CASES:
            preds = [c["predicted"] for c in case["candidates"]]
            self.assertEqual(preds, sorted(preds, reverse=True), case["title"])
            self.assertTrue(all(isinstance(p, int) and p >= 0 for p in preds), case["title"])

    def test_every_candidate_has_answer_and_rationale(self):
        for case in CASES:
            for candidate in case["candidates"]:
                self.assertTrue(candidate["answer"].strip(), case["title"])
                self.assertTrue(candidate["rationale"].strip(), case["title"])


if __name__ == "__main__":
    unittest.main()
