"""Helpers for locating question segments inside generated QP artifacts."""

from __future__ import annotations

from typing import Any, Dict, Optional


def normalize_marker(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("(") and text.endswith(")") and len(text) > 2:
        text = text[1:-1]
    return text


def find_qp_question(
    qp_payload: Dict[str, Any], question_marker: str
) -> Optional[Dict[str, Any]]:
    target = normalize_marker(question_marker)
    for question in qp_payload.get("questions", []):
        node = question.get("question") or {}
        if normalize_marker(node.get("text")) == target:
            return question
    return None


def find_qp_node(
    question_entry: Dict[str, Any],
    segment_kind: str,
    primary_marker: Any,
    secondary_marker: Any,
) -> Optional[Dict[str, Any]]:
    if segment_kind == "question":
        return question_entry.get("question")
    primary_target = normalize_marker(primary_marker)
    for primary in question_entry.get("primary_subparts", []):
        p_node = primary.get("primary") or {}
        if normalize_marker(p_node.get("text")) != primary_target:
            continue
        if segment_kind == "primary":
            return p_node
        secondary_target = normalize_marker(secondary_marker)
        for secondary in primary.get("secondary_subparts", []):
            s_node = secondary.get("secondary") or {}
            if normalize_marker(s_node.get("text")) == secondary_target:
                return s_node
        return None
    return None
