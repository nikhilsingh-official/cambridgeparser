import unittest

from src.pipeline.pseudocode_tools.extract_marking_points import (
    extract_structured_marking_points,
)


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


if __name__ == "__main__":
    unittest.main()
