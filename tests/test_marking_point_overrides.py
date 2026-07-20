import unittest

from src.pipeline.pseudocode_tools.marking_point_overrides import (
    _OVERRIDES,
    _VERIFIED_OVER_LIST,
    is_verified_over_list,
    override_marking_points,
)


class MarkingPointOverrideTests(unittest.TestCase):
    def test_unknown_record_returns_none(self):
        self.assertIsNone(override_marking_points("9608_s17_qp_21", "3", None, None))

    def test_known_record_returns_structured_points(self):
        result = override_marking_points("9618_w22_qp_22", "5", None, None)
        self.assertIsNotNone(result)
        self.assertEqual(len(result["points"]), 4)
        first = result["points"][0]
        self.assertEqual(first["id"], "mp1")
        self.assertEqual(first["style"], "manual_override")
        self.assertEqual(first["marks"], 1)
        self.assertTrue(first["text"])

    def test_container_record_supplies_missing_max_marks(self):
        result = override_marking_points("9608_s20_qp_21", "5", "(a)", None)
        self.assertEqual(result["max_marks"], 8)
        self.assertEqual(len(result["points"]), 8)

    def test_question_marker_is_normalised_to_string(self):
        # Records carry the question marker as a string; an int key still hits.
        self.assertIsNotNone(override_marking_points("9618_s23_qp_22", 2, "(a)", None))

    def test_point_counts_match_declared_mark_totals(self):
        # Each curated entry should list as many points as marks where a total is
        # known, so the grader is never handed fewer criteria than marks.
        expected = {
            ("9618_w22_qp_22", "5", None, None): 4,
            ("9618_w24_qp_22", "3", "(b)", None): 4,
            ("9618_w25_qp_22", "4", "(b)", None): 5,
            ("9608_s20_qp_23", "3", "(b)", "(ii)"): 2,
        }
        for key, count in expected.items():
            self.assertEqual(len(_OVERRIDES[key]["points"]), count, key)

    def test_replaces_parse_is_off_by_default_and_declared_where_used(self):
        # The flag silences the extractor for that record, so it stays rare and
        # every entry carrying it must also declare its mark total.
        fallback = override_marking_points("9618_w25_qp_22", "4", "(b)", None)
        self.assertFalse(fallback["replaces_parse"])

        replacing = [key for key, entry in _OVERRIDES.items() if entry.get("replaces_parse")]
        self.assertEqual(
            sorted(replacing),
            [
                ("9618_w21_qp_22", "1", "(c)", None),
                ("9618_w24_qp_23", "4", "(a)", None),
                ("9618_w25_qp_23", "3", None, None),
            ],
        )
        for key in replacing:
            entry = _OVERRIDES[key]
            self.assertEqual(len(entry["points"]), entry["max_marks"], key)


class VerifiedOverListTests(unittest.TestCase):
    """The annotation for schemes that out-list their marks without saying so."""

    def test_listed_records_are_recognised(self):
        self.assertTrue(is_verified_over_list("9608_s18_qp_21", "6", "(b)", None))
        self.assertTrue(is_verified_over_list("9618_w23_qp_21", 6, "(a)", None))
        self.assertFalse(is_verified_over_list("9608_s18_qp_21", "6", "(a)", None))
        self.assertFalse(is_verified_over_list("9608_x00_qp_00", "1", None, None))

    def test_annotation_never_supplies_marking_points(self):
        # It records that a parse was checked; it must not replace the parse,
        # or those records would stop benefiting from extractor improvements.
        for key in _VERIFIED_OVER_LIST:
            self.assertNotIn(key, _OVERRIDES)
            self.assertIsNone(override_marking_points(*key))


if __name__ == "__main__":
    unittest.main()
