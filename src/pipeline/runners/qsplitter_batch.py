"""Batch runner for qsplitter hierarchy generation."""

import argparse
from pathlib import Path

from src.pipeline.parser.qsplitter import process_paper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run qsplitter over every question paper with complete inputs.")
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        required=True,
        help="Directory containing the PDFs to process.",
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
        help="Directory to write qsplitter outputs.",
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

    errors: list[str] = []
    for code in paper_codes:
        print(f"\n=== Processing: {code}")
        try:
            process_paper(code, args.pdf_dir, args.ocr_dir, args.marker_dir, args.output_dir)
        except Exception as exc:
            print(f"qsplitter failed for {code}: {exc}")
            errors.append(code)

    print("\nBatch run complete")
    if errors:
        print(f"Errors for {len(errors)} papers")
        for code in errors:
            print(code)
        return 1

    print("All papers processed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
