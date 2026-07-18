"""CLI entrypoint for qsplitter diagnostics."""

import argparse
from pathlib import Path

from .diagnostics import run_diagnostics_for_paper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run structural diagnostics for one qsplitter paper.")
    parser.add_argument("--paper", required=True, help="Paper code to diagnose.")
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        required=True,
        help="Directory containing the source PDFs.",
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    issues = run_diagnostics_for_paper(args.paper, args.pdf_dir, args.ocr_dir, args.marker_dir)
    if issues:
        print("Diagnostics failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Diagnostics passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
