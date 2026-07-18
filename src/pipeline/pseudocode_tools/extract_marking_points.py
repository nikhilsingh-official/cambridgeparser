"""Extract MP-style marking points from mark scheme text for pseudocode questions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


MP_LINE_PATTERN = re.compile(r"^\s*MP\s*([0-9][0-9,\s\-toand]*)\s*(.*)$", re.IGNORECASE)
LIST_START_PATTERN = re.compile(r"^\s*mark\s+as\s+follows\s*:?\s*$", re.IGNORECASE)
LIST_ITEM_PATTERN = re.compile(r"^\s*(\d+)[).]?\s+(.*)$")
LIST_ITEM_NUMBER_ONLY_PATTERN = re.compile(r"^\s*(\d+)\s*$")
STOP_LINE_PATTERN = re.compile(
    r"^(max\b|total\b|marks?\b|answer\s+scheme\b|guidance\b)",
    re.IGNORECASE,
)
LEADING_TRIM_PATTERN = re.compile(r"^[\s•\-\–\—:.)]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract MP1/MP2-style marking points from pseudocode mark scheme text."
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_writing_final_qp_ms_context.json"),
        help="Final pseudocode-writing JSON containing ms_entry data.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_writing_final_qp_ms_marking_points.json"),
        help="Output JSON with marking_points added to each record.",
    )
    return parser.parse_args()


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _normalize_marker(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("(") and text.endswith(")") and len(text) > 2:
        text = text[1:-1]
    return text


def _clean_line(line: str) -> str:
    cleaned = LEADING_TRIM_PATTERN.sub("", line.strip())
    return cleaned.strip()


def _trim_lines(lines: Iterable[str]) -> list[str]:
    trimmed: list[str] = []
    for line in lines:
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        if STOP_LINE_PATTERN.match(cleaned):
            break
        trimmed.append(cleaned)
    return trimmed


def _parse_mp_numbers(raw: str) -> list[int]:
    numbers: list[int] = []
    if not raw:
        return numbers
    normalized = raw.lower().replace("and", ",").replace("to", "-")
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    for part in parts:
        if "-" in part:
            bounds = [seg.strip() for seg in part.split("-", 1)]
            if len(bounds) == 2 and bounds[0].isdigit() and bounds[1].isdigit():
                start = int(bounds[0])
                end = int(bounds[1])
                step = 1 if end >= start else -1
                numbers.extend(list(range(start, end + step, step)))
                continue
        if part.isdigit():
            numbers.append(int(part))
    return numbers


def _collect_mp_block(lines: list[str], start_index: int) -> tuple[list[str], int]:
    line = lines[start_index]
    match = MP_LINE_PATTERN.match(line)
    if not match:
        return ([], start_index + 1)
    mp_numbers = _parse_mp_numbers(match.group(1))
    desc_parts = [match.group(2).strip()] if match.group(2) else []
    idx = start_index + 1
    while idx < len(lines):
        next_line = lines[idx]
        if MP_LINE_PATTERN.match(next_line) or LIST_START_PATTERN.match(next_line):
            break
        cleaned = _clean_line(next_line)
        if STOP_LINE_PATTERN.match(cleaned):
            break
        desc_parts.append(next_line)
        idx += 1
    cleaned_lines = _trim_lines(desc_parts)
    description = " ".join(cleaned_lines).strip()
    if not mp_numbers:
        return ([description] if description else [""], idx)
    return ([description for _ in mp_numbers], idx)


def _collect_list_block(lines: list[str], start_index: int) -> tuple[list[str], int]:
    idx = start_index + 1
    items: list[str] = []
    current: Optional[str] = None
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue
        if LIST_START_PATTERN.match(line):
            break
        if STOP_LINE_PATTERN.match(line):
            break
        item_match = LIST_ITEM_PATTERN.match(line)
        if item_match:
            if current:
                items.append(current.strip())
            current = item_match.group(2).strip()
        elif LIST_ITEM_NUMBER_ONLY_PATTERN.match(line):
            if current:
                items.append(current.strip())
            current = ""
        else:
            if current is not None:
                current = f"{current} {line.strip()}"
        idx += 1
    if current:
        items.append(current.strip())
    return (items, idx)


def _extract_marking_points(text: Optional[str]) -> list[str]:
    if not text:
        return []
    lines = text.splitlines()
    points: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if MP_LINE_PATTERN.match(line):
            block_points, idx = _collect_mp_block(lines, idx)
            points.extend(block_points)
            continue
        if LIST_START_PATTERN.match(line):
            block_points, idx = _collect_list_block(lines, idx)
            points.extend(block_points)
            continue
        idx += 1
    return points


def _find_primary_node(ms_entry: Dict[str, Any], primary_marker: Any) -> Optional[Dict[str, Any]]:
    target = _normalize_marker(primary_marker)
    for part in ms_entry.get("primary_subparts", []):
        primary = part.get("primary") or {}
        if _normalize_marker(primary.get("text")) == target:
            return part
    return None


def _find_ms_node(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ms_entry = record.get("ms_entry")
    if not isinstance(ms_entry, dict):
        return None

    level = record.get("ms_level") or record.get("segment_kind")
    if level == "question":
        return ms_entry.get("question")
    if level == "primary":
        primary_part = _find_primary_node(ms_entry, record.get("primary_marker"))
        if primary_part:
            return primary_part.get("primary")
        return None
    if level == "secondary":
        primary_part = _find_primary_node(ms_entry, record.get("primary_marker"))
        if not primary_part:
            return None
        target = _normalize_marker(record.get("secondary_marker"))
        for subpart in primary_part.get("secondary_subparts", []):
            secondary = subpart.get("secondary") or {}
            if _normalize_marker(secondary.get("text")) == target:
                return secondary
        return None
    return None


def _apply_marking_points(records: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    with_points = 0
    total = 0
    for record in records:
        total += 1
        node = _find_ms_node(record)
        answer_text = node.get("answer_text") if isinstance(node, dict) else None
        marking_points = _extract_marking_points(answer_text)
        record["marking_points"] = marking_points
        if marking_points:
            with_points += 1
    return {"total": total, "with_points": with_points, "without_points": total - with_points}


def main() -> int:
    args = parse_args()
    payload = _read_json(args.input_json)
    records = payload.get("records", [])
    if isinstance(records, list):
        stats = _apply_marking_points(records)
        summary = payload.get("summary")
        if isinstance(summary, dict):
            summary["marking_points"] = {
                "records_total": stats["total"],
                "records_with_points": stats["with_points"],
                "records_without_points": stats["without_points"],
                "source_field": "ms_entry.answer_text",
            }
    _write_json(args.output_json, payload)
    print(f"Wrote marking points to {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
