"""Select only prompts where students are asked to write pseudocode.

This script is intentionally phrase-first and does not use weighted keyword scoring.
It consumes segmented question outputs (segmented_questions.json) and classifies each
question/subpart as selected, review, or rejected.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Pattern


DEFAULT_POSITIVE_RULES = [
    r"\bwrite\s+(?:an?\s+)?pseudocode\b",
    r"\bwrite\s+(?:an?\s+)?pseudocode\s+(?:for|to|that)\b",
    r"(?:^|[\n.])\s*write\s+the\s+pseudocode\s+equivalent\b",
    r"(?:^|[\n.])\s*write\s+pseudocode\s+equivalent\b",
    r"\buse\s+pseudocode\s+to\s+(?:write|declare|define|design|develop|create)\b",
    r"\busing\s+pseudocode\s+to\s+(?:write|declare|define|design|develop|create)\b",
    r"\bin\s+pseudocode\s*,?\s*(?:write|declare|define|design|develop|create)\b",
    r"(?:^|[\n.])\s*write\b[^\n]{0,80}\bin\s+pseudocode\b",
    r"\bwrite\s+(?:the\s+)?pseudocode\s+header\b",
    r"\bre-?write\s+(?:the\s+)?pseudocode\b",
    r"\bwrite\s+(?:the\s+)?modified\s+pseudocode\b",
    r"\bwrite\s+(?:the\s+)?correct\s+pseudocode\b",
    r"\bwrite\s+the\s+changes\b[^\n]{0,80}\bpseudocode\b",
    r"\bwrite\s+similar\s+program\s+code\b",
    r"\busing\s+pseudocode\s*,?\s*write\b",
    r"\bconstruct\s+(?:an?\s+)?pseudocode\s+(?:for|to|that)\b",
    r"\bproduce\s+(?:an?\s+)?pseudocode\s+(?:for|to|that)\b",
    r"\bdevelop\s+(?:an?\s+)?pseudocode\s+(?:for|to|that)\b",
    r"\bwrite\s+an?\s+algorithm\s+in\s+pseudocode\b",
    r"\bcomplete\s+the\s+pseudocode\b",
]

DEFAULT_NEGATIVE_RULES = [
    r"\bwhat\s+does\s+(?:the\s+following\s+)?pseudocode\b",
    r"\btrace\s+(?:through\s+)?(?:the\s+)?pseudocode\b",
    r"\bstate\s+(?:the\s+)?output\b",
    r"\bexplain\b",
    r"\bdescribe\b",
    r"\bidentify\b",
    r"\bdry\s+run\b",
    r"\bdesk\s+check\b",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select pseudocode-writing prompts from qsplitter segmented outputs."
    )
    parser.add_argument(
        "--segments",
        type=Path,
        required=True,
        help="Path to segmented_questions.json or a directory containing per-paper segmented_questions.json files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/pseudocode_writing"),
        help="Directory to write selection outputs.",
    )
    parser.add_argument(
        "--rules-file",
        type=Path,
        help="Optional JSON file with {\"positive\": [...], \"negative\": [...]} regex rules.",
    )
    return parser.parse_args()


def _load_rules(rules_file: Path | None) -> tuple[list[str], list[str]]:
    positives = list(DEFAULT_POSITIVE_RULES)
    negatives = list(DEFAULT_NEGATIVE_RULES)
    if rules_file is None:
        return positives, negatives

    with rules_file.open() as handle:
        custom = json.load(handle)
    positives.extend(custom.get("positive", []))
    negatives.extend(custom.get("negative", []))
    return positives, negatives


def _compile_rules(patterns: Iterable[str]) -> list[Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


def _iter_segmented_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return

    for segmented_path in sorted(path.rglob("segmented_questions.json")):
        if segmented_path.is_file():
            yield segmented_path


def _match_patterns(text: str, patterns: list[Pattern[str]]) -> list[str]:
    snippet = text.lower()
    matches: list[str] = []
    for pattern in patterns:
        found = pattern.search(snippet)
        if found:
            matches.append(found.group(0))
    return matches


def _segment_record(
    paper_code: str,
    question_marker: str,
    segment_kind: str,
    marker: Dict[str, Any],
    text: str,
    positive_patterns: list[Pattern[str]],
    negative_patterns: list[Pattern[str]],
    primary_marker: str | None = None,
    secondary_marker: str | None = None,
) -> Dict[str, Any]:
    positive_hits = _match_patterns(text, positive_patterns)
    negative_hits = _match_patterns(text, negative_patterns)

    if positive_hits and not negative_hits:
        decision = "selected"
        reason = "Matched write-intent starter phrase and no negative phrase."
    elif positive_hits and negative_hits:
        decision = "review"
        reason = "Matched both positive and negative phrases."
    else:
        decision = "rejected"
        reason = "No write-intent starter phrase matched."

    return {
        "paper_code": paper_code,
        "question_marker": question_marker,
        "primary_marker": primary_marker,
        "secondary_marker": secondary_marker,
        "segment_kind": segment_kind,
        "page_index": marker.get("page_index"),
        "marker_bbox": marker.get("bbox"),
        "content_bbox": marker.get("content_bbox"),
        "content_source": marker.get("content_source"),
        "text": text,
        "matched_positive": positive_hits,
        "matched_negative": negative_hits,
        "decision": decision,
        "decision_reason": reason,
    }


def _supersede_ancestors_with_selected_descendant(
    q_record: Dict[str, Any],
    primary_groups: list[tuple[Dict[str, Any], list[Dict[str, Any]]]],
) -> None:
    """Demote a whole-question or whole-primary hit when a more specific subpart is selected.

    A question node's ``content_text`` concatenates all of its subparts, so a
    subpart whose stem says "write pseudocode" makes the ancestor question match
    the same positive phrase. Keeping both produces a duplicate whole-question
    record whose aggregated mark scheme mixes the non-pseudocode subparts (e.g.
    the marks for a structure-chart part (a)) into the pseudocode subpart (b).
    The specific pseudocode subpart is the real target; the whole question stays
    available only as context. So any ancestor that still has a selected
    descendant is superseded.
    """

    def supersede(record: Dict[str, Any], by: str) -> None:
        if record["decision"] == "selected":
            record["decision"] = "superseded"
            record["decision_reason"] = (
                f"Superseded by a more specific selected {by}; the pseudocode-writing "
                "prompt lives in that subpart and the whole segment is kept only as context."
            )

    for p_record, s_records in primary_groups:
        if any(s["decision"] == "selected" for s in s_records):
            supersede(p_record, "secondary subpart")

    descendant_selected = any(
        rec["decision"] == "selected"
        for p_record, s_records in primary_groups
        for rec in (p_record, *s_records)
    )
    if descendant_selected:
        supersede(q_record, "subpart")


def _extract_records_from_payload(
    payload: Dict[str, Any],
    positive_patterns: list[Pattern[str]],
    negative_patterns: list[Pattern[str]],
) -> list[Dict[str, Any]]:
    records: list[Dict[str, Any]] = []
    paper_code = payload.get("paper_code", "unknown")
    for question in payload.get("questions", []):
        q_marker = question["question"].get("text", "?")
        q_node = question["question"]
        q_text = q_node.get("content_text", "")
        q_record = _segment_record(
            paper_code=paper_code,
            question_marker=q_marker,
            segment_kind="question",
            marker=q_node,
            text=q_text,
            positive_patterns=positive_patterns,
            negative_patterns=negative_patterns,
        )
        records.append(q_record)

        primary_groups: list[tuple[Dict[str, Any], list[Dict[str, Any]]]] = []
        for primary in question.get("primary_subparts", []):
            p_node = primary["primary"]
            p_marker = p_node.get("text", "?")
            p_text = p_node.get("content_text", "")
            p_record = _segment_record(
                paper_code=paper_code,
                question_marker=q_marker,
                primary_marker=p_marker,
                segment_kind="primary",
                marker=p_node,
                text=p_text,
                positive_patterns=positive_patterns,
                negative_patterns=negative_patterns,
            )
            records.append(p_record)

            s_records: list[Dict[str, Any]] = []
            for secondary in primary.get("secondary_subparts", []):
                s_node = secondary["secondary"]
                s_marker = s_node.get("text", "?")
                s_text = s_node.get("content_text", "")
                s_record = _segment_record(
                    paper_code=paper_code,
                    question_marker=q_marker,
                    primary_marker=p_marker,
                    secondary_marker=s_marker,
                    segment_kind="secondary",
                    marker=s_node,
                    text=s_text,
                    positive_patterns=positive_patterns,
                    negative_patterns=negative_patterns,
                )
                records.append(s_record)
                s_records.append(s_record)

            primary_groups.append((p_record, s_records))

        _supersede_ancestors_with_selected_descendant(q_record, primary_groups)
    return records


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def run_selection(
    segments_path: Path,
    output_dir: Path,
    positive_rule_strings: list[str],
    negative_rule_strings: list[str],
) -> Dict[str, Any]:
    positive_patterns = _compile_rules(positive_rule_strings)
    negative_patterns = _compile_rules(negative_rule_strings)

    all_records: list[Dict[str, Any]] = []
    source_files = list(_iter_segmented_files(segments_path))
    if not source_files:
        raise FileNotFoundError(f"No segmented_questions.json files found under {segments_path}")

    for source_file in source_files:
        with source_file.open() as handle:
            payload = json.load(handle)
        all_records.extend(
            _extract_records_from_payload(payload, positive_patterns, negative_patterns)
        )

    selected = [r for r in all_records if r["decision"] == "selected"]
    review = [r for r in all_records if r["decision"] == "review"]
    rejected = [r for r in all_records if r["decision"] == "rejected"]
    superseded = [r for r in all_records if r["decision"] == "superseded"]

    report = {
        "source_files": [str(path) for path in source_files],
        "total_segments": len(all_records),
        "selected_count": len(selected),
        "review_count": len(review),
        "rejected_count": len(rejected),
        "superseded_count": len(superseded),
        "positive_rules": positive_rule_strings,
        "negative_rules": negative_rule_strings,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "pseudocode_writing_selected.json", selected)
    _write_json(output_dir / "pseudocode_writing_review.json", review)
    _write_json(output_dir / "pseudocode_writing_rejected.json", rejected)
    _write_json(output_dir / "pseudocode_writing_superseded.json", superseded)
    _write_json(output_dir / "pseudocode_rule_report.json", report)
    _write_json(output_dir / "pseudocode_rule_records.json", all_records)

    return report


def main() -> int:
    args = parse_args()
    positive_rules, negative_rules = _load_rules(args.rules_file)
    report = run_selection(
        segments_path=args.segments,
        output_dir=args.output_dir,
        positive_rule_strings=positive_rules,
        negative_rule_strings=negative_rules,
    )
    print(
        f"Selection complete: {report['selected_count']} selected, "
        f"{report['review_count']} review, {report['rejected_count']} rejected, "
        f"{report['superseded_count']} superseded by a subpart."
    )
    print(f"Outputs written to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
