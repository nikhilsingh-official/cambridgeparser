"""Batch runner for qsplitter diagnostics."""

import argparse
import json
from pathlib import Path

from src.pipeline.analysis.diagnostics.diagnostics import run_diagnostics_for_paper
from src.pipeline.parser import qsplitter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run diagnostics across every question paper with complete inputs.")
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        required=True,
        help="Directory containing the PDFs to diagnose.",
    )
    parser.add_argument(
        "--ocr-dir",
        type=Path,
        required=True,
        help="Directory containing OCR outputs (per-paper folder with results.json).",
    )
    parser.add_argument(
        "--marker-dir",
        type=Path,
        required=True,
        help="Directory containing normalized marker output (per-paper folder with <paper>.json).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write debug outputs.",
    )
    return parser.parse_args()


def has_required_inputs(paper_code: str, ocr_dir: Path, marker_dir: Path) -> bool:
    has_ocr = (ocr_dir / paper_code / "results.json").exists()
    has_marker = (marker_dir / paper_code / f"{paper_code}.json").exists()
    return has_ocr and has_marker


def main() -> int:
    args = parse_args()
    all_paper_codes = sorted(path.stem for path in args.pdf_dir.glob("*.pdf") if path.is_file())
    question_paper_codes = [paper_code for paper_code in all_paper_codes if "_qp_" in paper_code]
    paper_codes = [
        paper_code
        for paper_code in question_paper_codes
        if has_required_inputs(paper_code, args.ocr_dir, args.marker_dir)
    ]
    skipped_codes = [paper_code for paper_code in question_paper_codes if paper_code not in paper_codes]

    if not paper_codes:
        print(f"No PDFs found in {args.pdf_dir}.")
        return 1

    print(f"Found {len(paper_codes)} papers in {args.pdf_dir}")
    if skipped_codes:
        preview = ", ".join(skipped_codes[:5])
        suffix = "" if len(skipped_codes) <= 5 else f" ... (+{len(skipped_codes) - 5} more)"
        print(f"Skipping {len(skipped_codes)} papers without complete OCR/marker inputs: {preview}{suffix}")

    passed: list[str] = []
    failed: list[tuple[str, list[str]]] = []

    for code in paper_codes:
        issues = run_diagnostics_for_paper(code, args.pdf_dir, args.ocr_dir, args.marker_dir)
        
        # Always generate hierarchy
        try:
            context = qsplitter.load_paper_context(code, args.pdf_dir, args.ocr_dir, args.marker_dir)
            hierarchy = qsplitter.build_hierarchical_structure(
                code,
                args.pdf_dir,
                args.ocr_dir,
                args.marker_dir,
                context=context,
            )
            output_paper_dir = args.output_dir / code
            output_paper_dir.mkdir(parents=True, exist_ok=True)

            hierarchy_path = output_paper_dir / "hierarchy.json"
            with hierarchy_path.open("w") as handle:
                json.dump(hierarchy, handle, indent=2)

            if issues:
                failed.append((code, issues))
                print(f"{code} failed diagnostics:")
                for issue in issues:
                    print(f"  - {issue}")
                print(f"Generated debug artifacts for {code}")
            else:
                passed.append(code)
        except Exception as exc:
            if issues:
                failed.append((code, issues))
                print(f"{code} failed diagnostics:")
                for issue in issues:
                    print(f"  - {issue}")
            print(f"Warning: failed to generate artifacts for {code}: {exc}")

    print("\nDiagnostics batch complete")
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failed papers:")
        for code, issues in failed:
            print(f"  {code}")
            for issue in issues:
                print(f"    - {issue}")
        print(f"Debug artifacts written to: {args.output_dir}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
