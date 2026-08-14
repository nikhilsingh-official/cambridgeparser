"""Load Marker layout regions for semantic region detection.

Marker is used purely as a layout/region detector here: we only care *where*
figures, diagrams and tables are, never Marker's own text. The normalized
Marker output shares the 794x1123 image coordinate space used by the qsplitter
word boxes and the rendered screenshots, so figure regions can be intersected
with a segment's word boxes without any coordinate transform.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.resources.paths import NORMALIZED_MARKER_OUTPUT_DIR

# Marker block types that must be rendered as cropped images, never as text.
# Their contained text is deliberately excluded from the reconstructed layer.
FIGURE_BLOCK_TYPES = frozenset(
    {
        "Picture",
        "PictureGroup",
        "Figure",
        "FigureGroup",
        "Table",
        "TableGroup",
    }
)

# Marker block types whose text is code/pseudocode; rendered in a fixed-width
# font so indentation and pseudocode structure read naturally.
CODE_BLOCK_TYPES = frozenset({"Code"})

# Region types we keep from the Marker tree (everything else is ignored).
KEPT_BLOCK_TYPES = FIGURE_BLOCK_TYPES | CODE_BLOCK_TYPES

DEFAULT_MARKER_ROOT = NORMALIZED_MARKER_OUTPUT_DIR

# Header/footer bands (image-space y) hold logos, page numbers and barcodes that
# Marker also tags as Picture; they are never part of a question's figures.
HEADER_BAND_BOTTOM = 95.0
FOOTER_BAND_TOP = 975.0
PAGE_HEIGHT = 1123.0


class MarkerRegionStore:
    """Lazily loads and caches figure/table regions per paper."""

    def __init__(self, marker_root: Path = DEFAULT_MARKER_ROOT) -> None:
        self.marker_root = marker_root
        self._cache: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}
        self._page_sizes: Dict[str, Dict[int, Tuple[float, float]]] = {}

    def _marker_path(self, paper_code: str) -> Path:
        return self.marker_root / paper_code / f"{paper_code}.json"

    def _ensure_loaded(self, paper_code: str) -> None:
        if paper_code in self._cache:
            return
        path = self._marker_path(paper_code)
        document = None
        if path.is_file():
            with path.open() as handle:
                document = json.load(handle)
        regions, page_sizes = extract_regions(document)
        self._cache[paper_code] = regions
        self._page_sizes[paper_code] = page_sizes

    def regions_by_page(self, paper_code: str) -> Dict[int, List[Dict[str, Any]]]:
        self._ensure_loaded(paper_code)
        return self._cache[paper_code]

    def regions_for_page(self, paper_code: str, page_index: int) -> List[Dict[str, Any]]:
        return self.regions_by_page(paper_code).get(page_index, [])

    def page_size(self, paper_code: str, page_index: int) -> Optional[Tuple[float, float]]:
        """Return the (width, height) of a page in image space, if known."""

        self._ensure_loaded(paper_code)
        return self._page_sizes.get(paper_code, {}).get(page_index)

    def figures_by_page(self, paper_code: str) -> Dict[int, List[Dict[str, Any]]]:
        return _filter_by_page(self.regions_by_page(paper_code), FIGURE_BLOCK_TYPES)

    def code_by_page(self, paper_code: str) -> Dict[int, List[Dict[str, Any]]]:
        return _filter_by_page(self.regions_by_page(paper_code), CODE_BLOCK_TYPES)


def _filter_by_page(
    regions_by_page: Dict[int, List[Dict[str, Any]]], block_types: frozenset
) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    for page_index, regions in regions_by_page.items():
        kept = [r for r in regions if r["block_type"] in block_types]
        if kept:
            result[page_index] = kept
    return result


def _is_header_or_footer(bbox: List[float]) -> bool:
    _, y0, _, y1 = bbox
    if y1 <= HEADER_BAND_BOTTOM:
        return True
    if y0 >= FOOTER_BAND_TOP:
        return True
    return False


def extract_regions(
    document: Optional[Dict[str, Any]],
) -> Tuple[Dict[int, List[Dict[str, Any]]], Dict[int, Tuple[float, float]]]:
    """Return ({page_index: [region, ...]}, {page_index: (width, height)}).

    Only figure/diagram/table and code blocks survive, and header/footer
    decorations are dropped. Nested group children are not descended into once a
    group is accepted, so a PictureGroup is emitted as a single region. Page
    sizes come from each Page block's own bbox in image space.
    """

    regions: Dict[int, List[Dict[str, Any]]] = {}
    page_sizes: Dict[int, Tuple[float, float]] = {}
    if not isinstance(document, dict):
        return regions, page_sizes

    pages = document.get("children") or []
    for page_index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        page_bbox = page.get("bbox")
        if _valid_bbox(page_bbox):
            page_sizes[page_index] = (float(page_bbox[2]), float(page_bbox[3]))
        page_regions: List[Dict[str, Any]] = []
        for block in page.get("children") or []:
            _collect_blocks(block, page_regions)
        if page_regions:
            regions[page_index] = page_regions
    return regions, page_sizes


def _collect_blocks(block: Any, out: List[Dict[str, Any]]) -> None:
    if not isinstance(block, dict):
        return
    block_type = block.get("block_type")
    bbox = block.get("bbox")
    if block_type in KEPT_BLOCK_TYPES and _valid_bbox(bbox):
        if not _is_header_or_footer(bbox):
            out.append({"block_type": block_type, "bbox": [float(v) for v in bbox]})
        # Do not descend into an accepted figure/table/code group.
        return
    for child in block.get("children") or []:
        _collect_blocks(child, out)


def _valid_bbox(bbox: Any) -> bool:
    return (
        isinstance(bbox, (list, tuple))
        and len(bbox) == 4
        and all(isinstance(v, (int, float)) for v in bbox)
        and bbox[2] > bbox[0]
        and bbox[3] > bbox[1]
    )
