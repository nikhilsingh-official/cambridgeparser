import unittest

from src.pipeline.pseudocode_tools.extract_marking_points import (
    declares_style_convention,
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

    def test_alternative_solutions_form_separate_groups(self):
        text = (
            "Mark as follows:\n"
            "1 Open file for read and close\n"
            "2 Conditional loop until EOF\n"
            "Alternative:\n"
            "1 Open file for read and close\n"
            "2 Output result in a loop"
        )

        result = extract_structured_marking_points(text)

        # The alternative keeps its own copy of the shared point: the two
        # rubrics are mutually exclusive, so merging them would turn a 2-mark
        # question into a 3-mark additive list.
        self.assertEqual(
            [(p["alt_group"], p["text"]) for p in result["points"]],
            [
                (0, "Open file for read and close"),
                (0, "Conditional loop until EOF"),
                (1, "Open file for read and close"),
                (1, "Output result in a loop"),
            ],
        )
        self.assertEqual(result["alt_group_count"], 2)

    def test_duplicates_within_one_rubric_are_deduped(self):
        text = (
            "Mark as follows:\n"
            "1 Open file for read and close\n"
            "2 Conditional loop until EOF\n"
            "3 Open file for read and close"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [p["text"] for p in result["points"]],
            ["Open file for read and close", "Conditional loop until EOF"],
        )
        self.assertEqual(result["alt_group_count"], 1)

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


class ForeignContentBoundaryTests(unittest.TestCase):
    """A rubric list must survive the annotations Cambridge prints around it."""

    def test_mp_crossreference_in_brackets_is_not_an_item(self):
        # "(after reasonable attempt at MP3)" wraps, leaving "MP3) in a loop" on
        # its own line. Read as an item it becomes the *only* point, discarding
        # the real five-item list.
        text = (
            "1 mark for each of the following:\n"
            "1 Loop through array elements\n"
            "2 Convert both strings to same case\n"
            "3 Compare array element with parameter in a loop\n"
            "4 Set a flag (or similar) if match found (after reasonable attempt at\n"
            "MP3) in a loop\n"
            "5 Return TRUE or FALSE in all cases"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(len(result["points"]), 5)
        self.assertEqual(result["points"][0]["style"], "numbered_list")
        self.assertIn("MP3", result["points"][3]["text"])

    def test_lone_mp_note_does_not_discard_a_longer_numbered_list(self):
        text = (
            "Mark as follows:\n"
            "1 Procedure heading and ending\n"
            "2 Open both files\n"
            "3 Conditional loop until EOF\n"
            "Note:\n"
            "MP6: Both counts must have been declared and initialised"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [p["text"] for p in result["points"]],
            ["Procedure heading and ending", "Open both files", "Conditional loop until EOF"],
        )

    def test_wrapped_line_starting_with_a_digit_continues_the_item(self):
        text = (
            "Mark as follows:\n"
            "4 Read three lines from OldFile in a loop\n"
            "5 Compare 3rd line read with Status parameter and if not equal write\n"
            "3 lines to NewFile in a loop\n"
            "6 Final output"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(len(result["points"]), 3)
        self.assertTrue(result["points"][1]["text"].endswith("3 lines to NewFile in a loop"))

    def test_mixed_case_routine_header_ends_the_list(self):
        text = (
            "One mark per point:\n"
            "1 Function heading and ending including parameters\n"
            "2 Return Result following a reasonable attempt\n"
            "Function Status(Actual, Min, Max : INTEGER) RETURNS CHAR\n"
            "DECLARE Result : CHAR"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(len(result["points"]), 2)
        self.assertEqual(result["points"][1]["text"], "Return Result following a reasonable attempt")

    def test_prose_about_a_function_heading_is_still_an_item(self):
        # "Function heading (inc parameters) and ending" has the same
        # name-then-bracket shape as a declaration but is a real marking point.
        text = (
            "1 mark for each of the following up to max 5 marks:\n"
            "1 Function heading (inc parameters) and ending\n"
            "2 Declaring local variables\n"
            "3 Return parameter"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(len(result["points"]), 3)
        self.assertEqual(result["points"][0]["text"], "Function heading (inc parameters) and ending")

    def test_plural_notes_heading_is_a_boundary(self):
        text = (
            "1 mark for each of the following:\n"
            "1 Inner loop to search array\n"
            "2 If Rnum not a duplicate then assign to array element and Increment\n"
            "index\n"
            "Notes:\n"
            "Max 5 if statement to generate random number not present"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(len(result["points"]), 2)
        self.assertEqual(
            result["points"][1]["text"],
            "If Rnum not a duplicate then assign to array element and Increment index",
        )


class UnderlineConventionTests(unittest.TestCase):
    def test_the_conventions_own_key_word_is_not_a_marking_point(self):
        # "One mark per <u>underlined</u> word" underlines its own key word.
        spans = [
            uspan("LENGTH(InString)", 118, 237, 300),
            uspan("RETURN OutString", 118, 237, 320),
            uspan("underlined", 118, 180, 400),
        ]

        points = marking_points_from_underlined_spans(spans, target_marks=2)

        self.assertEqual([p["text"] for p in points], ["LENGTH(InString)", "RETURN OutString"])

    def test_underlined_text_only_inside_a_comment_is_dropped(self):
        answer = (
            "IF NextChar >= 'A' AND NextChar <= 'Z'\n"
            "// NextChar = UCASE(NextChar)\n"
            "RETURN OutString"
        )
        spans = [
            uspan("NextChar >= 'A' AND NextChar <= 'Z'", 118, 300, 300),
            uspan("NextChar = UCASE(NextChar)", 118, 300, 320),
            uspan("RETURN OutString", 118, 237, 340),
        ]

        points = marking_points_from_underlined_spans(spans, target_marks=2, answer_text=answer)

        self.assertEqual(
            [p["text"] for p in points],
            ["NextChar >= 'A' AND NextChar <= 'Z'", "RETURN OutString"],
        )

    def test_slash_separated_declarations_become_alternative_groups(self):
        answer = (
            "DECLARE Item : ARRAY [1:2000] OF Component//\n"
            "DECLARE Item : ARRAY [2000] OF Component//\n"
            "DECLARE Item : ARRAY [0:1999] OF Component"
        )
        spans = [
            uspan("DECLARE Item : ARRAY [1:2000] OF Component/", 118, 400, 300),
            uspan("DECLARE Item : ARRAY [2000] OF Component/", 118, 400, 320),
            uspan("DECLARE Item : ARRAY [0:1999] OF Component", 118, 400, 340),
        ]

        points = marking_points_from_underlined_spans(spans, answer_text=answer)

        self.assertEqual([p["alt_group"] for p in points], [0, 1, 2])
        self.assertTrue(all(not p["text"].endswith("/") for p in points))

    def test_language_variants_are_alternative_groups(self):
        answer = (
            "RETURN OutString\n"
            "One mark for each part-statement (shown underlined and bold)\n"
            "VB: Dim Lookup(0 to 127) As CHAR\n"
            "Pascal: Var Lookup: Array[0..127] Of CHAR"
        )
        spans = [
            uspan("RETURN OutString", 118, 237, 300),
            uspan("Dim Lookup(0 to 127) As CHAR", 118, 300, 340),
            uspan("Var Lookup: Array[0..127] Of CHAR", 118, 300, 360),
        ]

        points = marking_points_from_underlined_spans(spans, answer_text=answer)

        self.assertEqual([p["alt_group"] for p in points], [0, 1, 2])

    def test_declares_style_convention(self):
        self.assertTrue(
            declares_style_convention("One mark for each part-statement (shown underlined and bold)")
        )
        self.assertTrue(declares_style_convention("One mark per highlighted part:"))
        self.assertFalse(declares_style_convention("Mark as follows:\n1 Loop over the array"))


class ItemSplittingTests(unittest.TestCase):
    """Rubric items that read like code, and items whose number went missing."""

    def test_in_sequence_items_naming_constructs_are_kept(self):
        # "FOR loop" / "OUTPUT ..." are what the mark is *for*; the code guard
        # used to drop them and silently under-credit the answer.
        text = (
            "One mark for each of the following:\n"
            "1 Initialisation of Count\n"
            "2 FOR loop\n"
            "3 Check column 1 element and increment count\n"
            "4 CASE OF ThisMark ... ENDCASE\n"
            "5 OUTPUT Count together with suitable message"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(len(result["points"]), 5)
        self.assertEqual(result["points"][1]["text"], "FOR loop")
        self.assertEqual(result["points"][4]["text"], "OUTPUT Count together with suitable message")

    def test_out_of_sequence_code_digit_is_still_rejected(self):
        # A circled mark digit in the example solution does not continue the
        # list's numbering, so the code guard still applies to it.
        text = (
            "Mark as follows:\n"
            "1 Two INPUT statements\n"
            "INPUT StartPos 1\n"
            "3 OUTPUT \" Input new value for position \" 3\n"
            "2 Working loop"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(
            [p["text"] for p in result["points"]], ["Two INPUT statements", "Working loop"]
        )

    def test_code_like_bullet_under_a_header_is_an_item(self):
        text = (
            "One mark for:\n"
            "• First line and ENDCASE\n"
            "• All clauses for 1, 2 and 3\n"
            "• 'OTHERWISE' clause\n"
            "• OUTPUT statement"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(len(result["points"]), 4)
        self.assertEqual(result["points"][3]["text"], "OUTPUT statement")

    def test_item_with_a_lost_number_is_promoted_when_undercounting(self):
        text = (
            "Mark as follows:\n"
            "1. Open EmailDetails for READ\n"
            "2. Writing a line to NewEmailDetails in a loop\n"
            "Closing both files"
        )

        result = extract_structured_marking_points(text, expected_marks=3)

        self.assertEqual(
            [p["text"] for p in result["points"]],
            [
                "Open EmailDetails for READ",
                "Writing a line to NewEmailDetails in a loop",
                "Closing both files",
            ],
        )

    def test_no_promotion_when_the_list_already_matches_the_marks(self):
        # The same text, but the marks are already accounted for, so the trailing
        # line is a wrap and must stay attached.
        text = (
            "Mark as follows:\n"
            "1. Open EmailDetails for READ\n"
            "2. Writing a line to NewEmailDetails in a loop\n"
            "Closing both files"
        )

        result = extract_structured_marking_points(text, expected_marks=2)

        self.assertEqual(len(result["points"]), 2)
        self.assertTrue(result["points"][1]["text"].endswith("Closing both files"))

    def test_genuine_wraps_are_never_promoted(self):
        # Lowercase start, an unclosed bracket, and a trailing conjunction each
        # mark the next line as a continuation even while undercounting.
        text = (
            "Mark as follows:\n"
            "1 Avoid checking uninitialised elements // initialisation to rogue value\n"
            "at start of algorithm\n"
            "2 OUTPUT final message after loop (exact text not specified but must include\n"
            "NumToChange or loop counter if correct)\n"
            "3 Assign the value to the element and\n"
            "Increment the index"
        )

        result = extract_structured_marking_points(text, expected_marks=8)

        self.assertEqual(len(result["points"]), 3)
        self.assertTrue(result["points"][0]["text"].endswith("at start of algorithm"))
        self.assertTrue(result["points"][1]["text"].endswith("if correct)"))
        self.assertTrue(result["points"][2]["text"].endswith("and Increment the index"))

    def test_up_to_max_marks_header_declares_a_cap(self):
        text = (
            "1 mark for each of the following up to max 5 marks:\n"
            "1 Function heading (inc parameters) and ending\n"
            "2 Declaring local variables\n"
            "3 Return parameter"
        )

        result = extract_structured_marking_points(text)

        self.assertEqual(result["max_marks"], 5)


class DeclarationSplittingTests(unittest.TestCase):
    """A whole declaration underlined in one run still carries several marks."""

    def test_parameter_list_splits_per_parameter(self):
        spans = [uspan("PROCEDURE SubA (A : STRING, B : INTEGER, BYREF C : CHAR)", 97, 473, 432)]

        points = marking_points_from_underlined_spans(spans, target_marks=3)

        self.assertEqual(
            [p["text"] for p in points],
            ["PROCEDURE SubA (A : STRING", "B : INTEGER", "BYREF C : CHAR)"],
        )

    def test_returns_clause_splits_before_parameters(self):
        spans = [uspan("Function SubB (D : STRING, E : INTEGER) RETURNS BOOLEAN", 97, 473, 432)]

        points = marking_points_from_underlined_spans(spans, target_marks=3)

        self.assertEqual(
            [p["text"] for p in points],
            ["Function SubB (D : STRING", "E : INTEGER)", "RETURNS BOOLEAN"],
        )

    def test_array_declaration_splits_before_of(self):
        spans = [uspan("DECLARE Rental : ARRAY[1:500] OF RentalRecord", 115, 419, 322)]

        points = marking_points_from_underlined_spans(spans, target_marks=2)

        self.assertEqual(
            [p["text"] for p in points],
            ["DECLARE Rental : ARRAY[1:500]", "OF RentalRecord"],
        )

    def test_split_spreads_across_a_header_wrapped_over_two_lines(self):
        spans = [
            uspan("FUNCTION CardPayment (ParamA : REAL, ParamB : STRING)", 118, 475, 615),
            uspan("BOOLEAN", 171, 224, 627),
        ]

        points = marking_points_from_underlined_spans(spans, target_marks=3)

        self.assertEqual(
            [p["text"] for p in points],
            ["FUNCTION CardPayment (ParamA : REAL", "ParamB : STRING)", "BOOLEAN"],
        )

    def test_runs_already_matching_the_marks_are_left_alone(self):
        spans = [
            uspan("DECLARE Result : ARRAY", 118, 250, 300),
            uspan("[0:99, 0:1]", 260, 330, 300),
            uspan("OF STRING", 340, 410, 300),
        ]

        points = marking_points_from_underlined_spans(spans, target_marks=3)

        # The comma inside the bounds must not be used: the runs are already the marks.
        self.assertEqual(
            [p["text"] for p in points],
            ["DECLARE Result : ARRAY", "[0:99, 0:1]", "OF STRING"],
        )

    def test_supplementary_alternative_groups_are_not_force_split(self):
        # The VB/Pascal restatements are worth a mark each, not the whole
        # question again, so a group that already has its marks stops the split.
        answer = (
            "RETURN OutString\n"
            "VB: Dim Lookup(0 to 127, 1) As CHAR"
        )
        spans = [
            uspan("RETURN OutString", 118, 237, 300),
            uspan("Dim Lookup(0 to 127, 1) As CHAR", 118, 300, 340),
        ]

        points = marking_points_from_underlined_spans(spans, target_marks=1, answer_text=answer)

        self.assertEqual([p["alt_group"] for p in points], [0, 1])
        self.assertEqual(points[1]["text"], "Dim Lookup(0 to 127, 1) As CHAR")

    def test_a_run_without_syntax_breaks_is_left_whole(self):
        spans = [uspan("Correct comparison", 118, 237, 300)]

        points = marking_points_from_underlined_spans(spans, target_marks=4)

        self.assertEqual([p["text"] for p in points], ["Correct comparison"])


class DeclaredMaxTests(unittest.TestCase):
    """Caps written without a bracket or "up to".

    Cambridge routinely lists more criteria than marks and states the cap in
    prose, either above the list or on a trailing note. The cap is the scheme's
    own design, so recording it keeps the list from reading as over-expansion.
    """

    def _max(self, text):
        return extract_structured_marking_points(text)["max_marks"]

    def test_trailing_note_declares_the_cap(self):
        text = (
            "1 mark for each of the following:\n"
            "1 Function heading, including return type and function end\n"
            "2 Loop counting spaces until word found\n"
            "3 Return Index following a reasonable attempt\n"
            "Note: Max 7 marks"
        )
        self.assertEqual(self._max(text), 7)

    def test_cap_without_the_word_marks(self):
        self.assertEqual(self._max("Mark as follows:\n1 Open the file\nNote: max 8"), 8)

    def test_cap_inside_the_mark_as_follows_header(self):
        text = "Mark as follows Max 6 marks:\n1 Procedure heading and ending\n2 Input ThisNum"
        self.assertEqual(self._max(text), 6)
        self.assertEqual(self._max("Mark as follows Max 7:\n1 Convert parameter to a number"), 7)

    def test_conditional_penalty_is_not_a_cap(self):
        # "Max 7 if X" withholds a mark for a specific fault; it does not say
        # the list is capped at seven.
        text = (
            "1 mark for each of the following:\n"
            "1 Function heading\n"
            "2 Count the characters\n"
            "Note: Max 7 if CharCount not used to store count"
        )
        self.assertIsNone(self._max(text))
        self.assertIsNone(self._max("Note: Max 4 if function declaration incorrect"))

    def test_max_inside_a_marking_point_is_not_a_cap(self):
        text = "Mark as follows:\n1 Compare new value with Max 255 and limit\n2 Return a BOOLEAN"
        self.assertIsNone(self._max(text))


if __name__ == "__main__":
    unittest.main()
