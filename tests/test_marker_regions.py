import unittest

from src.website.marker_regions import (
    MarkerRegionStore,
    extract_regions,
)


def block(block_type, bbox, children=None):
    node = {"block_type": block_type, "bbox": bbox}
    if children is not None:
        node["children"] = children
    return node


def page(bbox, children):
    return {"block_type": "Page", "bbox": bbox, "children": children}


class ExtractRegionsTests(unittest.TestCase):
    def test_keeps_figures_and_code_drops_prose(self):
        document = {
            "block_type": "Document",
            "children": [
                page(
                    [0.0, 0.0, 794.0, 1123.0],
                    [
                        block("Picture", [100.0, 200.0, 300.0, 400.0]),
                        block("Text", [100.0, 420.0, 600.0, 440.0]),
                        block("Table", [100.0, 460.0, 600.0, 560.0]),
                        block("Code", [100.0, 580.0, 600.0, 700.0]),
                    ],
                )
            ],
        }

        regions, page_sizes = extract_regions(document)

        kinds = [r["block_type"] for r in regions[0]]
        self.assertEqual(kinds, ["Picture", "Table", "Code"])
        self.assertEqual(page_sizes[0], (794.0, 1123.0))

    def test_header_and_footer_pictures_are_dropped(self):
        document = {
            "block_type": "Document",
            "children": [
                page(
                    [0.0, 0.0, 794.0, 1123.0],
                    [
                        block("Picture", [10.0, 20.0, 120.0, 80.0]),  # header band
                        block("Picture", [10.0, 1000.0, 120.0, 1050.0]),  # footer band
                        block("Picture", [100.0, 300.0, 300.0, 450.0]),  # real figure
                    ],
                )
            ],
        }

        regions, _ = extract_regions(document)

        self.assertEqual(len(regions[0]), 1)
        self.assertEqual(regions[0][0]["bbox"], [100.0, 300.0, 300.0, 450.0])

    def test_group_children_are_not_descended_into(self):
        document = {
            "block_type": "Document",
            "children": [
                page(
                    [0.0, 0.0, 794.0, 1123.0],
                    [
                        block(
                            "PictureGroup",
                            [100.0, 200.0, 400.0, 500.0],
                            children=[block("Picture", [110.0, 210.0, 390.0, 490.0])],
                        )
                    ],
                )
            ],
        }

        regions, _ = extract_regions(document)

        self.assertEqual(len(regions[0]), 1)
        self.assertEqual(regions[0][0]["block_type"], "PictureGroup")

    def test_missing_document_yields_empty(self):
        regions, page_sizes = extract_regions(None)
        self.assertEqual(regions, {})
        self.assertEqual(page_sizes, {})


class MarkerRegionStoreTests(unittest.TestCase):
    def test_figures_and_code_split_by_page(self):
        store = MarkerRegionStore()
        store._cache["paper"] = {
            0: [
                {"block_type": "Picture", "bbox": [0.0, 0.0, 10.0, 10.0]},
                {"block_type": "Code", "bbox": [0.0, 20.0, 10.0, 30.0]},
            ]
        }
        store._page_sizes["paper"] = {0: (794.0, 1123.0)}

        self.assertEqual(
            [r["block_type"] for r in store.figures_by_page("paper")[0]], ["Picture"]
        )
        self.assertEqual(
            [r["block_type"] for r in store.code_by_page("paper")[0]], ["Code"]
        )
        self.assertEqual(store.page_size("paper", 0), (794.0, 1123.0))


if __name__ == "__main__":
    unittest.main()
