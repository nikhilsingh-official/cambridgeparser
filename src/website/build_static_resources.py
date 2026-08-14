"""Build static JSON resources consumed by the Vue website."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from src.resources.paths import (
    NORMALIZED_MARKER_OUTPUT_DIR,
    PSEUDOCODE_QUESTION_RECORDS_JSON,
    QP_OUTPUT_DIR,
    SOURCE_PDF_DIR,
)
from src.resources.question_segments import find_qp_question
from src.website.marker_regions import MarkerRegionStore
from src.website.question_images import PdfCache, render_available, save_layout_image
from src.website.question_layout import build_question_layout, find_segment_node


DEFAULT_RECORDS = PSEUDOCODE_QUESTION_RECORDS_JSON
DEFAULT_QP_DIR = QP_OUTPUT_DIR
DEFAULT_MARKER_ROOT = NORMALIZED_MARKER_OUTPUT_DIR
DEFAULT_PDF_DIR = SOURCE_PDF_DIR
DEFAULT_PUBLIC_DIR = Path("src/website/frontend/public/resources")


def _prune_stale_layout_images(images_dir: Path, referenced: set[str]) -> None:
    """Remove generated question images no longer present in the record set."""

    if not images_dir.is_dir():
        return
    for pattern in ("q_*.png", "ctx_*.png"):
        for path in images_dir.glob(pattern):
            if path.name not in referenced:
                path.unlink()


def public_records_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Strip answers and grading rubrics from browser-readable records."""
    public_records = []
    for record in payload.get("records") or []:
        public_record = dict(record)
        mark_scheme = record.get("mark_scheme") or {}
        public_record["mark_scheme"] = {
            key: mark_scheme[key]
            for key in ("marks_value", "max_marks")
            if key in mark_scheme
        }
        public_record["marking_point_count"] = len(mark_scheme.get("marking_points") or [])
        public_record.pop("selection", None)
        public_record.pop("provenance", None)
        public_record.pop("diagnostics", None)
        public_records.append(public_record)
    return {
        "schema_version": (
            payload.get("schema_version")
            or (payload.get("summary") or {}).get("schema_version")
        ),
        "record_count": len(public_records),
        "records": public_records,
    }


def build_layouts(
    records: list[Dict[str, Any]],
    qp_dir: Path,
    marker_root: Path,
    pdf_dir: Path,
    images_dir: Path,
) -> Dict[str, Any]:
    marker_store = MarkerRegionStore(marker_root)
    pdf_cache = PdfCache(pdf_dir)
    qp_cache: Dict[str, Dict[str, Any] | None] = {}
    layouts: Dict[str, Dict[str, Any]] = {}
    referenced_images: set[str] = set()
    image_count = 0

    for record in records:
        record_id = record.get("id")
        paper_code = record.get("paper_code") or ""
        if record_id is None or not paper_code:
            continue

        if paper_code not in qp_cache:
            path = qp_dir / paper_code / "segmented_questions.json"
            qp_cache[paper_code] = json.loads(path.read_text()) if path.is_file() else None

        qp_payload = qp_cache[paper_code]
        segment_key = record.get("segment_key") or {}
        node = (
            find_segment_node(qp_payload, segment_key)
            if qp_payload is not None
            else None
        )
        if node is None:
            continue

        figures = marker_store.figures_by_page(paper_code)
        code = marker_store.code_by_page(paper_code)
        question_layout = build_question_layout(node, figures, code)

        # Context = the *whole* question (all subparts), reconstructed with the
        # same positioned-token builder so the "Show context" panel looks like
        # the real paper instead of a dumped text blob. Skipped when the answer
        # already is the whole question (the subpart node is the question node),
        # since that would just duplicate the question panel.
        context_layout = None
        if (segment_key.get("segment_kind") or "question") != "question":
            question_entry = find_qp_question(qp_payload, segment_key.get("question_marker"))
            context_node = (question_entry or {}).get("question")
            if context_node:
                context_layout = build_question_layout(context_node, figures, code)

        # Render the trusted "image" views straight from the PDF (skipped
        # gracefully when PyMuPDF/Pillow or the PDF is unavailable).
        doc = pdf_cache.get(paper_code)
        image = save_layout_image(doc, question_layout, images_dir, f"q_{record_id}.png")
        context_image = (
            save_layout_image(doc, context_layout, images_dir, f"ctx_{record_id}.png")
            if context_layout
            else None
        )
        image_count += (1 if image else 0) + (1 if context_image else 0)
        for descriptor in (image, context_image):
            if descriptor:
                referenced_images.add(Path(descriptor["src"]).name)

        layouts[str(record_id)] = {
            "question": question_layout,
            "context": context_layout,
            "image": image,
            "context_image": context_image,
        }

    _prune_stale_layout_images(images_dir, referenced_images)

    return {
        "schema_version": "static-question-layouts/v1",
        "record_count": len(records),
        "layout_count": len(layouts),
        "image_count": image_count,
        "images_rendered": render_available(),
        "layouts": layouts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build static website JSON resources.")
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--qp-dir", type=Path, default=DEFAULT_QP_DIR)
    parser.add_argument("--marker-root", type=Path, default=DEFAULT_MARKER_ROOT)
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--public-dir", type=Path, default=DEFAULT_PUBLIC_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.records.read_text())
    records = payload.get("records") or []

    args.public_dir.mkdir(parents=True, exist_ok=True)
    (args.public_dir / "pseudocode_question_records.json").write_text(
        json.dumps(public_records_payload(payload), separators=(",", ":"))
    )
    layouts = build_layouts(
        records, args.qp_dir, args.marker_root, args.pdf_dir, args.public_dir / "images"
    )
    (args.public_dir / "question_layouts.json").write_text(
        json.dumps(layouts, separators=(",", ":"))
    )
    print(
        f"Wrote {len(records)} records, {layouts['layout_count']} layouts, "
        f"and {layouts['image_count']} images to {args.public_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
