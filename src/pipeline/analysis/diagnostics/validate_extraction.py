"""Deterministic validation of generated extraction artifacts.

Inspects qp_output segmented questions, ms_output mark schemes, and the final
joined pseudocode records, then reports counts and suspect items without
calling any model or network service.

Usage:

    python -m src.pipeline.analysis.diagnostics.validate_extraction \
        --qp-dir qp_output \
        --ms-dir ms_output \
        --final-json pseudocode_writing_hits/pseudocode_writing_final_qp_ms_marking_points.json \
        --output-json pseudocode_writing_hits/extraction_validation.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ANSWER_DOTS_PATTERN = re.compile(r"\.{6,}")
MARKS_SUFFIX_PATTERN = re.compile(r"\[\s*\d+\s*\]")
GARBAGE_PATTERNS = [
    ("replacement_char", re.compile("�")),
    ("cid_artifact", re.compile(r"\(cid:\d+\)")),
    ("control_chars", re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")),
    ("html_tag_leak", re.compile(r"</?(?:p|div|span|table|br)\b", re.IGNORECASE)),
    ("repeated_char_run", re.compile(r"([^\s.…_-])\1{14,}")),
]
SHORT_SEGMENT_CHARS = 25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate generated qp_output, ms_output, and final pseudocode records."
    )
    parser.add_argument("--qp-dir", type=Path, default=Path("qp_output"))
    parser.add_argument("--ms-dir", type=Path, default=Path("ms_output"))
    parser.add_argument(
        "--final-json",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_question_records.json"),
        help=(
            "Final joined records: canonical pseudocode-question-record/v1 output "
            "from build_final_records, or the legacy final_qp_ms JSON."
        ),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("pseudocode_writing_hits/extraction_validation.json"),
        help="Where the machine-readable validation report is written.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=40,
        help="Maximum offending items listed per finding category.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> Any:
    with path.open() as handle:
        return json.load(handle)


def _strip_answer_lines(text: str) -> str:
    """Remove dotted answer lines and trailing [n] marks noise before length checks."""
    cleaned = ANSWER_DOTS_PATTERN.sub(" ", text)
    cleaned = MARKS_SUFFIX_PATTERN.sub(" ", cleaned)
    return " ".join(cleaned.split())


def _garbage_hits(text: str) -> List[str]:
    return [name for name, pattern in GARBAGE_PATTERNS if pattern.search(text)]


def _valid_bbox(bbox: Any) -> bool:
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False
    try:
        x0, y0, x1, y1 = (float(v) for v in bbox)
    except (TypeError, ValueError):
        return False
    return x1 > x0 and y1 > y0


def iter_qp_segments(payload: Dict[str, Any]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Yield (segment_key, node) for question, primary, and secondary nodes."""
    for question in payload.get("questions", []):
        q_node = question.get("question") or {}
        q_marker = str(q_node.get("text") or "?").strip()
        yield (f"q{q_marker}", q_node)
        for primary in question.get("primary_subparts", []):
            p_node = primary.get("primary") or {}
            p_marker = str(p_node.get("text") or "?").strip()
            yield (f"q{q_marker}|{p_marker}", p_node)
            for secondary in primary.get("secondary_subparts", []):
                s_node = secondary.get("secondary") or {}
                s_marker = str(s_node.get("text") or "?").strip()
                yield (f"q{q_marker}|{p_marker}|{s_marker}", s_node)


def validate_qp_dir(qp_dir: Path, max_items: int) -> Dict[str, Any]:
    files = sorted(qp_dir.glob("*/segmented_questions.json"))
    empty_hierarchies: List[str] = []
    empty_segments: List[str] = []
    short_segments: List[Dict[str, Any]] = []
    garbage_segments: List[Dict[str, Any]] = []
    invalid_bboxes: List[str] = []
    invalid_page_refs: List[str] = []
    total_segments = 0

    for path in files:
        paper_code = path.parent.name
        payload = _load_json(path)
        segments = list(iter_qp_segments(payload))
        if not payload.get("questions"):
            empty_hierarchies.append(paper_code)
            continue
        for key, node in segments:
            total_segments += 1
            ref = f"{paper_code}:{key}"
            content = (node.get("content_text") or "").strip()
            if not content:
                empty_segments.append(ref)
            else:
                stripped = _strip_answer_lines(content)
                if len(stripped) < SHORT_SEGMENT_CHARS:
                    short_segments.append({"segment": ref, "text": stripped})
                hits = _garbage_hits(content)
                if hits:
                    garbage_segments.append({"segment": ref, "patterns": hits})
            if not _valid_bbox(node.get("content_bbox")):
                invalid_bboxes.append(ref)
            pages = node.get("content_pages")
            page_ok = isinstance(pages, list) and all(
                isinstance(page, dict) and isinstance(page.get("page_index"), int)
                for page in pages
            )
            if not page_ok:
                invalid_page_refs.append(ref)

    return {
        "segmented_files": len(files),
        "total_segments": total_segments,
        "empty_hierarchies": {"count": len(empty_hierarchies), "items": empty_hierarchies[:max_items]},
        "empty_segment_text": {"count": len(empty_segments), "items": empty_segments[:max_items]},
        "short_segment_text": {"count": len(short_segments), "items": short_segments[:max_items]},
        "garbage_segments": {"count": len(garbage_segments), "items": garbage_segments[:max_items]},
        "invalid_content_bboxes": {"count": len(invalid_bboxes), "items": invalid_bboxes[:max_items]},
        "invalid_page_refs": {"count": len(invalid_page_refs), "items": invalid_page_refs[:max_items]},
    }


