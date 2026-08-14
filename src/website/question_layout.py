"""Reconstruct a question's on-page layout from qsplitter word boxes.

The goal is a text layer that visually resembles the original PDF: words keep
their original positions (line breaks, indentation, relative spacing) so the
text can be selected and copied, blank dotted/underscored runs become
interactive input fields, and Marker's figure/diagram/table regions are carved
out to be shown as cropped images instead of garbled text.

Everything here works in the shared 794x1123 image coordinate space, so the
output positions line up with both the rendered screenshots and the figure
crops taken straight from the PDF. The builder is a pure function of its inputs
(word boxes + figure regions) so it can be unit-tested without a PDF or Marker
on disk.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.resources.question_segments import find_qp_node, find_qp_question

# A blank is a run of dotted-leader / underscore fill characters. Cambridge uses
# dotted leaders almost everywhere and underscores occasionally; four or more in
# a row is well clear of an ellipsis in ordinary prose.
BLANK_CHARS = ".·…_․‥"
BLANK_RUN = re.compile(f"[{re.escape(BLANK_CHARS)}]{{4,}}")

# Padding around the reconstructed content, in image-space units.
CANVAS_PADDING = 6.0


def find_segment_node(
    qp_payload: Dict[str, Any], segment_key: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Locate the qsplitter node for a record's segment_key."""

    question_entry = find_qp_question(qp_payload, segment_key.get("question_marker"))
    if question_entry is None:
        return None
    return find_qp_node(
        question_entry,
        segment_key.get("segment_kind") or "question",
        segment_key.get("primary_marker"),
        segment_key.get("secondary_marker"),
    )


