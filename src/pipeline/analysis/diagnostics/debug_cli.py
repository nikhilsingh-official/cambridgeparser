"""CLI entrypoint for qsplitter debug rendering."""

import argparse
import json
from pathlib import Path

from src.pipeline.parser import qsplitter
from src.pipeline.parser.qsplitter.debug import write_reading_order_file
from src.pipeline.parser.qsplitter.segmentation import build_segmented_questions

from .debug_renderer import write_debug_page_images


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render debug artifacts for one qsplitter paper.")
    parser.add_argument("--paper", required=True, help="Paper code to render.")
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
        help="Directory to write debug images and hierarchy output to.",
    )
    parser.add_argument(
        "--debug-bboxes",
        action="store_true",
        help="Overlay computed segment content boxes on the rendered page images.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = qsplitter.load_paper_context(args.paper, args.pdf_dir, args.ocr_dir, args.marker_dir)
    hierarchy = qsplitter.build_hierarchical_structure(
        args.paper,
        args.pdf_dir,
        args.ocr_dir,
        args.marker_dir,
        context=context,
    )

    output_paper_dir = args.output_dir / args.paper
    output_paper_dir.mkdir(parents=True, exist_ok=True)
    write_reading_order_file(context["data"], output_paper_dir / "reading_order.txt")
    segmented_payload = None
    if args.debug_bboxes:
        segmented_payload = build_segmented_questions(
            paper_code=args.paper,
            hierarchy_payload=hierarchy,
            pdf_dir=args.pdf_dir,
            ocr_dir=args.ocr_dir,
            context=context,
        )
    write_debug_page_images(
        context,
        output_paper_dir,
        segmented_payload=segmented_payload,
        draw_segment_bboxes=args.debug_bboxes,
    )

    hierarchy_path = output_paper_dir / "hierarchy.json"
    with hierarchy_path.open("w") as handle:
        json.dump(hierarchy, handle, indent=2)

    print(f"Wrote debug artifacts for {args.paper} to {output_paper_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