def iter_ms_nodes(payload: Dict[str, Any]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    for question in payload.get("questions", []):
        q_node = question.get("question") or {}
        key = (q_node.get("parsed_marker") or {}).get("normalized_key") or "?"
        yield (key, q_node)
        for primary in question.get("primary_subparts", []):
            p_node = primary.get("primary") or {}
            p_key = (p_node.get("parsed_marker") or {}).get("normalized_key") or f"{key}|?"
            yield (p_key, p_node)
            for secondary in primary.get("secondary_subparts", []):
                s_node = secondary.get("secondary") or {}
                s_key = (s_node.get("parsed_marker") or {}).get("normalized_key") or f"{p_key}|?"
                yield (s_key, s_node)


def validate_ms_dir(ms_dir: Path, max_items: int) -> Dict[str, Any]:
    files = sorted(ms_dir.glob("*/mark_scheme.json"))
    empty_question_lists: List[str] = []
    garbage_answers: List[Dict[str, Any]] = []
    unresolved_row_counts: Dict[str, int] = {}
    nodes_total = 0
    nodes_with_answer = 0
    nodes_with_marks = 0
    marks_without_answer: List[str] = []

    for path in files:
        paper_code = path.parent.name
        payload = _load_json(path)
        if not payload.get("questions"):
            empty_question_lists.append(paper_code)
            continue
        unresolved = payload.get("unresolved_rows") or []
        if unresolved:
            unresolved_row_counts[paper_code] = len(unresolved)
        for key, node in iter_ms_nodes(payload):
            nodes_total += 1
            answer = (node.get("answer_text") or "").strip()
            marks_value = node.get("marks_value")
            if answer:
                nodes_with_answer += 1
                hits = _garbage_hits(answer)
                if hits:
                    garbage_answers.append({"node": f"{paper_code}:{key}", "patterns": hits})
            if marks_value is not None:
                nodes_with_marks += 1
                if not answer:
                    marks_without_answer.append(f"{paper_code}:{key}")

    return {
        "ms_files": len(files),
        "empty_question_lists": {"count": len(empty_question_lists), "items": empty_question_lists[:max_items]},
        "nodes_total": nodes_total,
        "nodes_with_answer_text": nodes_with_answer,
        "nodes_with_marks_value": nodes_with_marks,
        "marks_without_answer_text": {
            "count": len(marks_without_answer),
            "items": marks_without_answer[:max_items],
        },
        "garbage_answer_text": {"count": len(garbage_answers), "items": garbage_answers[:max_items]},
        "papers_with_unresolved_rows": unresolved_row_counts,
    }


def _ms_matched_node(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the mark-scheme node a record claims to match, if any."""
    ms_entry = record.get("ms_entry")
    if not isinstance(ms_entry, dict):
        return None

    # Primary/secondary joins store the resolved mark-scheme node directly;
    # question-level joins store the {question, primary_subparts} subtree.
    if "answer_text" in ms_entry:
        return ms_entry

    def norm(value: Any) -> str:
        text = str(value or "").strip().lower()
        return text[1:-1] if text.startswith("(") and text.endswith(")") else text

    level = record.get("ms_level") or record.get("segment_kind")
    if level == "question":
        return ms_entry.get("question")
    primary_target = norm(record.get("primary_marker"))
    primary_part = next(
        (
            part
            for part in ms_entry.get("primary_subparts", [])
            if norm((part.get("primary") or {}).get("text")) == primary_target
        ),
        None,
    )
    if level == "primary":
        return (primary_part or {}).get("primary")
    if level == "secondary" and primary_part:
        secondary_target = norm(record.get("secondary_marker"))
        for subpart in primary_part.get("secondary_subparts", []):
            if norm((subpart.get("secondary") or {}).get("text")) == secondary_target:
                return subpart.get("secondary")
    return None


def _node_answer_text(record: Dict[str, Any], node: Optional[Dict[str, Any]]) -> str:
    """Answer text for the matched node, aggregating subparts for question-level records."""
    if not isinstance(node, dict):
        return ""
    answer = (node.get("answer_text") or "").strip()
    if answer or (record.get("ms_level") or record.get("segment_kind")) != "question":
        return answer
    parts: List[str] = []
    for part in (record.get("ms_entry") or {}).get("primary_subparts", []):
        primary = part.get("primary") or {}
        parts.append((primary.get("answer_text") or "").strip())
        for subpart in part.get("secondary_subparts", []):
            secondary = subpart.get("secondary") or {}
            parts.append((secondary.get("answer_text") or "").strip())
    return "\n".join(part for part in parts if part)


def validate_final_records(final_json: Path, max_items: int) -> Dict[str, Any]:
    payload = _load_json(final_json)
    records = payload.get("records", [])
    summary = payload.get("summary") or {}

    no_ms_entry: List[int] = []
    no_ms_answer: List[int] = []
    no_marking_points: List[int] = []
    missing_screenshots: List[Dict[str, Any]] = []
    empty_question_text: List[int] = []

    for record in records:
        record_id = record.get("id")
        if record.get("schema_version") == "pseudocode-question-record/v1":
            if not (record.get("question_text") or "").strip():
                empty_question_text.append(record_id)
            mark_scheme = record.get("mark_scheme") or {}
            if not (mark_scheme.get("answer_text") or "").strip():
                no_ms_answer.append(record_id)
            if not mark_scheme.get("marking_points"):
                no_marking_points.append(record_id)
            shots = (record.get("provenance") or {}).get("screenshots") or {}
            for kind in ("selected_segment", "question_context"):
                path_value = shots.get(kind)
                if path_value and not Path(path_value).exists():
                    missing_screenshots.append({"id": record_id, "path": path_value})
            continue

        question_text = (
            (record.get("qp_selected_entry") or {}).get("content_text") or ""
        ).strip()
        if not question_text:
            empty_question_text.append(record_id)
        node = _ms_matched_node(record)
        if node is None:
            no_ms_entry.append(record_id)
        elif not _node_answer_text(record, node):
            no_ms_answer.append(record_id)
        if not record.get("marking_points"):
            no_marking_points.append(record_id)
        shots = record.get("screenshots") or {}
        for kind in ("selected_segment_path", "question_context_path"):
            path_value = shots.get(kind)
            if path_value and not Path(path_value).exists():
                missing_screenshots.append({"id": record_id, "path": path_value})

    return {
        "final_json": str(final_json),
        "record_count": len(records),
        "discarded_not_found_count": summary.get("discarded_not_found_count"),
        "records_without_ms_match": {"count": len(no_ms_entry), "items": no_ms_entry[:max_items]},
        "records_without_ms_answer_text": {"count": len(no_ms_answer), "items": no_ms_answer[:max_items]},
        "records_without_marking_points": {
            "count": len(no_marking_points),
            "items": no_marking_points[:max_items],
        },
        "records_with_empty_question_text": {
            "count": len(empty_question_text),
            "items": empty_question_text[:max_items],
        },
        "missing_screenshot_files": {
            "count": len(missing_screenshots),
            "items": missing_screenshots[:max_items],
        },
    }


def build_report(
    qp_dir: Path, ms_dir: Path, final_json: Path, max_items: int
) -> Dict[str, Any]:
    report: Dict[str, Any] = {"schema_version": "extraction-validation/v1"}
    report["qp"] = (
        validate_qp_dir(qp_dir, max_items)
        if qp_dir.is_dir()
        else {"error": f"missing directory: {qp_dir}"}
    )
    report["ms"] = (
        validate_ms_dir(ms_dir, max_items)
        if ms_dir.is_dir()
        else {"error": f"missing directory: {ms_dir}"}
    )
    report["final_records"] = (
        validate_final_records(final_json, max_items)
        if final_json.is_file()
        else {"error": f"missing file: {final_json}"}
    )
    return report


def print_summary(report: Dict[str, Any]) -> None:
    qp = report.get("qp", {})
    ms = report.get("ms", {})
    final = report.get("final_records", {})

    def count(section: Dict[str, Any], key: str) -> Any:
        value = section.get(key)
        return value.get("count") if isinstance(value, dict) and "count" in value else value

    print("QP segmented files:", qp.get("segmented_files"))
    print("QP total segments:", qp.get("total_segments"))
    print("QP empty hierarchies:", count(qp, "empty_hierarchies"))
    print("QP empty segment text:", count(qp, "empty_segment_text"))
    print("QP short segment text:", count(qp, "short_segment_text"))
    print("QP garbage segments:", count(qp, "garbage_segments"))
    print("QP invalid content bboxes:", count(qp, "invalid_content_bboxes"))
    print("QP invalid page refs:", count(qp, "invalid_page_refs"))
    print("MS files:", ms.get("ms_files"))
    print("MS empty question lists:", count(ms, "empty_question_lists"))
    print("MS nodes with answer text:", ms.get("nodes_with_answer_text"), "/", ms.get("nodes_total"))
    print("MS marks without answer text:", count(ms, "marks_without_answer_text"))
    print("MS garbage answer text:", count(ms, "garbage_answer_text"))
    print("Final records:", final.get("record_count"))
    print("Final records without MS match:", count(final, "records_without_ms_match"))
    print("Final records without MS answer text:", count(final, "records_without_ms_answer_text"))
    print("Final records without marking points:", count(final, "records_without_marking_points"))
    print("Final records with empty question text:", count(final, "records_with_empty_question_text"))
    print("Final missing screenshot files:", count(final, "missing_screenshot_files"))


def main() -> int:
    args = parse_args()
    report = build_report(args.qp_dir, args.ms_dir, args.final_json, args.max_items)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print_summary(report)
    print(f"\nWrote validation report to {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
