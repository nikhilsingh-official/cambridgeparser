"""Export paper-2 questions where all subparts are pseudocode-writing prompts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict

import fitz

from src.pipeline.analysis.diagnostics.debug_renderer import render_pdf_page
from src.pipeline.parser import qsplitter
from src.resources.paths import (
    PSEUDOCODE_WRITING_DIR,
    PSEUDOCODE_WRITING_SELECTED_JSON,
    QP_OUTPUT_DIR,
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export paper-2 pseudocode-writing questions where all subparts are pseudocode."
    )
    parser.add_argument(
        "--selected-file",
        type=Path,
        default=PSEUDOCODE_WRITING_SELECTED_JSON,
        help="Path to pseudocode_writing_selected.json",
    )
    parser.add_argument(
        "--segments-dir",
        type=Path,
        default=QP_OUTPUT_DIR,
        help="Directory containing per-paper segmented_questions.json files.",
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
        default=PSEUDOCODE_WRITING_DIR / "paper2_full_questions",
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


def _selected_key(hit: Dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        hit.get("paper_code", ""),
        str(hit.get("question_marker", "")),
        str(hit.get("primary_marker") or ""),
        str(hit.get("secondary_marker") or ""),
        hit.get("segment_kind", ""),
    )


def _load_selected(selected_file: Path) -> set[tuple[str, str, str, str, str]]:
    selected = json.loads(selected_file.read_text())
    return {_selected_key(hit) for hit in selected if _paper2(hit.get("paper_code", ""))}


def _segment_key(
    paper_code: str,
    question_marker: str,
    segment_kind: str,
    primary_marker: str | None = None,
    secondary_marker: str | None = None,
) -> tuple[str, str, str, str, str]:
    return (
        paper_code,
        str(question_marker),
        str(primary_marker or ""),
        str(secondary_marker or ""),
        segment_kind,
    )


def _question_is_full(
    paper_code: str,
    question: Dict[str, Any],
    selected_keys: set[tuple[str, str, str, str, str]],
) -> bool:
    q_marker = question["question"]["text"]
    primaries = question.get("primary_subparts", [])
    if not primaries:
        return _segment_key(paper_code, q_marker, "question") in selected_keys

    for primary in primaries:
        p_marker = primary["primary"]["text"]
        if _segment_key(paper_code, q_marker, "primary", p_marker) not in selected_keys:
            return False
        for secondary in primary.get("secondary_subparts", []):
            s_marker = secondary["secondary"]["text"]
            if (
                _segment_key(paper_code, q_marker, "secondary", p_marker, s_marker)
                not in selected_keys
            ):
                return False
    return True


def export_full_questions(
    selected_file: Path,
    segments_dir: Path,
    pdf_dir: Path,
    ocr_dir: Path,
    marker_dir: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    selected_keys = _load_selected(selected_file)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "paper2_full_questions": 0,
        "papers": {},
        "output_dir": str(output_dir),
    }

    for segmented_path in sorted(segments_dir.rglob("segmented_questions.json")):
        paper_code = segmented_path.parent.name
        if not _paper2(paper_code):
            continue

        payload = json.loads(segmented_path.read_text())
        questions = payload.get("questions", [])
        full_questions = [
            q for q in questions if _question_is_full(paper_code, q, selected_keys)
        ]
        if not full_questions:
            continue

        context = qsplitter.load_paper_context(paper_code, pdf_dir, ocr_dir, marker_dir)
        pdf_document = fitz.open(context["pdf_path"])
        page_cache = {}

        paper_out = output_dir / paper_code
        paper_out.mkdir(parents=True, exist_ok=True)

        exported = []
        for q_idx, question in enumerate(full_questions, 1):
            q_marker = question["question"]
            q_marker_text = q_marker.get("text", "?")
            primaries = question.get("primary_subparts", [])

            if not primaries:
                pages = q_marker.get("content_pages") or [
                    {
                        "page_index": q_marker["page_index"],
                        "bbox": q_marker.get("content_bbox", q_marker.get("bbox")),
                    }
                ]
                for slice_idx, page in enumerate(pages, 1):
                    page_index = page["page_index"]
                    bbox = page["bbox"]
                    if page_index not in page_cache:
                        image_bbox = context["data"][page_index]["image_bbox"]
                        page_cache[page_index] = render_pdf_page(pdf_document, page_index, image_bbox)
                    page_image = page_cache[page_index]
                    clamp = _clamp_bbox(bbox, page_image.width, page_image.height)
                    if not clamp:
                        continue
                    crop = page_image.crop(clamp)
                    image_name = f"{q_idx:03d}_question_q{_safe_text(q_marker_text)}_p{page_index+1:03d}.png"
                    image_path = paper_out / image_name
                    crop.save(image_path)
                    exported.append(
                        {
                            "paper_code": paper_code,
                            "question_marker": q_marker_text,
                            "segment_kind": "question",
                            "content_text": q_marker.get("content_text", ""),
                            "content_bbox": bbox,
                            "page_index": page_index,
                            "slice_index": slice_idx,
                            "slice_count": len(pages),
                            "image_path": str(image_path),
                        }
                    )
                continue

            for p_idx, primary in enumerate(primaries, 1):
                p_marker = primary["primary"]
                p_marker_text = p_marker.get("text", "?")
                pages = list(
                    p_marker.get("content_pages")
                    or [
                        {
                            "page_index": p_marker["page_index"],
                            "bbox": p_marker.get("content_bbox", p_marker.get("bbox")),
                        }
                    ]
                )

                if p_idx == 1 and pages and pages[0]["page_index"] == q_marker["page_index"]:
                    q_bbox = q_marker.get("bbox", [0, 0, 0, 0])
                    p_bbox = pages[0]["bbox"]
                    pages[0] = {
                        **pages[0],
                        "bbox": [
                            min(q_bbox[0], p_bbox[0]),
                            min(q_bbox[1], p_bbox[1]),
                            max(p_bbox[2], q_bbox[2]),
                            p_bbox[3],
                        ],
                    }
                    context_text = f"{q_marker.get('content_text','')}\n{p_marker.get('content_text','')}"
                else:
                    context_text = p_marker.get("content_text", "")

                for slice_idx, page in enumerate(pages, 1):
                    page_index = page["page_index"]
                    bbox = page["bbox"]
                    if page_index not in page_cache:
                        image_bbox = context["data"][page_index]["image_bbox"]
                        page_cache[page_index] = render_pdf_page(pdf_document, page_index, image_bbox)
                    page_image = page_cache[page_index]
                    clamp = _clamp_bbox(bbox, page_image.width, page_image.height)
                    if not clamp:
                        continue
                    crop = page_image.crop(clamp)
                    image_name = (
                        f"{q_idx:03d}_primary_{p_idx:02d}_"
                        f"q{_safe_text(q_marker_text)}_p{_safe_text(p_marker_text)}_p{page_index+1:03d}.png"
                    )
                    image_path = paper_out / image_name
                    crop.save(image_path)
                    exported.append(
                        {
                            "paper_code": paper_code,
                            "question_marker": q_marker_text,
                            "primary_marker": p_marker_text,
                            "segment_kind": "primary",
                            "content_text": p_marker.get("content_text", ""),
                            "context_text": context_text,
                            "content_bbox": bbox,
                            "page_index": page_index,
                            "slice_index": slice_idx,
                            "slice_count": len(pages),
                            "image_path": str(image_path),
                        }
                    )

                for s_idx, secondary in enumerate(primary.get("secondary_subparts", []), 1):
                    s_marker = secondary["secondary"]
                    s_marker_text = s_marker.get("text", "?")
                    pages = s_marker.get("content_pages") or [
                        {
                            "page_index": s_marker["page_index"],
                            "bbox": s_marker.get("content_bbox", s_marker.get("bbox")),
                        }
                    ]
                    for slice_idx, page in enumerate(pages, 1):
                        page_index = page["page_index"]
                        bbox = page["bbox"]
                        if page_index not in page_cache:
                            image_bbox = context["data"][page_index]["image_bbox"]
                            page_cache[page_index] = render_pdf_page(pdf_document, page_index, image_bbox)
                        page_image = page_cache[page_index]
                        clamp_s = _clamp_bbox(bbox, page_image.width, page_image.height)
                        if not clamp_s:
                            continue
                        crop = page_image.crop(clamp_s)
                        image_name = (
                            f"{q_idx:03d}_secondary_{p_idx:02d}_{s_idx:02d}_"
                            f"q{_safe_text(q_marker_text)}_p{_safe_text(p_marker_text)}_s{_safe_text(s_marker_text)}_p{page_index+1:03d}.png"
                        )
                        image_path = paper_out / image_name
                        crop.save(image_path)
                        exported.append(
                            {
                                "paper_code": paper_code,
                                "question_marker": q_marker_text,
                                "primary_marker": p_marker_text,
                                "secondary_marker": s_marker_text,
                                "segment_kind": "secondary",
                                "content_text": s_marker.get("content_text", ""),
                                "content_bbox": bbox,
                                "page_index": page_index,
                                "slice_index": slice_idx,
                                "slice_count": len(pages),
                                "image_path": str(image_path),
                            }
                        )

        pdf_document.close()

        _write_json(paper_out / "hits.json", exported)
        summary["papers"][paper_code] = {
            "full_questions": len(full_questions),
            "segments_exported": len(exported),
            "hits_file": str(paper_out / "hits.json"),
        }
        summary["paper2_full_questions"] += len(full_questions)

    _write_json(output_dir / "paper2_full_questions_summary.json", summary)
    return summary


def main() -> int:
    args = parse_args()
    summary = export_full_questions(
        selected_file=args.selected_file,
        segments_dir=args.segments_dir,
        pdf_dir=args.pdf_dir,
        ocr_dir=args.ocr_dir,
        marker_dir=args.marker_dir,
        output_dir=args.output_dir,
    )
    print(
        f"Exported {summary['paper2_full_questions']} full paper-2 questions into {summary['output_dir']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
