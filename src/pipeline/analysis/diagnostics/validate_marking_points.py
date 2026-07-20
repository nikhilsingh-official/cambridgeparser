"""Read-only audit of marking-point quality in the final records.

Turns the manual marking-point audit into an automated, repeatable report so we
have a scope baseline before any behaviour change and a regression gate after
each fix. It inspects only
``pseudocode_writing_hits/pseudocode_question_records.json`` — it never touches
the parser, ms_output, or the records themselves.

Each record is checked against a set of flags grouped by severity:

  high    — actively wrong / grading-unsafe marking points:
            meta_mp, fragment_mp, lone_mp_discarded_list, over_expansion,
            rubric_selection_mismatch
  medium  — likely lossy or needs review:
            undercount, multi_rubric, multi_solution
  low     — informational:
            mp_crossref_in_text, codey_mp, duplicate_mp, alt_groups,
            no_marking_points

Counts are measured per alternative-solution group (``alt_group``), because
alternatives are mutually exclusive: a 5-mark question with two 5-point
alternatives holds 10 points but is not over-expanded.

Usage:

    python -m src.pipeline.analysis.diagnostics.validate_marking_points \
        --records pseudocode_writing_hits/pseudocode_question_records.json \
        --output-json pseudocode_writing_hits/marking_point_validation.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from ...pseudocode_tools.extract_marking_points import (
    HEADER_PATTERNS,
    NUM_ITEM_PATTERN,
)

SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1, "none": 0}

# An MP whose text is itself rubric/meta wording rather than a gradeable
# criterion. Deliberately narrow: "One mark for TYPE and ENDTYPE statements" is a
# real, specific MP, but "one mark for each of the remaining bold parts" is a
# collapsed meta description, so only the collapsed forms are matched.
META_MP_PATTERN = re.compile(
    r"^(underlin\w*|bold|highlight\w*|note\b|n\.?b\.?\b|guidance\b|in\s+a\s+loop\b"
    r"|as\s+above\b|part-?statements?\b"
    r"|.*\beach\s+of\s+(?:the\s+)?(?:following|remaining)\b"
    r"|.*\bremaining\s+\w+\s+(?:bold\s+)?parts?\b)",
    re.IGNORECASE,
)
# A convention where the marks are underlined/highlighted/bold spans, not text.
STYLE_CONVENTION_PATTERN = re.compile(
    r"underlined|highlighted|part-?statement|bold\s+part|per\s+bold|as\s+circled",
    re.IGNORECASE,
)
TEXT_DERIVED_STYLES = {"numbered_list", "mp_label", "bullet", "one_mark_bullet"}
# A stray "MPn" cross-reference that leaked into an MP's text (usually benign —
# e.g. "...use count from MP4 to generate..." — so only informational).
MP_CROSSREF_PATTERN = re.compile(r"\bMP\s?\d")
# Foreign content merged into the tail of an MP despite the count being right: a
# code header (a following example solution) or a "Note" that should have been a
# boundary, appearing after some real description text.
APPENDED_CONTENT_PATTERN = re.compile(
    r".\s(?:FUNCTION|PROCEDURE)\s+\w+\s*\(|\w\s+Notes?\b\s*:?", re.IGNORECASE
)
# Assignment / comparison operators that mark an MP as code rather than prose.
CODEY_PATTERN = re.compile("(\\u2190|\\uf0ac|>=|<=|:=|&|\\bMOD\\b|\\bDIV\\b)")
SOLUTION_NAME_PATTERN = re.compile(r"^\s*(?:FUNCTION|PROCEDURE)\s+([A-Za-z_]\w*)", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit marking-point quality (read-only).")
    parser.add_argument(
        "--records",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_question_records.json"),
    )
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument(
        "--limit", type=int, default=60, help="Rows to print in the console table."
    )
    return parser.parse_args()


def _alpha_count(text: str) -> int:
    return sum(1 for ch in text if ch.isalpha())


def _count_rubric_headers(answer_text: str) -> int:
    count = 0
    for line in answer_text.splitlines():
        stripped = line.strip()
        if stripped and any(p.search(stripped) for p in HEADER_PATTERNS):
            count += 1
    return count


def _count_numbered_items(answer_text: str) -> int:
    count = 0
    for line in answer_text.splitlines():
        match = NUM_ITEM_PATTERN.match(line.strip())
        if match and match.group(2) is not None and re.search(r"[A-Za-z]", match.group(3) or ""):
            # A dotted / parenthesised number with prose after it.
            count += 1
        elif match and re.search(r"[A-Za-z]", match.group(3) or ""):
            count += 1
    return count


def _distinct_solution_names(answer_text: str) -> List[str]:
    names = []
    for line in answer_text.splitlines():
        match = SOLUTION_NAME_PATTERN.match(line)
        if match:
            name = match.group(1).lower()
            if name not in names:
                names.append(name)
    return names


def _by_alt_group(points: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    groups: Dict[int, List[Dict[str, Any]]] = {}
    for point in points:
        key = point.get("alt_group")
        groups.setdefault(key if isinstance(key, int) else 0, []).append(point)
    return [groups[key] for key in sorted(groups)]


def audit_record(record: Dict[str, Any]) -> Dict[str, Any]:
    ms = record.get("mark_scheme") or {}
    points = ms.get("marking_points") or []
    texts = [str(p.get("text") or "") for p in points]
    # Alternative-solution rubrics are mutually exclusive, so a record is only
    # over-expanded when a *single* alternative exceeds the mark cap.
    alt_groups = _by_alt_group(points)
    largest_group = max((len(g) for g in alt_groups), default=0)
    answer_text = ms.get("answer_text") or ""
    style = points[0].get("style") if points else None
    max_marks = ms.get("max_marks")
    marks_value = ms.get("marks_value")
    cap = max_marks if isinstance(max_marks, int) else (marks_value if isinstance(marks_value, int) else None)

    header_count = _count_rubric_headers(answer_text)
    numbered_items = _count_numbered_items(answer_text)
    solution_names = _distinct_solution_names(answer_text)

    flags: List[str] = []

    # ---- high severity: actively wrong / unsafe ----
    if any(META_MP_PATTERN.match(t.strip()) for t in texts):
        flags.append("meta_mp")
    # A terse point is only suspect when the split that produced it is
    # unverified. Under a "one mark per underlined part" convention a mark really
    # can be "= 5" or "[0:99, 0:1]", and hitting the scheme's own mark total
    # exactly is the corroboration that each piece is a mark.
    corroborated = isinstance(cap, int) and largest_group == cap
    if not corroborated and any(_alpha_count(t) < 3 for t in texts):
        flags.append("fragment_mp")
    if style == "mp_label" and len(points) == 1 and numbered_items >= 2:
        flags.append("lone_mp_discarded_list")
    # Some schemes deliberately list more criteria than marks ("One mark per
    # point (Max 8):" above nine items). That cap is the scheme's own design and
    # the grading layer enforces it, so it is not an extraction defect.
    declared_max = ms.get("marking_points_max")
    if isinstance(cap, int) and largest_group > cap:
        if isinstance(declared_max, int) and declared_max <= cap:
            flags.append("declared_max_list")
        else:
            flags.append("over_expansion")
    # Contamination signal: the answer declares an underline/bold/highlight
    # convention, yet the extracted points are a text list — the extractor
    # jumped past the intended rubric to a later (often foreign) block.
    if STYLE_CONVENTION_PATTERN.search(answer_text) and style in TEXT_DERIVED_STYLES:
        flags.append("rubric_selection_mismatch")

    # ---- medium severity: lossy / review ----
    if isinstance(cap, int) and 0 < largest_group < cap:
        flags.append("undercount")
    if header_count >= 2:
        flags.append("multi_rubric")
    if len(solution_names) >= 2:
        flags.append("multi_solution")
    if any(APPENDED_CONTENT_PATTERN.search(t) for t in texts):
        flags.append("appended_content")

    # ---- low severity: informational ----
    if any(MP_CROSSREF_PATTERN.search(t) for t in texts):
        flags.append("mp_crossref_in_text")
    if style not in ("underlined", "manual_override") and any(CODEY_PATTERN.search(t) for t in texts):
        flags.append("codey_mp")
    # Repeats are only suspicious inside one rubric; alternatives legitimately
    # restate shared criteria.
    for group in alt_groups:
        lowered = [str(p.get("text") or "").strip().lower() for p in group]
        if len(lowered) != len(set(lowered)):
            flags.append("duplicate_mp")
            break
    if len(alt_groups) > 1:
        flags.append("alt_groups")
    if not points:
        flags.append("no_marking_points")

    severity = "none"
    for flag in flags:
        severity = _worst(severity, _flag_severity(flag))

    sk = record.get("segment_key") or {}
    return {
        "id": record.get("id"),
        "paper_code": record.get("paper_code"),
        "marker": f"q{sk.get('question_marker')}{sk.get('primary_marker') or ''}{sk.get('secondary_marker') or ''}",
        "style": style,
        "mp_count": len(points),
        "alt_group_count": len(alt_groups),
        "largest_alt_group": largest_group,
        "cap": cap,
        "header_count": header_count,
        "numbered_items": numbered_items,
        "solution_names": solution_names,
        "flags": flags,
        "severity": severity,
    }


_HIGH = {
    "meta_mp",
    "fragment_mp",
    "lone_mp_discarded_list",
    "over_expansion",
    "rubric_selection_mismatch",
}
_MEDIUM = {"undercount", "multi_rubric", "multi_solution", "appended_content"}


def _flag_severity(flag: str) -> str:
    if flag in _HIGH:
        return "high"
    if flag in _MEDIUM:
        return "medium"
    return "low"


def _worst(a: str, b: str) -> str:
    return a if SEVERITY_ORDER[a] >= SEVERITY_ORDER[b] else b


def run(records_path: Path) -> Dict[str, Any]:
    payload = json.loads(records_path.read_text())
    audited = [audit_record(r) for r in payload.get("records") or []]

    flag_counts: Dict[str, int] = {}
    severity_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0, "none": 0}
    for row in audited:
        severity_counts[row["severity"]] += 1
        for flag in row["flags"]:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

    return {
        "records_audited": len(audited),
        "severity_counts": severity_counts,
        "flag_counts": dict(sorted(flag_counts.items(), key=lambda kv: -kv[1])),
        "records": sorted(
            audited, key=lambda r: (-SEVERITY_ORDER[r["severity"]], -len(r["flags"]), r["id"])
        ),
    }


def _print_report(report: Dict[str, Any], limit: int) -> None:
    print(f"Audited {report['records_audited']} records")
    sc = report["severity_counts"]
    print(f"Severity: high {sc['high']} | medium {sc['medium']} | low {sc['low']} | clean {sc['none']}")
    print("\nFlag counts (a record may carry several):")
    for flag, count in report["flag_counts"].items():
        print(f"  {flag:<24} {count}")

    flagged = [r for r in report["records"] if r["severity"] != "none"]
    print(f"\nTop {min(limit, len(flagged))} flagged records (severity, id, marker, mp/cap, flags):")
    header = f"{'sev':<7} {'id':>4} {'paper':<15} {'marker':<10} {'mp/cap':>7}  flags"
    print(header)
    print("-" * len(header))
    for row in flagged[:limit]:
        cap = row["cap"] if row["cap"] is not None else "?"
        print(
            f"{row['severity']:<7} {row['id']:>4} {row['paper_code']:<15} {row['marker']:<10} "
            f"{str(row['mp_count']) + '/' + str(cap):>7}  {', '.join(row['flags'])}"
        )


def main() -> int:
    args = parse_args()
    if not args.records.is_file():
        print(f"Records file not found: {args.records}")
        return 2
    report = run(args.records)
    _print_report(report, args.limit)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nWrote full audit to {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
