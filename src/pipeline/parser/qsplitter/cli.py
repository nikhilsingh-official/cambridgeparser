"""CLI entrypoint for qsplitter."""

import argparse
from pathlib import Path

from . import process_all_papers, process_paper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build qsplitter outputs from OCR and marker inputs.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--paper", help="Paper code to process.")
    group.add_argument(
        "--all",
        action="store_true",
        help="Process every paper found in the marker directory.",
    )
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
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write qsplitter outputs.",
    )
    parser.add_argument(
        "--debug-bboxes",
        action="store_true",
        help="Render debug page images and overlay computed segment content boxes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.all:
        results = process_all_papers(
            args.pdf_dir,
            args.ocr_dir,
            args.marker_dir,
            args.output_dir,
            debug_bboxes=args.debug_bboxes,
        )
        print(f"Processed {len(results)} papers, outputs in {args.output_dir}")
        return 0

    process_paper(
        args.paper,
        args.pdf_dir,
        args.ocr_dir,
        args.marker_dir,
        args.output_dir,
        debug_bboxes=args.debug_bboxes,
    )
    print(f"Wrote qsplitter output for {args.paper} to {args.output_dir / args.paper}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
