import unittest

from src.pipeline.pseudocode_tools.extract_marking_points import (
    extract_structured_marking_points,
    marking_points_from_underlined_spans,
)


def uspan(text, x0, x1, y0):
    return {"text": text, "bbox": [x0, y0, x1, y0 + 12.0]}


class StructuredMarkingPointTests(unittest.TestCase):
    def test_mp_labels_inline_and_on_own_line(self):
        text = (
            "MP1 Function heading and end\n"
            "MP2\nDeclaration of locals\n"
            "MP3 Loop for Count iterations"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [point["text"] for point in result["points"]],
            [
                "Function heading and end",
                "Declaration of locals",
                "Loop for Count iterations",
            ],
        )
        self.assertTrue(all(p["style"] == "mp_label" for p in result["points"]))

    def test_bare_digit_numbered_list_is_extracted(self):
        # Newer 9618 schemes number items without a dot separator.
        text = (
            "PROCEDURE Sort()\n"
            "ENDPROCEDURE\n"
            "Mark as follows:\n"
            "1 Outer loop\n"
            "2 Inner loop\n"
            "3 Correct comparison in a loop"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [point["text"] for point in result["points"]],
            ["Outer loop", "Inner loop", "Correct comparison in a loop"],
        )

    def test_circled_digit_code_lines_are_not_list_items(self):
        # Circled mark digits render inline with example code ("2 OUTPUT ...");
        # they must not become marking points, while the real dotted
        # descriptions after the trigger line must.
        text = (
            "Mark as follows:\n"
            "INPUT StartPos 1\n"
            "2 OUTPUT \" Input new value for position \" 3\n"
            "INPUT NewChar 4\n"
            "Mark points as circled, descriptions as below:\n"
            "1. Two INPUT statements\n"
            "2. Working loop\n"
            "3. OUTPUT prompt (exact text not specified)"
        )

        result = extract_structured_marking_points(text)

        texts = [point["text"] for point in result["points"]]
        self.assertEqual(
            texts,
            ["Two INPUT statements", "Working loop", "OUTPUT prompt (exact text not specified)"],
        )

    def test_max_marks_cap_is_detected(self):
        text = "Max 5 marks\nMP1\nOpen the text file in WRITE mode"

        result = extract_structured_marking_points(text)

        self.assertEqual(result["max_marks"], 5)

    def test_one_mark_bullets_are_high_confidence(self):
        text = (
            "One mark per point:\n"
            "• The array is declared from 1 to 50\n"
            "• Line number: 10"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(len(result["points"]), 2)
        self.assertTrue(all(p["confidence"] == "high" for p in result["points"]))

    def test_code_only_answer_produces_no_points(self):
        text = (
            "FUNCTION MakeString(Count : INTEGER) RETURNS STRING\n"
            "DECLARE MyString : STRING\n"
            "RETURN MyString\n"
            "ENDFUNCTION"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(result["points"], [])

    def test_mp_labels_after_mark_as_follows_header(self):
        # "Mark as follows:" followed by MP-labels must not be swallowed by the
        # list collector (the historic id110 bug).
        text = (
            "PROCEDURE AddNewCustomers()\n"
            "ENDPROCEDURE\n"
            "Mark as follows:\n"
            "MP1 All variables declared with correct type\n"
            "MP2 Open file in read mode and close\n"
            "MP3 Conditional loop with EOF"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [p["text"] for p in result["points"]],
            [
                "All variables declared with correct type",
                "Open file in read mode and close",
                "Conditional loop with EOF",
            ],
        )
        self.assertTrue(all(p["style"] == "mp_label" for p in result["points"]))

    def test_wrapped_mp_cross_reference_merges_and_max_line_stops(self):
        # A wrapped "MP4 to generate ..." line (out of sequence, after MP6) is a
        # cross-reference continuation, and a trailing "Max 8" is not a point.
        text = (
            "Mark as follows:\n"
            "MP6 Extract CustomerID and convert to integer // use count from\n"
            "MP4 to generate last CustomerID stored\n"
            "MP7 A count controlled loop\n"
            "Max 8"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [p["text"] for p in result["points"]],
            [
                "Extract CustomerID and convert to integer // use count from MP4 to generate last CustomerID stored",
                "A count controlled loop",
            ],
        )
        self.assertEqual(result["max_marks"], 8)

    def test_bullets_after_mark_as_follows_header(self):
        text = (
            "PROCEDURE ClearArray()\n"
            "ENDPROCEDURE\n"
            "Mark as follows:\n"
            "• Procedure header\n"
            "• Loop\n"
            "• Assignment within loop"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [p["text"] for p in result["points"]],
            ["Procedure header", "Loop", "Assignment within loop"],
        )

    def test_header_with_leading_and_trailing_context_triggers_list(self):
        text = (
            "PROCEDURE Square()\n"
            "ENDPROCEDURE\n"
            "For loop-based solutions, mark as follows:\n"
            "1 Procedure heading and ending including parameter\n"
            "2 Loop using parameter\n"
            "3 Construct first line"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(len(result["points"]), 3)
        self.assertTrue(all(p["style"] == "numbered_list" for p in result["points"]))

    def test_one_mark_for_each_header_with_inline_max_and_numbered_list(self):
        text = (
            "ENDFUNCTION\n"
            "One mark for each of the following (max 8):\n"
            "1. Function header and end\n"
            "2. Declaration and initialisation of local count variable\n"
            "3. FOR loop for 40 array elements"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(result["max_marks"], 8)
        self.assertEqual(len(result["points"]), 3)

    def test_inline_mp_markers_in_code_produce_no_points(self):
        # Marks shown as gaps in the solution ("One mark per gap") — the MPn
        # tokens are position markers, not describable rubric text.
        text = (
            "DECLARE EasyQ, HardQ : INTEGER\n"
            "FOR EasyQ 0 TO 15 STEP 3\n"
            "MP1 MP2\n"
            "FOR HardQ 0 TO 20 STEP 5\n"
            "MP3 MP4\n"
            "NEXT HardQ MP5\n"
            "NEXT EasyQ\n"
            "Mark as follows:\n"
            "One mark per gap (boldened)"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(result["points"], [])

    def test_expected_output_table_rows_are_not_points(self):
        # A numbered "expected output" demonstration must not become marks.
        text = (
            "One mark for each of the following:\n"
            "1 Correct construction of the string\n"
            "2 Output in a loop\n"
            "Expected output:\n"
            "1 : OUTPUT \"1\"\n"
            "2 : OUTPUT \"22\"\n"
            "3 : OUTPUT \"333\""
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [p["text"] for p in result["points"]],
            ["Correct construction of the string", "Output in a loop"],
        )

    def test_note_and_alternative_lines_do_not_pollute_items(self):
        text = (
            "Mark as follows:\n"
            "MP1 Output final count once only\n"
            "Note: max 8\n"
            "Alternative solution:\n"
            "MP1 Initialise array of 24 elements"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [p["text"] for p in result["points"]],
            ["Output final count once only", "Initialise array of 24 elements"],
        )

    def test_stray_bracket_glyphs_are_stripped(self):
        text = (
            "One mark for each of the following:\n"
            "1 A nested loop including attempt at flip operation «\n"
            "2 « Correct number of iterations"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [p["text"] for p in result["points"]],
            ["A nested loop including attempt at flip operation", "Correct number of iterations"],
        )

    def test_duplicate_alternative_solution_marks_are_deduped(self):
        text = (
            "Mark as follows:\n"
            "1 Open file for read and close\n"
            "2 Conditional loop until EOF\n"
            "Alternative:\n"
            "1 Open file for read and close\n"
            "2 Output result in a loop"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [p["text"] for p in result["points"]],
            [
                "Open file for read and close",
                "Conditional loop until EOF",
                "Output result in a loop",
            ],
        )

    def test_numbered_list_without_header_needs_two_items(self):
        # A single stray numbered line with no rubric header is not a mark.
        single = extract_structured_marking_points("Some heading\n1 Lonely line")
        self.assertEqual(single["points"], [])
        # Two consecutive numbered items are trusted as a list even so.
        pair = extract_structured_marking_points("1 First real point\n2 Second real point")
        self.assertEqual(len(pair["points"]), 2)


class UnderlinedSpanMarkingPointTests(unittest.TestCase):
    def test_one_run_per_line_when_marks_match_lines(self):
        # Three underlined expressions on three lines -> three marks.
        spans = [
            uspan("breakpoint", 174, 232, 118),
            uspan("report/watch window", 377, 478, 131),
            uspan("single stepping", 147, 223, 144),
        ]

        points = marking_points_from_underlined_spans(spans, target_marks=3)

        self.assertEqual(
            [p["text"] for p in points],
            ["breakpoint", "report/watch window", "single stepping"],
        )
        self.assertTrue(all(p["style"] == "underlined" for p in points))

    def test_spans_merge_to_hit_target_marks(self):
        # Five style-split spans across two lines collapse to three marks, and
        # the private-use arrow glyph is normalised and correctly ordered.
        spans = [
            uspan("DECLARE StartDate", 118, 237, 674),
            uspan("DATE", 250, 283, 674),
            uspan("StartDate", 118, 178, 726),
            uspan("\uf0ac", 181, 192, 724),  # slightly higher baseline
            uspan(" SETDATE (15, 11, 2005)", 192, 350, 726),
        ]

        points = marking_points_from_underlined_spans(spans, target_marks=3)

        self.assertEqual(
            [p["text"] for p in points],
            ["DECLARE StartDate", "DATE", "StartDate ← SETDATE (15, 11, 2005)"],
        )

    def test_multiple_words_on_one_line_split_to_target(self):
        spans = [
            uspan("array", 150, 179, 234),
            uspan("records", 191, 231, 234),
            uspan("array", 256, 285, 234),
            uspan("type", 344, 368, 234),
        ]

        points = marking_points_from_underlined_spans(spans, target_marks=2)

        self.assertEqual(len(points), 2)

    def test_fewer_spans_than_marks_keeps_all_spans(self):
        spans = [uspan("breakpoint", 174, 232, 118), uspan("watch window", 377, 478, 131)]

        points = marking_points_from_underlined_spans(spans, target_marks=4)

        self.assertEqual([p["text"] for p in points], ["breakpoint", "watch window"])

    def test_no_target_merges_per_line(self):
        spans = [
            uspan("DECLARE StartDate", 118, 237, 674),
            uspan("DATE", 250, 283, 674),
            uspan("assignment line", 118, 350, 726),
        ]

        points = marking_points_from_underlined_spans(spans, target_marks=None)

        self.assertEqual(
            [p["text"] for p in points],
            ["DECLARE StartDate DATE", "assignment line"],
        )

    def test_empty_spans_yield_no_points(self):
        self.assertEqual(marking_points_from_underlined_spans(None), [])
        self.assertEqual(marking_points_from_underlined_spans([]), [])


if __name__ == "__main__":
    unittest.main()
