import unittest

from PIL import Image, ImageDraw

from src.pipeline.pseudocode_tools.render_pseudocode_question_screenshots import (
    _is_blank_crop,
    _page_has_centered_blank_notice,
)


class FakeRect:
    width = 600.0


class FakePage:
    rect = FakeRect()

    def __init__(self, blocks):
        self.blocks = blocks

    def get_text(self, mode):
        self.assert_mode = mode
        return self.blocks


class PseudocodeRendererTests(unittest.TestCase):
    def test_detects_blank_white_crop(self):
        image = Image.new("RGB", (400, 400), "white")

        self.assertTrue(
            _is_blank_crop(
                image,
                pixel_threshold=245,
                nonwhite_ratio=0.003,
            )
        )

    def test_keeps_crop_with_visible_content(self):
        image = Image.new("RGB", (400, 400), "white")
        draw = ImageDraw.Draw(image)
        for row in range(20, 260, 20):
            draw.rectangle((20, row, 380, row + 5), fill="black")

        self.assertFalse(
            _is_blank_crop(
                image,
                pixel_threshold=245,
                nonwhite_ratio=0.003,
            )
        )

    def test_detects_centered_blank_page_notice(self):
        page = FakePage([(260.0, 60.0, 340.0, 80.0, "BLANK PAGE\n", 0, 0)])

        self.assertTrue(_page_has_centered_blank_notice(page))

    def test_ignores_cover_page_blank_page_sentence(self):
        page = FakePage(
            [
                (
                    160.0,
                    740.0,
                    440.0,
                    755.0,
                    "This document consists of 14 printed pages and 2 blank pages.",
                    0,
                    0,
                )
            ]
        )

        self.assertFalse(_page_has_centered_blank_notice(page))


if __name__ == "__main__":
    unittest.main()
