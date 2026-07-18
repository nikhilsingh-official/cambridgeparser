"""Diagnostic checks for qsplitter output."""

from pathlib import Path
from typing import Any, List, Optional, Tuple

from src.pipeline.parser.qsplitter import (
    build_hierarchical_structure,
    builder as builder_utils,
    candidate_position,
    load_paper_context,
    markers as marker_utils,
)


ROMAN_VALUES = {
    "i": 1,
    "v": 5,
    "x": 10,
    "l": 50,
    "c": 100,
    "d": 500,
    "m": 1000,
}

EXCLUSION_AREA_RATIO = 0.25


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


def _find_exclusion_entry(bbox: List[float], exclusions: List[dict[str, Any]]) -> Optional[dict[str, Any]]:
    best = None
    best_intersection = 0.0
    for entry in exclusions:
        entry_bbox = entry.get("bbox")
        if not entry_bbox:
            continue
        intersection = _bbox_intersection_area(bbox, entry_bbox)
        if intersection > best_intersection:
            best_intersection = intersection
            best = entry
    return best


def _strip_parens(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("(") and cleaned.endswith(")") and len(cleaned) >= 2:
        return cleaned[1:-1].strip()
    return cleaned


def _alpha_index(text: str) -> Optional[int]:
    cleaned = _strip_parens(text).lower()
    if len(cleaned) != 1 or not cleaned.isalpha():
        return None
    return ord(cleaned) - ord("a") + 1


def _roman_to_int(text: str) -> Optional[int]:
    cleaned = _strip_parens(text).lower()
    if not cleaned or any(ch not in ROMAN_VALUES for ch in cleaned):
        return None

    total = 0
    prev = 0
    for ch in reversed(cleaned):
        value = ROMAN_VALUES[ch]
        if value < prev:
            total -= value
        else:
            total += value
            prev = value
    return total


def _is_consecutive(values: List[Tuple[int, str]], start_at: Optional[int] = None) -> bool:
    if not values:
        return True
    if start_at is not None and values[0][0] != start_at:
        return False
    for prev, curr in zip(values, values[1:]):
        if curr[0] != prev[0] + 1:
            return False
    return True


def _validate_consecutive(
    values: List[Tuple[int, str]],
    label: str,
    issues: List[str],
    *,
    start_at: Optional[int] = None,
) -> None:
    if not values:
        return
    if start_at is not None and values[0][0] != start_at:
        issues.append(f"{label} expected to start at {start_at}: got {values[0][1]}")
        return
    if len(values) < 2:
        return
    for prev, curr in zip(values, values[1:]):
        if curr[0] != prev[0] + 1:
            issues.append(f"{label} not consecutive: {prev[1]} then {curr[1]}")
            return


def validate_question_order(questions: List[dict[str, Any]], issues: List[str]) -> None:
    last_value = None
    for question in questions:
        text = question["question"]["text"]
        if not isinstance(text, str) or not text.isdigit():
            continue
        value = int(text)
        if last_value is not None and value <= last_value:
            issues.append(f"Question order mismatch: got {value} after {last_value}")
        last_value = value


def validate_reading_order(markers: List[dict[str, Any]], label: str, issues: List[str]) -> None:
    positions = [candidate_position(marker) for marker in markers]
    if positions != sorted(positions):
        issues.append(f"{label} are not in reading order")


def primary_markers(question: dict[str, Any]) -> List[dict[str, Any]]:
    return [entry["primary"] for entry in question.get("primary_subparts", [])]


def secondary_markers(primary: dict[str, Any]) -> List[dict[str, Any]]:
    return [entry["secondary"] for entry in primary.get("secondary_subparts", [])]


def validate_hierarchy(hierarchy: dict[str, Any]) -> List[str]:
    issues: List[str] = []
    questions = hierarchy.get("questions", [])
    if not questions:
        issues.append("Hierarchy is empty: no questions detected")
        return issues
    validate_question_order(questions, issues)

    for question in questions:
        question_text = question["question"]["text"]
        validate_reading_order(
            primary_markers(question),
            f"Question {question_text} primary subparts",
            issues,
        )
        primary_label = f"Question {question_text} primary subparts"
        primary_texts = [entry["primary"]["text"] for entry in question.get("primary_subparts", [])]
        alpha_values: List[Tuple[int, str]] = []
        roman_values: List[Tuple[int, str]] = []
        alpha_possible = True
        roman_possible = True
        for text in primary_texts:
            alpha = _alpha_index(text)
            roman = _roman_to_int(text)
            if alpha is None:
                alpha_possible = False
            else:
                alpha_values.append((alpha, text))
            if roman is None:
                roman_possible = False
            else:
                roman_values.append((roman, text))

        alpha_valid = alpha_possible and _is_consecutive(alpha_values, start_at=1)
        roman_valid = roman_possible and _is_consecutive(roman_values, start_at=1)
        if not alpha_valid and not roman_valid:
            if alpha_possible and not roman_possible:
                _validate_consecutive(alpha_values, primary_label, issues, start_at=1)
            elif roman_possible and not alpha_possible:
                _validate_consecutive(roman_values, primary_label, issues, start_at=1)
            elif alpha_possible and roman_possible:
                issues.append(f"{primary_label} not consecutive for alpha or roman markers")
            elif primary_texts:
                issues.append(f"{primary_label} contains non alpha/roman markers")
        for primary in question.get("primary_subparts", []):
            validate_reading_order(
                secondary_markers(primary),
                f"Question {question_text} primary {primary['primary']['text']} secondary subparts",
                issues,
            )
            secondary_values = []
            non_roman_secondaries = []
            for entry in primary.get("secondary_subparts", []):
                text = entry["secondary"]["text"]
                value = _roman_to_int(text)
                if value is not None:
                    secondary_values.append((value, text))
                else:
                    non_roman_secondaries.append(text)
            if non_roman_secondaries:
                issues.append(
                    f"Question {question_text} primary {primary['primary']['text']} secondary subparts must be roman: "
                    + ", ".join(non_roman_secondaries)
                )
            _validate_consecutive(
                secondary_values,
                f"Question {question_text} primary {primary['primary']['text']} secondary subparts",
                issues,
                start_at=1,
            )

    return issues


def validate_exclusion_anomalies(context: dict[str, Any], issues: List[str]) -> None:
    seen = set()
    for page_index, page in enumerate(context.get("data", [])):
        exclusions = context.get("excluded_bboxes_by_page", [])[page_index]
        if not exclusions:
            continue
        page_bbox = page.get("image_bbox") or [0.0, 0.0, 0.0, 0.0]
        page_area = _bbox_area(page_bbox)
        for line_index, line in enumerate(page.get("text_lines", [])):
            text = line.get("text") or ""
            if not text:
                continue
            for marker in marker_utils.extract_parenthetical_markers(text, line.get("chars", [])):
                if marker_utils.classify_subpart_marker(marker["text"]) is None:
                    continue
                if not marker_utils.is_in_excluded_region(marker["bbox"], exclusions):
                    continue
                entry = _find_exclusion_entry(marker["bbox"], exclusions)
                if not entry:
                    continue
                entry_bbox = entry.get("bbox")
                block_type = entry.get("block_type", "Unknown")
                entry_area = _bbox_area(entry_bbox) if entry_bbox else 0.0
                if page_area and entry_area / page_area < EXCLUSION_AREA_RATIO:
                    continue
                key = (page_index, line_index, marker["text"], block_type)
                if key in seen:
                    continue
                seen.add(key)
                issues.append(
                    f"Possible oversized exclusion on page {page_index + 1}: {block_type} excludes {marker['text']}"
                )

            candidate = builder_utils._extract_question_candidate_from_digit_run(
                line, page_index, line_index, []
            )
            if candidate and marker_utils.is_in_excluded_region(candidate["bbox"], exclusions):
                entry = _find_exclusion_entry(candidate["bbox"], exclusions)
                if not entry:
                    continue
                entry_bbox = entry.get("bbox")
                block_type = entry.get("block_type", "Unknown")
                entry_area = _bbox_area(entry_bbox) if entry_bbox else 0.0
                if page_area and entry_area / page_area < EXCLUSION_AREA_RATIO:
                    continue
                key = (page_index, line_index, candidate["text"], block_type)
                if key in seen:
                    continue
                seen.add(key)
                issues.append(
                    f"Possible oversized exclusion on page {page_index + 1}: {block_type} excludes question {candidate['text']}"
                )


def run_diagnostics_for_paper(
    paper_code: str,
    pdf_dir: Path,
    ocr_dir: Path,
    marker_dir: Path,
) -> List[str]:
    context = load_paper_context(paper_code, pdf_dir, ocr_dir, marker_dir)
    hierarchy = build_hierarchical_structure(paper_code, pdf_dir, ocr_dir, marker_dir, context=context)
    issues = validate_hierarchy(hierarchy)
    validate_exclusion_anomalies(context, issues)
    return issues
