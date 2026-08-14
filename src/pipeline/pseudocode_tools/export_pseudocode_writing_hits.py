"""Export paper-2 pseudocode-writing hits with cropped images and segmented text."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict

import fitz

from src.pipeline.analysis.diagnostics.debug_renderer import render_pdf_page
from src.pipeline.parser import qsplitter
from src.resources.paths import PSEUDOCODE_WRITING_DIR, PSEUDOCODE_WRITING_SELECTED_JSON


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export pseudocode-writing hits for paper 2 only, with images and text."
    )
    parser.add_argument(
        "--selected-file",
        type=Path,
        default=PSEUDOCODE_WRITING_SELECTED_JSON,
        help="Path to pseudocode_writing_selected.json",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        required=True,
        help="Directory containing PDFs.",
    )
    parser.add_argument(
        "--ocr-dir",
        type=Path,
        required=True,
        help="Directory containing OCR outputs.",
    )
    parser.add_argument(
        "--marker-dir",
        type=Path,
        required=True,
        help="Directory containing normalized marker outputs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PSEUDOCODE_WRITING_DIR / "paper2_hits",
        help="Directory to write images and hit metadata.",
    )
    return parser.parse_args()


def _paper2(code: str) -> bool:
    return bool(re.search(r"_qp_2", code))


def _safe_text(value: Any) -> str:
    text = (value or "").strip()
    return re.sub(r"[^\w\-]+", "_", text)[:50] or "unknown"


def _clamp_bbox(bbox, width: int, height: int):
    x0, y0, x1, y1 = bbox
    x0 = max(0, min(int(x0), width))
    x1 = max(0, min(int(x1), width))
    y0 = max(0, min(int(y0), height))
    y1 = max(0, min(int(y1), height))
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def export_hits(
    selected_file: Path,
    pdf_dir: Path,
    ocr_dir: Path,
    marker_dir: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    selected = json.loads(selected_file.read_text())
    paper2_hits = [hit for hit in selected if _paper2(hit.get("paper_code", ""))]

    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "selected_total": len(selected),
        "paper2_hits": len(paper2_hits),
        "output_dir": str(output_dir),
        "papers": {},
    }

    paper_groups: Dict[str, list[dict]] = {}
    for hit in paper2_hits:
        paper_groups.setdefault(hit["paper_code"], []).append(hit)

    for paper_code, hits in sorted(paper_groups.items()):
        context = qsplitter.load_paper_context(paper_code, pdf_dir, ocr_dir, marker_dir)
        pdf_document = fitz.open(context["pdf_path"])
        page_cache = {}

        paper_out = output_dir / paper_code
        paper_out.mkdir(parents=True, exist_ok=True)

        exported_hits = []
        for idx, hit in enumerate(hits, 1):
            page_index = hit.get("page_index")
            bbox = hit.get("content_bbox")
            if page_index is None or not bbox:
                continue

            if page_index not in page_cache:
                image_bbox = context["data"][page_index]["image_bbox"]
                page_cache[page_index] = render_pdf_page(pdf_document, page_index, image_bbox)

            page_image = page_cache[page_index]
            clamp = _clamp_bbox(bbox, page_image.width, page_image.height)
            if not clamp:
                continue

            crop = page_image.crop(clamp)
            q_marker = _safe_text(hit.get("question_marker"))
            p_marker = _safe_text(hit.get("primary_marker"))
            s_marker = _safe_text(hit.get("secondary_marker"))
            kind = _safe_text(hit.get("segment_kind"))
            image_name = f"{idx:03d}_{kind}_q{q_marker}_p{p_marker}_s{s_marker}.png"
            image_path = paper_out / image_name
            crop.save(image_path)

            exported = {**hit, "image_path": str(image_path)}
            exported_hits.append(exported)

        pdf_document.close()

        _write_json(paper_out / "hits.json", exported_hits)
        summary["papers"][paper_code] = {
            "hits": len(exported_hits),
            "hits_file": str(paper_out / "hits.json"),
        }

    _write_json(output_dir / "paper2_hits_summary.json", summary)
    return summary


def main() -> int:
    args = parse_args()
    summary = export_hits(
        selected_file=args.selected_file,
        pdf_dir=args.pdf_dir,
        ocr_dir=args.ocr_dir,
        marker_dir=args.marker_dir,
        output_dir=args.output_dir,
    )
    print(
        f"Exported {summary['paper2_hits']} paper-2 hits into {summary['output_dir']} "
        f"across {len(summary['papers'])} papers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