def build_question_layout(
    node: Dict[str, Any],
    figure_regions_by_page: Dict[int, List[Dict[str, Any]]],
    code_regions_by_page: Optional[Dict[int, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Build a positioned layout model for one question segment.

    ``figure_regions_by_page`` maps page_index to Marker figure/table regions
    (see :mod:`marker_regions`); ``code_regions_by_page`` maps page_index to
    Marker code regions, whose tokens are flagged for fixed-width rendering.
    Returns a JSON-serialisable layout with one entry per page, each carrying
    figure crops and reading-ordered text/blank tokens in canvas-local
    coordinates.
    """

    word_boxes = node.get("content_word_boxes") or []
    page_bboxes = _page_bboxes(node)
    code_regions_by_page = code_regions_by_page or {}

    figure_index = 0
    blank_count = 0
    pages: List[Dict[str, Any]] = []

    for page_index in _ordered_pages(word_boxes):
        words = [w for w in word_boxes if w.get("page_index") == page_index]
        if not words:
            continue

        content_bbox = page_bboxes.get(page_index)
        figures = _figures_for_page(
            figure_regions_by_page.get(page_index, []), words, content_bbox
        )
        code_regions = code_regions_by_page.get(page_index, [])

        kept_words = [w for w in words if not _inside_any(w.get("bbox"), figures)]
        if not kept_words and not figures:
            continue

        origin, size = _canvas_extent(kept_words, figures)
        page_figures = []
        for fig in figures:
            page_figures.append(
                {
                    "index": figure_index,
                    "block_type": fig["block_type"],
                    "page_index": page_index,
                    "bbox": fig["bbox"],
                    **_local_rect(fig["bbox"], origin),
                }
            )
            figure_index += 1

        tokens, page_blanks = _tokens_for_words(kept_words, origin, code_regions)
        blank_count += page_blanks

        pages.append(
            {
                "page_index": page_index,
                "origin": list(origin),
                "width": size[0],
                "height": size[1],
                "figures": page_figures,
                "tokens": tokens,
            }
        )

    return {
        "pages": pages,
        "figure_count": figure_index,
        "blank_count": blank_count,
        "has_blanks": blank_count > 0,
    }


def _page_bboxes(node: Dict[str, Any]) -> Dict[int, List[float]]:
    result: Dict[int, List[float]] = {}
    for page in node.get("content_pages") or []:
        idx = page.get("page_index")
        if isinstance(idx, int) and _valid_bbox(page.get("bbox")):
            result[idx] = [float(v) for v in page["bbox"]]
    return result


def _ordered_pages(word_boxes: Sequence[Dict[str, Any]]) -> List[int]:
    seen: List[int] = []
    for w in word_boxes:
        idx = w.get("page_index")
        if isinstance(idx, int) and idx not in seen:
            seen.append(idx)
    return sorted(seen)


def _figures_for_page(
    regions: Sequence[Dict[str, Any]],
    words: Sequence[Dict[str, Any]],
    content_bbox: Optional[List[float]],
) -> List[Dict[str, Any]]:
    """Keep figure regions that belong to this segment's content band."""

    if not words:
        return []
    word_top = min(w["bbox"][1] for w in words if _valid_bbox(w.get("bbox")))
    word_bottom = max(w["bbox"][3] for w in words if _valid_bbox(w.get("bbox")))
    # Allow figures a little past the last text line (diagrams often trail the
    # prompt) but not the whole rest of the page.
    band_top = word_top - 200.0
    band_bottom = word_bottom + 120.0

    kept: List[Dict[str, Any]] = []
    for region in regions:
        bbox = region.get("bbox")
        if not _valid_bbox(bbox):
            continue
        if content_bbox is not None and not _intersects(bbox, content_bbox):
            continue
        if bbox[3] < band_top or bbox[1] > band_bottom:
            continue
        kept.append(region)
    return kept


def _canvas_extent(
    words: Sequence[Dict[str, Any]], figures: Sequence[Dict[str, Any]]
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    boxes = [w["bbox"] for w in words if _valid_bbox(w.get("bbox"))]
    boxes += [f["bbox"] for f in figures if _valid_bbox(f.get("bbox"))]
    if not boxes:
        return (0.0, 0.0), (0.0, 0.0)
    left = min(b[0] for b in boxes) - CANVAS_PADDING
    top = min(b[1] for b in boxes) - CANVAS_PADDING
    right = max(b[2] for b in boxes) + CANVAS_PADDING
    bottom = max(b[3] for b in boxes) + CANVAS_PADDING
    return (left, top), (right - left, bottom - top)


def _tokens_for_words(
    words: Sequence[Dict[str, Any]],
    origin: Tuple[float, float],
    code_regions: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int]:
    ordered = sorted(
        (w for w in words if _valid_bbox(w.get("bbox")) and (w.get("text") or "")),
        key=_reading_key,
    )
    line_numbers = _sequential_line_index(ordered)

    tokens: List[Dict[str, Any]] = []
    blank_count = 0
    for line_no, word in zip(line_numbers, ordered):
        mono = _inside_any(word.get("bbox"), code_regions)
        for token in _split_token(word):
            token["line"] = line_no
            if mono:
                token["mono"] = True
            token.update(_local_rect(token.pop("_bbox"), origin))
            if token["kind"] == "blank":
                blank_count += 1
            tokens.append(token)
    return tokens, blank_count


def _reading_key(word: Dict[str, Any]) -> Tuple[float, float]:
    line_id = word.get("line_id")
    bbox = word["bbox"]
    if isinstance(line_id, (list, tuple)) and len(line_id) == 2:
        return (float(line_id[1]), bbox[0])
    return (round(bbox[1] / 3.0), bbox[0])


def _sequential_line_index(ordered: Sequence[Dict[str, Any]]) -> List[int]:
    numbers: List[int] = []
    current = -1
    prev_key: Optional[float] = None
    for word in ordered:
        key = _reading_key(word)[0]
        if prev_key is None or key != prev_key:
            current += 1
            prev_key = key
        numbers.append(current)
    return numbers


def _split_token(word: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = word["text"]
    x0, y0, x1, y1 = word["bbox"]
    width = x1 - x0
    length = len(text)
    if length == 0 or width <= 0:
        return [{"kind": "text", "text": text, "_bbox": [x0, y0, x1, y1]}]

    char_w = width / length
    parts: List[Dict[str, Any]] = []
    cursor = 0
    for match in BLANK_RUN.finditer(text):
        if match.start() > cursor:
            parts.append(
                _sub_token("text", text[cursor : match.start()], x0, char_w, cursor, y0, y1)
            )
        parts.append(
            _sub_token("blank", match.group(0), x0, char_w, match.start(), y0, y1)
        )
        cursor = match.end()
    if cursor < length:
        parts.append(_sub_token("text", text[cursor:], x0, char_w, cursor, y0, y1))
    return parts or [{"kind": "text", "text": text, "_bbox": [x0, y0, x1, y1]}]


def _sub_token(
    kind: str, text: str, x0: float, char_w: float, start: int, y0: float, y1: float
) -> Dict[str, Any]:
    sub_x0 = x0 + start * char_w
    sub_x1 = sub_x0 + len(text) * char_w
    token: Dict[str, Any] = {"kind": kind, "_bbox": [sub_x0, y0, sub_x1, y1]}
    if kind == "text":
        token["text"] = text
    else:
        token["chars"] = len(text)
    return token


def _local_rect(bbox: Sequence[float], origin: Tuple[float, float]) -> Dict[str, float]:
    return {
        "x": bbox[0] - origin[0],
        "y": bbox[1] - origin[1],
        "w": bbox[2] - bbox[0],
        "h": bbox[3] - bbox[1],
    }


def _inside_any(bbox: Any, figures: Sequence[Dict[str, Any]]) -> bool:
    if not _valid_bbox(bbox):
        return False
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    for fig in figures:
        fx0, fy0, fx1, fy1 = fig["bbox"]
        if fx0 <= cx <= fx1 and fy0 <= cy <= fy1:
            return True
    return False


def _intersects(a: Sequence[float], b: Sequence[float]) -> bool:
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def _valid_bbox(bbox: Any) -> bool:
    return (
        isinstance(bbox, (list, tuple))
        and len(bbox) == 4
        and all(isinstance(v, (int, float)) for v in bbox)
        and bbox[2] > bbox[0]
        and bbox[3] > bbox[1]
    )
