import unittest

from src.pipeline.analysis.diagnostics.validate_marking_points import audit_record


def record(points, answer_text="", max_marks=None, marks_value=None):
    return {
        "id": 1,
        "paper_code": "9608_x00_qp_00",
        "segment_key": {"question_marker": "1", "primary_marker": None, "secondary_marker": None},
        "mark_scheme": {
            "marking_points": [
                {"id": f"mp{i}", "text": t, "style": s}
                for i, (t, s) in enumerate(points, start=1)
            ],
            "answer_text": answer_text,
            "max_marks": max_marks,
            "marks_value": marks_value,
        },
    }


def N(*texts, style="numbered_list"):
    return [(t, style) for t in texts]


class ValidateMarkingPointsTests(unittest.TestCase):
    def test_clean_record_has_no_flags(self):
        row = audit_record(record(N("Loop over array", "Compare elements", "Return flag"), max_marks=3))
        self.assertEqual(row["flags"], [])
        self.assertEqual(row["severity"], "none")

    def test_meta_and_fragment_are_high(self):
        meta = audit_record(record(N("Correct heading", "underlined"), max_marks=2))
        self.assertIn("meta_mp", meta["flags"])
        self.assertEqual(meta["severity"], "high")
        frag = audit_record(record(N("5", "GB[Index]"), max_marks=2))
        self.assertIn("fragment_mp", frag["flags"])

    def test_over_expansion_when_more_points_than_cap(self):
        row = audit_record(record(N("a1", "b2", "c3", "d4", "e5"), max_marks=3))
        self.assertIn("over_expansion", row["flags"])
        self.assertEqual(row["severity"], "high")

    def test_undercount_is_medium(self):
        row = audit_record(record(N("only one point"), max_marks=4))
        self.assertIn("undercount", row["flags"])
        self.assertEqual(row["severity"], "medium")

    def test_lone_mp_discarding_numbered_list(self):
        answer = "Mark as follows:\n1 First item\n2 Second item\n3 Third item"
        row = audit_record(record([("in a loop", "mp_label")], answer_text=answer, max_marks=5))
        self.assertIn("lone_mp_discarded_list", row["flags"])

    def test_rubric_selection_mismatch_flags_style_convention_with_text_list(self):
        # Answer declares an underline convention but points are a text list.
        answer = "One mark for each part-statement shown underlined and bold\nMark as follows:\n1 Foo\n2 Bar"
        row = audit_record(record(N("Two INPUT statements", "Working loop"), answer_text=answer, max_marks=6))
        self.assertIn("rubric_selection_mismatch", row["flags"])
        self.assertEqual(row["severity"], "high")

    def test_underline_style_with_convention_is_not_mismatch(self):
        answer = "One mark per underlined part"
        row = audit_record(record([("DECLARE StartDate", "underlined")], answer_text=answer, max_marks=3))
        self.assertNotIn("rubric_selection_mismatch", row["flags"])

    def test_appended_content_detects_trailing_header_or_note(self):
        header = audit_record(record(N("Return Result Function Status(Actual, Min, Max)"), max_marks=6))
        self.assertIn("appended_content", header["flags"])
        note = audit_record(record(N("Increment index Notes:"), max_marks=6))
        self.assertIn("appended_content", note["flags"])

    def test_specific_one_mark_for_phrasing_is_not_meta(self):
        # "One mark for TYPE and ENDTYPE statements" is a real, specific MP.
        row = audit_record(record(N("One mark for TYPE and ENDTYPE statements"), max_marks=4))
        self.assertNotIn("meta_mp", row["flags"])


if __name__ == "__main__":
    unittest.main()
