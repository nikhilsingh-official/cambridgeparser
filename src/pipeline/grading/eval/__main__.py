"""Grade the hand-authored candidate answers and compare to predicted marks.

    python -m src.pipeline.grading.eval \
        --records resources/generated/pseudocode_writing_hits/pseudocode_question_records.json

Without OPENROUTER_API_KEY the grader runs in dry-run mode (a deterministic
placeholder), which only exercises the harness; set the key to measure how well
the model's awarded marks track the human-predicted marks in ``cases.py``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.resources.paths import PSEUDOCODE_QUESTION_RECORDS_JSON

from ..ast_adapter import parse_answer
from ..router import grade_answer_routed
from .cases import CASES

Key = Tuple[str, str, Optional[str], Optional[str]]


def _record_key(record: Dict[str, Any]) -> Key:
    sk = record.get("segment_key") or {}
    return (
        record.get("paper_code"),
        str(sk.get("question_marker")),
        sk.get("primary_marker"),
        sk.get("secondary_marker"),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate grading against predicted marks.")
    parser.add_argument(
        "--records",
        type=Path,
        default=PSEUDOCODE_QUESTION_RECORDS_JSON,
    )
    parser.add_argument("--parse-timeout", type=float, default=10.0)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path to write the full per-candidate results.",
    )
    return parser.parse_args()


def run(records_path: Path, parse_timeout: float) -> Dict[str, Any]:
    payload = json.loads(records_path.read_text())
    by_key: Dict[Key, Dict[str, Any]] = {
        _record_key(r): r for r in payload.get("records") or []
    }
    results: List[Dict[str, Any]] = []
    missing: List[Key] = []
    for case in CASES:
        key = tuple(case["key"])  # type: ignore[assignment]
        record = by_key.get(key)  # type: ignore[arg-type]
        if record is None:
            missing.append(key)  # type: ignore[arg-type]
            continue
        max_marks = (record.get("mark_scheme") or {}).get("max_marks")
        for candidate in case["candidates"]:
            parsed = parse_answer(candidate["answer"], timeout=parse_timeout)
            # Route exactly as production does, so the eval measures the
            # provider and model that actually grade student answers.
            grading = grade_answer_routed(record, parsed)
            awarded = None
            if grading.get("ok"):
                awarded = (grading.get("result") or {}).get("total_awarded")
            results.append(
                {
                    "title": case["title"],
                    "type": case["type"],
                    "quality": candidate["quality"],
                    "predicted": candidate["predicted"],
                    "awarded": awarded,
                    "max_marks": max_marks,
                    "parse_ok": bool((parsed.get("parse") or {}).get("ok")),
                    "grading_ok": bool(grading.get("ok")),
                    "dry_run": bool(grading.get("dry_run")),
                    "error": grading.get("error"),
                    "rationale": candidate["rationale"],
                }
            )
    return {"results": results, "missing_keys": [list(k) for k in missing]}


def _summarise(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    scored = [r for r in results if isinstance(r.get("awarded"), int) and isinstance(r.get("predicted"), int)]
    n = len(scored)
    if n == 0:
        return {"scored": 0}
    abs_err = [abs(r["awarded"] - r["predicted"]) for r in scored]
    return {
        "scored": n,
        "exact": sum(1 for e in abs_err if e == 0),
        "within_1": sum(1 for e in abs_err if e <= 1),
        "mae": round(sum(abs_err) / n, 2),
        "over_predicted": sum(1 for r in scored if r["awarded"] > r["predicted"]),
        "under_predicted": sum(1 for r in scored if r["awarded"] < r["predicted"]),
    }


def _print_report(payload: Dict[str, Any]) -> None:
    results = payload["results"]
    dry = any(r["dry_run"] for r in results)
    if dry:
        print("MODE: DRY RUN (no OPENROUTER_API_KEY) — placeholder marks; set the key for a real test.\n")
    header = f"{'type':<9} {'quality':<7} {'pred':>4} {'ai':>4} {'max':>4}  title"
    print(header)
    print("-" * len(header))
    last_title = None
    for r in results:
        title = r["title"] if r["title"] != last_title else ""
        last_title = r["title"]
        awarded = r["awarded"] if r["awarded"] is not None else "-"
        flag = ""
        if isinstance(r["awarded"], int):
            delta = r["awarded"] - r["predicted"]
            flag = " " if delta == 0 else (f" (+{delta})" if delta > 0 else f" ({delta})")
        print(
            f"{r['type']:<9} {r['quality']:<7} {r['predicted']:>4} {str(awarded):>4} "
            f"{str(r['max_marks']):>4}{flag:<6} {title[:52]}"
        )

    summary = _summarise(results)
    print()
    if summary.get("scored"):
        print(
            f"Scored {summary['scored']} candidates | exact {summary['exact']} | "
            f"within-1 {summary['within_1']} | MAE {summary['mae']} | "
            f"AI over {summary['over_predicted']} / under {summary['under_predicted']}"
        )
    if payload["missing_keys"]:
        print(f"WARNING: {len(payload['missing_keys'])} case(s) had no matching record: "
              f"{payload['missing_keys']}")


def main() -> int:
    args = parse_args()
    if not args.records.is_file():
        print(f"Records file not found: {args.records}")
        return 2
    payload = run(args.records, args.parse_timeout)
    _print_report(payload)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"\nWrote full results to {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
