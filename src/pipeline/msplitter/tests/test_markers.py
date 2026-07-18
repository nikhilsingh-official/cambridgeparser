import unittest

from src.pipeline.msplitter.markers import extract_leading_question_number


def make_chars(text: str):
    chars = []
    cursor = 0.0
    for char in text:
        chars.append(
            {
                "text": char,
                "bbox": [cursor, 0.0, cursor + 1.0, 1.0],
                "bbox_valid": True,
            }
        )
        cursor += 1.0
    return chars


class MarkerExtractionTests(unittest.TestCase):
    def test_accepts_question_number_before_primary_subpart_on_same_line(self):
        marker = extract_leading_question_number(make_chars("2 (a) Draw a logic circuit"))
        self.assertIsNotNone(marker)
        self.assertEqual(marker["text"], "2")


if __name__ == "__main__":
    unittest.main()
