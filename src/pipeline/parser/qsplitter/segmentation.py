from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .markers import is_in_excluded_region, looks_like_marks_pattern

Y_TOLERANCE = 5.0


def _marker_key(marker: Dict[str, Any]) -> tuple[int, tuple[Any, ...]]:
    page_index = int(marker["page_index"])
    bbox = marker.get("bbox", [0, 0, 0, 0])
    y0 = round(float(bbox[1]), 3) if len(bbox) >= 2 else 0.0
    x0 = round(float(bbox[0]), 3) if len(bbox) >= 1 else 0.0
    line_id = marker.get("line_id")
    if isinstance(line_id, (list, tuple)) and len(line_id) == 2:
        return page_index, ("line", int(line_id[0]), int(line_id[1]), y0, x0)

    return page_index, ("bbox", y0, x0)


def _candidate_position(marker: Dict[str, Any]) -> tuple[int, float, float]:
    bbox = marker.get("bbox", [0, 0, 0, 0])
    return int(marker["page_index"]), float(bbox[1]), float(bbox[0])


def _marker_sort_key(marker: Dict[str, Any]) -> tuple[int, int, float, float]:
    page_idx, y0, x0 = _candidate_position(marker)
    line_id = marker.get("line_id")
    if isinstance(line_id, (list, tuple)) and len(line_id) == 2:
        return page_idx, int(line_id[1]), y0, x0
    return page_idx, 10**9, y0, x0


def _collect_segment_markers(hierarchy_payload: Dict[str, Any]) -> list[Dict[str, Any]]:
    markers: list[Dict[str, Any]] = []
    for question in hierarchy_payload.get("questions", []):
        q = question["question"]
        markers.append({"level": 0, "marker": {"kind": "question", **q}})
        for primary in question.get("primary_subparts", []):
            p = primary["primary"]
            markers.append({"level": 1, "marker": {"kind": "primary", **p}})
            for secondary in primary.get("secondary_subparts", []):
                s = secondary["secondary"]
                markers.append({"level": 2, "marker": {"kind": "secondary", **s}})
    return markers


def _build_end_marker_map(hierarchy_payload: Dict[str, Any]) -> dict[tuple[int, tuple[Any, ...]], Optional[Dict[str, Any]]]:
    """Map each marker to the next marker at the same or higher hierarchy level.

    This gives question, primary, and secondary segments independent end
    boundaries: a primary ends at the next primary/question, not at its first
    secondary.
    """
    marker_entries = sorted(
        _collect_segment_markers(hierarchy_payload),
        key=lambda entry: _marker_sort_key(entry["marker"]),
    )
    end_by_marker: dict[tuple[int, tuple[Any, ...]], Optional[Dict[str, Any]]] = {}

    for idx, entry in enumerate(marker_entries):
        current_marker = entry["marker"]
        current_level = int(entry["level"])
        next_end: Optional[Dict[str, Any]] = None

        for candidate in marker_entries[idx + 1 :]:
            if int(candidate["level"]) <= current_level:
                next_end = candidate["marker"]
                break

        end_by_marker[_marker_key(current_marker)] = next_end

    return end_by_marker


def _combine_bboxes(bboxes: list[list[float]]) -> list[float]:
    return [
        min(float(bbox[0]) for bbox in bboxes),
        min(float(bbox[1]) for bbox in bboxes),
        max(float(bbox[2]) for bbox in bboxes),
        max(float(bbox[3]) for bbox in bboxes),
    ]


def _page_bounds(data: list[Dict[str, Any]], page_index: int) -> list[float]:
    if 0 <= page_index < len(data):
        image_bbox = data[page_index].get("image_bbox")
        if isinstance(image_bbox, list) and len(image_bbox) == 4:
            return [float(v) for v in image_bbox]

    return [0.0, 0.0, 0.0, 0.0]


def _resolve_line_index(
    data: list[Dict[str, Any]],
    marker: Dict[str, Any],
    page_index: int,
) -> int:
    if not (0 <= page_index < len(data)):
        return 0

    page_lines = data[page_index].get("text_lines", [])
    if not page_lines:
        return 0

    line_id = marker.get("line_id")
    if isinstance(line_id, (list, tuple)) and len(line_id) == 2:
        idx = int(line_id[1])
        if 0 <= idx < len(page_lines):
            return idx

    bbox = marker.get("bbox", [0, 0, 0, 0])
    marker_y = float(bbox[1]) if len(bbox) >= 2 else 0.0
    for idx, line in enumerate(page_lines):
        line_bbox = line.get("bbox")
        if not line_bbox or len(line_bbox) != 4:
            continue
        if float(line_bbox[1]) + Y_TOLERANCE >= marker_y:
            return idx

    return len(page_lines) - 1


