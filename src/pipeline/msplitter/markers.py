import re
import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional
from .geometry import combine_bboxes, bbox_intersects
from .type_definitions import Char, ExcludedRegion

PAREN_MARK_REGEX = re.compile(r"\(([^)]+)\)")
BRACKET_MARK_REGEX = re.compile(r"\[(\d+)\]")
SUBPART_INDICATOR_REGEX = re.compile(r"^[A-Za-z0-9]+$|^[ivxlcdmIVXLCDM]+$")
ALPHA_REGEX = re.compile(r"^\([a-z]\)$")
ROMAN_REGEX = re.compile(r"^\([ivxlcdm]+\)$")
QUESTION_MARKER_TRAILING_CHARS = {".", ")", ":", "-", "/"}
PICTURE_EXCLUSION_OVERLAP = 0.2
HEADER_EXCLUSION_OVERLAP = 0.2
FOOTER_EXCLUSION_OVERLAP = 0.2


def can_cast_to_int(x: str) -> bool:
    try:
        int(x)
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def _latex_converter():
    try:
        from pylatexenc.latex2text import LatexNodes2Text
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Marker math parsing requires pylatexenc; install it to process OCR lines with <math> tags."
        ) from exc

    return LatexNodes2Text()


def convert_latex_to_text(latex_source: str) -> str:
    return _latex_converter().latex_to_text(latex_source).strip()


def replace_math_tags(text: str) -> str:
    if "<math>" not in text:
        return text

    parts: List[str] = []
    cursor = 0
    while True:
        start = text.find("<math>", cursor)
        if start == -1:
            parts.append(text[cursor:])
            break

        parts.append(text[cursor:start])
        end = text.find("</math>", start)
        if end == -1:
            parts.append(text[start:])
            break

        parts.append(convert_latex_to_text(text[start + len("<math>"):end]))
        cursor = end + len("</math>")

    return "".join(parts)


def find_prev_nonempty(chars: List[Char], start_index: int) -> Optional[int]:
    for idx in range(start_index, -1, -1):
        text = (chars[idx].get("text") or "").strip()
        if text:
            return idx
    return None


def find_next_nonempty(chars: List[Char], start_index: int) -> Optional[int]:
    for idx in range(start_index, len(chars)):
        text = (chars[idx].get("text") or "").strip()
        if text:
            return idx
    return None


def is_bracketed_digit_run(chars: List[Char], start_index: int, end_index: int) -> bool:
    prev = find_prev_nonempty(chars, start_index - 1)
    nxt = find_next_nonempty(chars, end_index + 1)
    if prev is None or nxt is None:
        return False

    return chars[prev].get("text") == "[" and chars[nxt].get("text") == "]"


def extract_question_number_from_math_text(text_line: str) -> Optional[str]:
    if "<math>" not in text_line:
        return None

    converted = replace_math_tags(text_line)
    normalized = "".join(
        ch
        for ch in converted
        if not ch.isspace() and not unicodedata.combining(ch)
    )
    if normalized.isdigit():
        return normalized

    return None


def classify_subpart_marker(marker_text: str) -> Optional[str]:
    normalized = marker_text.strip().lower()
    is_alpha = ALPHA_REGEX.fullmatch(normalized)
    is_roman = ROMAN_REGEX.fullmatch(normalized)
    if is_alpha and is_roman:
        return "ambiguous"
    if is_alpha:
        return "alpha"
    if is_roman:
        return "roman"
    return None


def extract_leading_question_number(chars: List[Char]) -> Optional[Dict[str, Any]]:
    nonempty_positions = [
        index for index, char in enumerate(chars) if (char.get("text") or "").strip()
    ]

    for ordinal, start_index in enumerate(nonempty_positions, start=1):
        if ordinal > 2:
            break

        start_text = chars[start_index].get("text") or ""
        if not can_cast_to_int(start_text):
            continue

        run_positions = [start_index]
        next_ordinal = ordinal
        while next_ordinal < len(nonempty_positions):
            next_index = nonempty_positions[next_ordinal]
            next_text = chars[next_index].get("text") or ""
            if not can_cast_to_int(next_text):
                break
            run_positions.append(next_index)
            next_ordinal += 1

        end_index = run_positions[-1]
        if is_bracketed_digit_run(chars, start_index, end_index):
            continue

        next_nonempty = find_next_nonempty(chars, end_index + 1)
        if next_nonempty is not None:
            next_text = (chars[next_nonempty].get("text") or "").strip()
            if next_text == "(":
                pass
            elif next_text not in QUESTION_MARKER_TRAILING_CHARS:
                whitespace_between = any(
                    (chars[idx].get("text") or "").isspace()
                    for idx in range(end_index + 1, next_nonempty)
                )
                if not whitespace_between:
                    continue
            elif _has_following_alnum_before_whitespace(chars, next_nonempty + 1):
                continue

        marker_chars = [chars[index] for index in run_positions]
        marker_text = "".join((char.get("text") or "") for char in marker_chars)
        if len(marker_text) > 2:
            continue
        return {
            "text": marker_text,
            "bbox": combine_bboxes([char["bbox"] for char in marker_chars]),
            "start_index": start_index,
            "end_index": end_index,
        }

    return None


