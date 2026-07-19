"""CLI entry point for the grading web app.

Usage:

    python -m src.pipeline.webapp \
        --records pseudocode_writing_hits/pseudocode_question_records.json \
        --port 8000
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .app import make_server
from ..grading.ast_adapter import find_parser_binary
from ..grading.openrouter_client import OpenRouterConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the pseudocode grading web app.")
    parser.add_argument(
        "--records",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_question_records.json"),
        help="Canonical pseudocode-question-record/v1 JSON from build_final_records.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--parse-timeout",
        type=float,
        default=10.0,
        help="Seconds allowed for one Rust parser invocation.",
    )
    parser.add_argument(
        "--qp-dir",
        type=Path,
        default=Path("qp_output"),
        help="Directory of per-paper segmented_questions.json (for layout reconstruction).",
    )
    parser.add_argument(
        "--marker-root",
        type=Path,
        default=Path("normalize/normalized_marker_output"),
        help="Directory of normalized Marker layout outputs (for figure/table regions).",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("resources/pdfs/cs_papers"),
        help="Directory of source question-paper PDFs (for figure crops).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.records.is_file():
        print(f"Records file not found: {args.records}")
        print("Generate it with: python -m src.pipeline.pseudocode_tools.build_final_records")
        return 2

    server = make_server(
        records_path=args.records,
        host=args.host,
        port=args.port,
        parse_timeout=args.parse_timeout,
        qp_dir=args.qp_dir,
        marker_root=args.marker_root,
        pdf_dir=args.pdf_dir,
    )

    config = OpenRouterConfig()
    grading_mode = (
        f"OpenRouter model {config.model}" if config.has_api_key
        else "DRY RUN (set OPENROUTER_API_KEY to grade with the real model)"
    )
    parser_binary = find_parser_binary()
    parser_state = str(parser_binary) if parser_binary else (
        "NOT BUILT — run: cargo build --release (in pseudocode-parser/)"
    )
    print(f"Records:  {args.records}", flush=True)
    print(f"Parser:   {parser_state}", flush=True)
    print(f"Grading:  {grading_mode}", flush=True)
    print(f"Serving:  http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