def _iter_lines_between(
    data: list[Dict[str, Any]],
    start_page: int,
    start_line: int,
    end_page: int,
    end_line: int,
) -> list[tuple[int, int, Dict[str, Any]]]:
    lines: list[tuple[int, int, Dict[str, Any]]] = []
    for page_idx in range(start_page, end_page + 1):
        if not (0 <= page_idx < len(data)):
            continue

        page_lines = data[page_idx].get("text_lines", [])
        if not page_lines:
            continue

        if page_idx == start_page and page_idx == end_page:
            lo = max(0, start_line)
            hi = min(len(page_lines) - 1, end_line)
        elif page_idx == start_page:
            lo = max(0, start_line)
            hi = len(page_lines) - 1
        elif page_idx == end_page:
            lo = 0
            hi = min(len(page_lines) - 1, end_line)
        else:
            lo = 0
            hi = len(page_lines) - 1

        for line_idx in range(lo, hi + 1):
            lines.append((page_idx, line_idx, page_lines[line_idx]))

    return lines


def _slice_line_text_and_words(
    line: Dict[str, Any],
    page_idx: int,
    line_idx: int,
    start_x: Optional[float],
    end_x: Optional[float],
    start_y: Optional[float] = None,
    end_y: Optional[float] = None,
    page_bounds: Optional[list[float]] = None,
    page_exclusions: Optional[list[Dict[str, Any]]] = None,
) -> tuple[str, list[Dict[str, Any]], Optional[list[float]]]:
    chars = line.get("chars", [])
    if not chars:
        return (line.get("text") or "").strip(), [], None

    filtered_chars: list[tuple[str, list[float]]] = []
    kept_char_bboxes: list[list[float]] = []
    page_top = float(page_bounds[1]) if page_bounds and len(page_bounds) == 4 else 0.0
    page_bottom = float(page_bounds[3]) if page_bounds and len(page_bounds) == 4 else 0.0
    page_height = max(0.0, page_bottom - page_top)
    # Hide common header/footer artifacts (page IDs, running footer text) in segmented content.
    top_noise_limit = (
        page_top + max(20.0, page_height * 0.06)
        if page_bounds and page_height > 0.0
        else None
    )
    bottom_noise_limit = (
        page_bottom - max(20.0, page_height * 0.03)
        if page_bounds and page_height > 0.0
        else None
    )
    for char in chars:
        text = char.get("text") or ""
        if not text:
            continue

        bbox = char.get("bbox")
        if bbox and len(bbox) == 4:
            if start_y is not None and float(bbox[3]) < (start_y - Y_TOLERANCE):
                continue
            if end_y is not None and float(bbox[1]) >= (end_y - Y_TOLERANCE):
                continue
            if (
                page_exclusions is not None
                and is_in_excluded_region(bbox, page_exclusions)
                and not looks_like_marks_pattern(line.get("text", ""))
            ):
                continue
            if top_noise_limit is not None and float(bbox[3]) <= top_noise_limit:
                continue
            if bottom_noise_limit is not None and float(bbox[1]) >= bottom_noise_limit:
                continue
            cx = (float(bbox[0]) + float(bbox[2])) / 2.0
            if start_x is not None and cx < start_x:
                continue
            if end_x is not None and cx > end_x:
                continue
            bbox_f = [float(v) for v in bbox]
            filtered_chars.append((text, bbox_f))
            kept_char_bboxes.append(bbox_f)
            continue

        filtered_chars.append((text, [0.0, 0.0, 0.0, 0.0]))

    if not filtered_chars:
        return "", [], None

    line_text = "".join(char_text for char_text, _ in filtered_chars).strip()

    words: list[Dict[str, Any]] = []
    current_word_chars: list[str] = []
    current_word_bboxes: list[list[float]] = []

    def flush_word() -> None:
        if not current_word_chars:
            return
        word_text = "".join(current_word_chars)
        words.append(
            {
                "page_index": page_idx,
                "line_id": [page_idx, line_idx],
                "text": word_text,
                "bbox": _combine_bboxes(current_word_bboxes),
            }
        )
        current_word_chars.clear()
        current_word_bboxes.clear()

    for char_text, char_bbox in filtered_chars:
        if char_text.isspace():
            flush_word()
            continue

        current_word_chars.append(char_text)
        current_word_bboxes.append(char_bbox)

    flush_word()
    line_content_bbox = _combine_bboxes(kept_char_bboxes) if kept_char_bboxes else None
    return line_text, words, line_content_bbox


