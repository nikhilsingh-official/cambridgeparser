"""Build canonical pseudocode question records from selection, QP, and MS artifacts.

This replaces the ad hoc join steps that previously produced the final
pseudocode-writing JSON. It consumes:

- selected pseudocode-writing hits (select_pseudocode_writing.py output);
- qp_output/<paper>/segmented_questions.json;
- ms_output/<ms_paper>/mark_scheme.json;
- previously rendered screenshots when present (matched by marker slug).

and writes one canonical record file with schema
``pseudocode-question-record/v1``.

Usage:

    python -m src.pipeline.pseudocode_tools.build_final_records \
        --selected-json pseudocode_writing_hits/pseudocode_writing_selected.json \
        --qp-dir qp_output \
        --ms-dir ms_output \
        --screenshots-dir pseudocode_writing_hits/pseudocode_question_screenshots \
        --output-json pseudocode_writing_hits/pseudocode_question_records.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .extract_marking_points import (
    extract_structured_marking_points,
    marking_points_from_underlined_spans,
)

SCHEMA_VERSION = "pseudocode-question-record/v1"
TRAILING_MARKS_PATTERN = re.compile(r"\[\s*(\d+)\s*\]\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Join selected pseudocode hits with QP and MS artifacts into canonical records."
    )
    parser.add_argument(
        "--selected-json",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_writing_selected.json"),
    )
    parser.add_argument("--qp-dir", type=Path, default=Path("qp_output"))
    parser.add_argument("--ms-dir", type=Path, default=Path("ms_output"))
    parser.add_argument(
        "--screenshots-dir",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_question_screenshots"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_question_records.json"),
    )
    return parser.parse_args()


def _load_json(path: Path) -> Any:
    with path.open() as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _norm_marker(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("(") and text.endswith(")") and len(text) > 2:
        text = text[1:-1]
    return text


def ms_paper_code_for(paper_code: str) -> str:
    return paper_code.replace("_qp_", "_ms_")


def _find_qp_question(qp_payload: Dict[str, Any], question_marker: str) -> Optional[Dict[str, Any]]:
    target = _norm_marker(question_marker)
    for question in qp_payload.get("questions", []):
        node = question.get("question") or {}
        if _norm_marker(node.get("text")) == target:
            return question
    return None


def _find_qp_node(
    question_entry: Dict[str, Any],
    segment_kind: str,
    primary_marker: Any,
    secondary_marker: Any,
) -> Optional[Dict[str, Any]]:
    if segment_kind == "question":
        return question_entry.get("question")
    primary_target = _norm_marker(primary_marker)
    for primary in question_entry.get("primary_subparts", []):
        p_node = primary.get("primary") or {}
        if _norm_marker(p_node.get("text")) != primary_target:
            continue
        if segment_kind == "primary":
            return p_node
        secondary_target = _norm_marker(secondary_marker)
        for secondary in primary.get("secondary_subparts", []):
            s_node = secondary.get("secondary") or {}
            if _norm_marker(s_node.get("text")) == secondary_target:
                return s_node
        return None
    return None


def _find_ms_question(ms_payload: Dict[str, Any], question_marker: str) -> Optional[Dict[str, Any]]:
    target = _norm_marker(question_marker)
    for question in ms_payload.get("questions", []):
        node = question.get("question") or {}
        parsed = node.get("parsed_marker") or {}
        if str(parsed.get("question_number") or "").strip() == target:
            return question
    return None


def _find_ms_node(
    ms_question: Dict[str, Any],
    segment_kind: str,
    primary_marker: Any,
    secondary_marker: Any,
) -> Optional[Dict[str, Any]]:
    if segment_kind == "question":
        return ms_question.get("question")
    primary_target = _norm_marker(primary_marker)
    for primary in ms_question.get("primary_subparts", []):
        p_node = primary.get("primary") or {}
        parsed = p_node.get("parsed_marker") or {}
        marker = _norm_marker(parsed.get("primary_marker") or p_node.get("text"))
        if marker != primary_target:
            continue
        if segment_kind == "primary":
            return p_node
        secondary_target = _norm_marker(secondary_marker)
        for secondary in primary.get("secondary_subparts", []):
            s_node = secondary.get("secondary") or {}
            s_parsed = s_node.get("parsed_marker") or {}
            s_marker = _norm_marker(s_parsed.get("secondary_marker") or s_node.get("text"))
            if s_marker == secondary_target:
                return s_node
        return None
    return None


def _aggregate_question_answer(ms_question: Dict[str, Any]) -> Tuple[str, Optional[int]]:
    """Aggregate subpart answers for question-level records whose question node is empty."""
    parts: List[str] = []
    marks_total = 0
    marks_seen = False
    for primary in ms_question.get("primary_subparts", []):
        p_node = primary.get("primary") or {}
        p_text = (p_node.get("answer_text") or "").strip()
        p_marker = (p_node.get("text") or "").strip()
        if p_text:
            parts.append(f"{p_marker} {p_text}".strip())
        if isinstance(p_node.get("marks_value"), int):
            marks_total += p_node["marks_value"]
            marks_seen = True
        for secondary in primary.get("secondary_subparts", []):
            s_node = secondary.get("secondary") or {}
            s_text = (s_node.get("answer_text") or "").strip()
            s_marker = (s_node.get("text") or "").strip()
            if s_text:
                parts.append(f"{p_marker}{s_marker} {s_text}".strip())
            if isinstance(s_node.get("marks_value"), int):
                marks_total += s_node["marks_value"]
                marks_seen = True
    return "\n".join(parts), (marks_total if marks_seen else None)


def _qp_marks_value(question_text: str) -> Optional[int]:
    match = TRAILING_MARKS_PATTERN.search((question_text or "").strip())
    return int(match.group(1)) if match else None


def _marker_slug(hit: Dict[str, Any]) -> str:
    def safe(value: Any, prefix: str) -> str:
        text = str(value or "").strip().lower().replace("(", "").replace(")", "")
        text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
        return f"{prefix}{text or 'unknown'}"

    parts = [safe(hit.get("question_marker"), "q")]
    if hit.get("primary_marker"):
        parts.append(safe(hit.get("primary_marker"), "p"))
    if hit.get("secondary_marker"):
        parts.append(safe(hit.get("secondary_marker"), "s"))
    return "_".join(parts)


def _find_screenshot(
    screenshots_dir: Optional[Path], paper_code: str, slug: str, kind: str
) -> Optional[str]:
    if screenshots_dir is None:
        return None
    paper_dir = screenshots_dir / paper_code
    if not paper_dir.is_dir():
        return None
    matches = sorted(paper_dir.glob(f"*_{slug}_{kind}.png"))
    return str(matches[0]) if matches else None


def _content_pages_summary(node: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(node, dict):
        return []
    pages = []
    for page in node.get("content_pages") or []:
        if isinstance(page.get("page_index"), int):
            pages.append({"page_index": page["page_index"], "bbox": page.get("bbox")})
    return pages


def _ms_pages_summary(node: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(node, dict):
        return []
    pages = []
    for page in node.get("content_pages") or []:
        if isinstance(page.get("page_index"), int):
            pages.append(
                {
                    "page_index": page["page_index"],
                    "table_index": page.get("table_index"),
                    "row_index": page.get("row_index"),
                    "row_bbox": page.get("row_bbox"),
                }
            )
    return pages


def build_records(
    selected_hits: List[Dict[str, Any]],
    qp_dir: Path,
    ms_dir: Path,
    screenshots_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    qp_cache: Dict[str, Optional[Dict[str, Any]]] = {}
    ms_cache: Dict[str, Optional[Dict[str, Any]]] = {}

    def load_qp(paper_code: str) -> Optional[Dict[str, Any]]:
        if paper_code not in qp_cache:
            path = qp_dir / paper_code / "segmented_questions.json"
            qp_cache[paper_code] = _load_json(path) if path.is_file() else None
        return qp_cache[paper_code]

    def load_ms(ms_code: str) -> Optional[Dict[str, Any]]:
        if ms_code not in ms_cache:
            path = ms_dir / ms_code / "mark_scheme.json"
            ms_cache[ms_code] = _load_json(path) if path.is_file() else None
        return ms_cache[ms_code]

    records: List[Dict[str, Any]] = []
    discarded: List[Dict[str, Any]] = []
    next_id = 1

    for hit in selected_hits:
        paper_code = hit.get("paper_code") or "unknown"
        ms_code = ms_paper_code_for(paper_code)
        segment_kind = hit.get("segment_kind") or "question"
        diagnostics: List[str] = []

        def discard(reason: str) -> None:
            discarded.append(
                {
                    "paper_code": paper_code,
                    "ms_paper_code": ms_code,
                    "question_marker": hit.get("question_marker"),
                    "primary_marker": hit.get("primary_marker"),
                    "secondary_marker": hit.get("secondary_marker"),
                    "segment_kind": segment_kind,
                    "reason": reason,
                }
            )

        qp_payload = load_qp(paper_code)
        if qp_payload is None:
            discard("qp_segmented_questions_missing")
            continue
        question_entry = _find_qp_question(qp_payload, hit.get("question_marker"))
        if question_entry is None:
            discard("qp_question_not_found")
            continue
        qp_node = _find_qp_node(
            question_entry,
            segment_kind,
            hit.get("primary_marker"),
            hit.get("secondary_marker"),
        )
        if qp_node is None:
            discard("qp_segment_not_found")
            continue

        question_text = (qp_node.get("content_text") or "").strip()
        context_node = question_entry.get("question") or {}
        context_text = (context_node.get("content_text") or "").strip()

        ms_payload = load_ms(ms_code)
        ms_question = (
            _find_ms_question(ms_payload, hit.get("question_marker"))
            if ms_payload is not None
            else None
        )
        if ms_payload is None:
            discard("ms_output_missing")
            continue
        if ms_question is None:
            discard("ms_question_not_found")
            continue

        ms_node = _find_ms_node(
            ms_question,
            segment_kind,
            hit.get("primary_marker"),
            hit.get("secondary_marker"),
        )
        if ms_node is None:
            discard("ms_node_not_found")
            continue

        answer_text = (ms_node.get("answer_text") or "").strip()
        marks_text = (ms_node.get("marks_text") or "").strip()
        marks_value = ms_node.get("marks_value")
        if not answer_text and segment_kind == "question":
            answer_text, aggregated_marks = _aggregate_question_answer(ms_question)
            if answer_text:
                diagnostics.append("ms_answer_aggregated_from_subparts")
            if marks_value is None:
                marks_value = aggregated_marks
        if not answer_text:
            diagnostics.append("ms_answer_text_empty")

        extraction = extract_structured_marking_points(answer_text)
        marking_points = extraction["points"]
        if not marking_points:
            # No text rubric: recover the "one mark per underlined ..." schemes
            # from the underlined spans ms_parser captured, using the node's mark
            # value to decide how finely to split them.
            underlined_points = marking_points_from_underlined_spans(
                ms_node.get("answer_underlined_spans"),
                target_marks=marks_value if isinstance(marks_value, int) else None,
            )
            if underlined_points:
                marking_points = underlined_points
                diagnostics.append("marking_points_from_underlined_spans")
        if not marking_points:
            diagnostics.append("no_marking_points_extracted")

        qp_marks = _qp_marks_value(question_text)
        max_marks = marks_value if isinstance(marks_value, int) else None
        if max_marks is None:
            max_marks = extraction["max_marks"]
        if max_marks is None:
            max_marks = qp_marks

        slug = _marker_slug(hit)
        record = {
            "schema_version": SCHEMA_VERSION,
            "id": next_id,
            "paper_code": paper_code,
            "ms_paper_code": ms_code,
            "segment_key": {
                "question_marker": hit.get("question_marker"),
                "primary_marker": hit.get("primary_marker"),
                "secondary_marker": hit.get("secondary_marker"),
                "segment_kind": segment_kind,
            },
            "question_text": question_text,
            "question_context_text": context_text,
            "qp_marks_value": qp_marks,
            "mark_scheme": {
                "ms_level": segment_kind,
                "answer_text": answer_text,
                "marks_text": marks_text,
                "marks_value": marks_value,
                "max_marks": max_marks,
                "marking_points": marking_points,
                "marking_points_max": extraction["max_marks"],
            },
            "selection": {
                "matched_positive": hit.get("matched_positive") or [],
                "decision_reason": hit.get("decision_reason"),
            },
            "provenance": {
                "qp_pages": _content_pages_summary(qp_node),
                "context_pages": _content_pages_summary(context_node),
                "ms_pages": _ms_pages_summary(ms_node),
                "screenshots": {
                    "selected_segment": _find_screenshot(
                        screenshots_dir, paper_code, slug, "selected"
                    ),
                    "question_context": _find_screenshot(
                        screenshots_dir, paper_code, slug, "question_context"
                    ),
                },
            },
            "diagnostics": diagnostics,
        }
        records.append(record)
        next_id += 1

    summary = {
        "schema_version": SCHEMA_VERSION,
        "record_count": len(records),
        "discarded_count": len(discarded),
        "paper_count": len({record["paper_code"] for record in records}),
        "segment_kind_counts": _count_by(records, lambda r: r["segment_key"]["segment_kind"]),
        "records_with_marking_points": sum(
            1 for r in records if r["mark_scheme"]["marking_points"]
        ),
        "records_with_ms_answer_text": sum(
            1 for r in records if r["mark_scheme"]["answer_text"]
        ),
        "records_with_screenshots": sum(
            1
            for r in records
            if r["provenance"]["screenshots"]["selected_segment"]
        ),
        "discard_reasons": _count_by(discarded, lambda d: d["reason"]),
    }
    return {"summary": summary, "records": records, "discarded": discarded}


def _count_by(items: List[Dict[str, Any]], key_fn) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        key = str(key_fn(item))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def main() -> int:
    args = parse_args()
    selected_hits = _load_json(args.selected_json)
    if not isinstance(selected_hits, list):
        raise ValueError(f"Expected a list of selected hits in {args.selected_json}")
    payload = build_records(
        selected_hits,
        qp_dir=args.qp_dir,
        ms_dir=args.ms_dir,
        screenshots_dir=args.screenshots_dir,
    )
    _write_json(args.output_json, payload)
    summary = payload["summary"]
    print(json.dumps(summary, indent=2))
    print(f"Wrote {summary['record_count']} records to {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