def _has_following_alnum_before_whitespace(chars: List[Char], start_index: int) -> bool:
    for index in range(start_index, len(chars)):
        char_text = chars[index].get("text") or ""
        if char_text.isspace():
            return False
        if char_text.isalnum():
            return True
    return False


def _looks_like_question_prefix(prefix: str) -> bool:
    stripped = prefix.strip()
    if not stripped:
        return False
    if stripped.isdigit():
        return True
    if stripped[:-1].isdigit() and stripped[-1] in {".", ")"}:
        return True
    return False


def extract_parenthetical_markers(text_line: str, chars: List[Char]) -> List[Dict[str, Any]]:
    leading_ws = len(text_line) - len(text_line.lstrip())
    max_leading_gap = 6
    markers = []
    last_accepted_end = None

    for match in PAREN_MARK_REGEX.finditer(text_line):
        if match.start() > leading_ws + max_leading_gap:
            if last_accepted_end is None or match.start() > last_accepted_end + 3:
                prefix = text_line[leading_ws:match.start()]
                if not _looks_like_question_prefix(prefix):
                    continue

        inner_text = match.group(1).strip()
        if not inner_text or not SUBPART_INDICATOR_REGEX.match(inner_text):
            continue

        marker_chars = chars[match.start():match.end()]
        candidate_bboxes = [char["bbox"] for char in marker_chars]
        if not candidate_bboxes:
            continue

        markers.append({
            "text": f"({inner_text})",
            "bbox": combine_bboxes(candidate_bboxes),
            "start_index": match.start(),
            "end_index": match.end(),
            "line_text": text_line,
        })
        last_accepted_end = match.end()

    return markers


def extract_bracketed_marks(text_line: str, chars: List[Char]) -> List[Dict[str, Any]]:
    markers = []
    for match in BRACKET_MARK_REGEX.finditer(text_line):
        marker_chars = chars[match.start():match.end()]
        candidate_bboxes = [char["bbox"] for char in marker_chars]
        if not candidate_bboxes:
            continue

        markers.append({
            "text": f"[{match.group(1)}]",
            "bbox": combine_bboxes(candidate_bboxes),
            "start_index": match.start(),
            "end_index": match.end(),
            "line_text": text_line,
        })

    return markers


def looks_like_marks_pattern(line_text: str) -> bool:
    # Simple heuristic: contains digits or the word 'marks'
    if not line_text:
        return False
    if "marks" in line_text.lower():
        return True
    return any(ch.isdigit() for ch in line_text)


def _bbox_area(bbox: List[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _bbox_intersection_area(left: List[float], right: List[float]) -> float:
    x_left = max(left[0], right[0])
    y_top = max(left[1], right[1])
    x_right = min(left[2], right[2])
    y_bottom = min(left[3], right[3])
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    return (x_right - x_left) * (y_bottom - y_top)


def collect_marker_exclusion_bboxes(marker_document: Dict[str, Any], excluded_types: set) -> List[List[ExcludedRegion]]:
    exclusion_bboxes_by_page = []
    marker_pages = marker_document.get("children", [])

    for page_index, marker_page in enumerate(marker_pages):
        page_exclusions: List[ExcludedRegion] = []
        marker_blocks = marker_page.get("children") or []

        # Exclude first page
        if page_index == 0:
            page_bbox = marker_page.get("bbox")
            if page_bbox:
                page_exclusions.append({"bbox": page_bbox, "block_type": "FirstPage"})

        for block in marker_blocks:
            if block.get("block_type") in excluded_types:
                block_bbox = block.get("bbox")
                if block_bbox:
                    page_exclusions.append(
                        {"bbox": block_bbox, "block_type": block.get("block_type") or "Unknown"}
                    )

        exclusion_bboxes_by_page.append(page_exclusions)

    return exclusion_bboxes_by_page


def is_in_excluded_region(char_bbox: List[float], excluded_bboxes: List[ExcludedRegion]) -> bool:
    for entry in excluded_bboxes:
        if isinstance(entry, dict):
            excluded_bbox = entry.get("bbox")
            block_type = entry.get("block_type")
        else:
            excluded_bbox = entry
            block_type = None
        if not excluded_bbox:
            continue
        if not bbox_intersects(char_bbox, excluded_bbox):
            continue
        if block_type in {"Picture", "PageHeader", "PageFooter"}:
            intersection = _bbox_intersection_area(char_bbox, excluded_bbox)
            if intersection <= 0:
                continue
            marker_area = _bbox_area(char_bbox)
            if marker_area <= 0:
                continue
            overlap_threshold = {
                "Picture": PICTURE_EXCLUSION_OVERLAP,
                "PageHeader": HEADER_EXCLUSION_OVERLAP,
                "PageFooter": FOOTER_EXCLUSION_OVERLAP,
            }.get(block_type, PICTURE_EXCLUSION_OVERLAP)
            if (intersection / marker_area) < overlap_threshold:
                continue
        return True
    return False