def _content_from_bounds(
    data: list[Dict[str, Any]],
    start_marker: Dict[str, Any],
    end_marker: Optional[Dict[str, Any]],
    excluded_bboxes_by_page: Optional[list[list[Dict[str, Any]]]] = None,
) -> tuple[str, list[Dict[str, Any]], list[str], list[Dict[str, Any]]]:
    """Extract visible line text between two markers across page boundaries."""
    if not data:
        return "", [], ["empty"], []

    start_page = int(start_marker["page_index"])
    start_line = _resolve_line_index(data, start_marker, start_page)
    start_y = float(start_marker["bbox"][1]) if start_marker.get("bbox") else None

    if end_marker is None:
        end_page = len(data) - 1
        end_lines = data[end_page].get("text_lines", []) if end_page >= 0 else []
        end_line = max(0, len(end_lines) - 1)
        end_y = None
    else:
        end_page = int(end_marker["page_index"])
        end_line = _resolve_line_index(data, end_marker, end_page)
        end_y = float(end_marker["bbox"][1]) if end_marker.get("bbox") else None

    if (end_page, end_line) < (start_page, start_line):
        return "", [], ["empty"], []

    lines = _iter_lines_between(data, start_page, start_line, end_page, end_line)
    if not lines:
        return "", [], ["empty"], []

    text_parts: list[str] = []
    per_page_text: dict[int, list[str]] = {}
    per_page_bbox: dict[int, list[float]] = {}
    per_page_words: dict[int, list[Dict[str, Any]]] = {}
    flat_words: list[Dict[str, Any]] = []

    for page_idx, line_idx, line in lines:
        sx: Optional[float] = None
        ex: Optional[float] = None

        if page_idx == start_page and line_idx == start_line:
            sx = float(start_marker["bbox"][2])
        if end_marker is not None and page_idx == end_page and line_idx == end_line:
            ex = float(end_marker["bbox"][0])

        page_exclusions = (
            excluded_bboxes_by_page[page_idx]
            if excluded_bboxes_by_page is not None and 0 <= page_idx < len(excluded_bboxes_by_page)
            else None
        )
        sliced_text, words, line_content_bbox = _slice_line_text_and_words(
            line,
            page_idx,
            line_idx,
            sx,
            ex,
            start_y=start_y if page_idx == start_page else None,
            end_y=end_y if page_idx == end_page else None,
            page_bounds=_page_bounds(data, page_idx),
            page_exclusions=page_exclusions,
        )

        if sliced_text:
            text_parts.append(sliced_text)
            per_page_text.setdefault(page_idx, []).append(sliced_text)

            if line_content_bbox and len(line_content_bbox) == 4:
                if page_idx not in per_page_bbox:
                    per_page_bbox[page_idx] = [
                        float(line_content_bbox[0]),
                        float(line_content_bbox[1]),
                        float(line_content_bbox[2]),
                        float(line_content_bbox[3]),
                    ]
                else:
                    per_page_bbox[page_idx][0] = min(per_page_bbox[page_idx][0], float(line_content_bbox[0]))
                    per_page_bbox[page_idx][1] = min(per_page_bbox[page_idx][1], float(line_content_bbox[1]))
                    per_page_bbox[page_idx][2] = max(per_page_bbox[page_idx][2], float(line_content_bbox[2]))
                    per_page_bbox[page_idx][3] = max(per_page_bbox[page_idx][3], float(line_content_bbox[3]))

        if words:
            per_page_words.setdefault(page_idx, []).extend(words)
            flat_words.extend(words)

    all_pages = sorted(set(per_page_text.keys()) | set(per_page_words.keys()))
    content_pages: list[Dict[str, Any]] = []
    for page_idx in all_pages:
        page_bounds = _page_bounds(data, page_idx)
        page_bbox_raw = per_page_bbox.get(page_idx, page_bounds)
        page_bbox = [
            float(page_bounds[0]),
            float(page_bbox_raw[1]),
            float(page_bounds[2]),
            float(page_bbox_raw[3]),
        ]
        content_pages.append(
            {
                "page_index": page_idx,
                "bbox": page_bbox,
                "text": "\n".join(per_page_text.get(page_idx, [])).strip(),
                "source": "fitz",
                "words": per_page_words.get(page_idx, []),
            }
        )

    if not text_parts and not flat_words:
        return "", content_pages, ["empty"], []

    content_source = "fitz" if text_parts else "empty"
    return "\n".join(text_parts).strip(), content_pages, [content_source], flat_words


def _segment_page_bbox(
    data: list[Dict[str, Any]],
    page_idx: int,
    start_marker: Dict[str, Any],
    end_marker: Optional[Dict[str, Any]],
) -> list[float]:
    page_bounds = _page_bounds(data, page_idx)
    page_top = float(page_bounds[1])
    page_bottom = float(page_bounds[3])
    start_page = int(start_marker["page_index"])

    if page_idx == start_page:
        y0 = float(start_marker["bbox"][1])
    else:
        y0 = page_top

    if end_marker is not None and page_idx == int(end_marker["page_index"]):
        y1 = float(end_marker["bbox"][1])
    else:
        y1 = page_bottom

    if y1 < y0:
        y1 = y0

    return [float(page_bounds[0]), y0, float(page_bounds[2]), y1]


def _build_segment(
    marker: Dict[str, Any],
    data: list[Dict[str, Any]],
    end_marker: Optional[Dict[str, Any]],
    excluded_bboxes_by_page: Optional[list[list[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    content_text, content_pages, content_sources, content_word_boxes = _content_from_bounds(
        data,
        marker,
        end_marker,
        excluded_bboxes_by_page=excluded_bboxes_by_page,
    )

    start_page = int(marker["page_index"])
    content_bbox = _segment_page_bbox(data, start_page, marker, end_marker)
    for page in content_pages:
        page["bbox"] = _segment_page_bbox(data, int(page["page_index"]), marker, end_marker)

    return {
        **marker,
        "content_bbox": content_bbox,
        "content_text": content_text,
        "content_source": content_sources[0] if content_sources else "empty",
        "content_pages": content_pages,
        "content_word_boxes": content_word_boxes,
    }


def build_segmented_questions(
    paper_code: str,
    hierarchy_payload: Dict[str, Any],
    pdf_dir: Path,
    ocr_dir: Path,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    del pdf_dir, ocr_dir  # segmentation now uses context text lines directly
    if context is None:
        raise ValueError("build_segmented_questions requires context for line-order extraction")

    data = context["data"]
    excluded_bboxes_by_page = context.get("excluded_bboxes_by_page")
    end_by_marker = _build_end_marker_map(hierarchy_payload)
    questions = hierarchy_payload.get("questions", [])

    questions_out: list[Dict[str, Any]] = []
    for question in questions:
        q_marker = question["question"]
        q_end = end_by_marker.get(_marker_key(q_marker))
        question_out = _build_segment(
            q_marker,
            data,
            q_end,
            excluded_bboxes_by_page=excluded_bboxes_by_page,
        )

        primaries_out: list[Dict[str, Any]] = []
        for primary in question.get("primary_subparts", []):
            p_marker = primary["primary"]
            p_end = end_by_marker.get(_marker_key(p_marker))
            primary_out = _build_segment(
                p_marker,
                data,
                p_end,
                excluded_bboxes_by_page=excluded_bboxes_by_page,
            )

            secondaries_out: list[Dict[str, Any]] = []
            for secondary in primary.get("secondary_subparts", []):
                s_marker = secondary["secondary"]
                s_end = end_by_marker.get(_marker_key(s_marker))
                secondary_out = _build_segment(
                    s_marker,
                    data,
                    s_end,
                    excluded_bboxes_by_page=excluded_bboxes_by_page,
                )
                secondaries_out.append({"secondary": secondary_out})

            primaries_out.append(
                {
                    "primary": primary_out,
                    "secondary_subparts": secondaries_out,
                }
            )

        questions_out.append(
            {
                "question": question_out,
                "primary_subparts": primaries_out,
            }
        )

    return {"paper_code": paper_code, "questions": questions_out}
