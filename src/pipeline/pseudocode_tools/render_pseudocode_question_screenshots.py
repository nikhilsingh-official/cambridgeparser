"""Render pseudocode-question screenshots directly from PDFs and stored bboxes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import fitz
from PIL import Image, ImageDraw, ImageFont


HEADER_HEIGHT = 24
SECTION_GAP = 8
HIGHLIGHT_WIDTH = 3
DEFAULT_PAGE_WIDTH = 794.0
DEFAULT_PAGE_HEIGHT = 1123.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render selected pseudocode-writing segments and parent question context "
            "from PDFs using content_pages/content_bbox already stored in the final JSON."
        )
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_writing_final_qp_ms_context.json"),
        help="Final pseudocode-writing JSON containing retained records.",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("resources/pdfs/cs_papers"),
        help="Directory containing question-paper PDFs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_question_screenshots"),
        help="Directory where screenshots will be written.",
    )
    parser.add_argument("--zoom", type=float, default=2.0, help="PDF render zoom.")
    parser.add_argument(
        "--keep-blank-pages",
        action="store_true",
        help="Keep visually blank full-page chunks in stitched screenshots.",
    )
    parser.add_argument(
        "--blank-pixel-threshold",
        type=int,
        default=245,
        help="Grayscale value above which a pixel is treated as blank paper.",
    )
    parser.add_argument(
        "--blank-nonwhite-ratio",
        type=float,
        default=0.003,
        help="Maximum non-white pixel ratio for a crop to be treated as blank.",
    )
    return parser.parse_args()


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _safe_marker(value: Any, prefix: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("(", "").replace(")", "")
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return f"{prefix}{text or 'unknown'}"


def _record_slug(record: Dict[str, Any]) -> str:
    parts = [_safe_marker(record.get("question_marker"), "q")]
    if record.get("primary_marker"):
        parts.append(_safe_marker(record.get("primary_marker"), "p"))
    if record.get("secondary_marker"):
        parts.append(_safe_marker(record.get("secondary_marker"), "s"))
    return "_".join(parts)


def _marker_pages(marker: Dict[str, Any]) -> List[Dict[str, Any]]:
    pages = marker.get("content_pages") or []
    if pages:
        return [
            {"page_index": page.get("page_index"), "bbox": page.get("bbox")}
            for page in pages
            if isinstance(page.get("page_index"), int)
            and isinstance(page.get("bbox"), list)
            and len(page["bbox"]) == 4
        ]

    page_index = marker.get("page_index")
    bbox = marker.get("content_bbox") or marker.get("bbox")
    if isinstance(page_index, int) and isinstance(bbox, list) and len(bbox) == 4:
        return [{"page_index": page_index, "bbox": bbox}]
    return []


def _iter_record_markers(record: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    selected = record.get("qp_selected_entry")
    if isinstance(selected, dict):
        yield selected
    context_question = (record.get("qp_context_question") or {}).get("question")
    if isinstance(context_question, dict):
        yield context_question


def _infer_paper_canvas(records: Iterable[Dict[str, Any]]) -> Dict[str, Tuple[float, float]]:
    canvas_by_paper: Dict[str, Tuple[float, float]] = {}
    for record in records:
        paper_code = record.get("paper_code")
        if not paper_code:
            continue
        current_width, current_height = canvas_by_paper.get(
            paper_code, (DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT)
        )
        for marker in _iter_record_markers(record):
            for page in _marker_pages(marker):
                bbox = page["bbox"]
                current_width = max(current_width, float(bbox[2]))
                current_height = max(current_height, float(bbox[3]))
        canvas_by_paper[paper_code] = (current_width, current_height)
    return canvas_by_paper


def _render_pdf_page(
    document: fitz.Document,
    page_index: int,
    canvas_size: Tuple[float, float],
    zoom: float,
) -> Image.Image:
    page = document.load_page(page_index)
    canvas_width, canvas_height = canvas_size
    x_scale = (canvas_width / page.rect.width) * zoom
    y_scale = (canvas_height / page.rect.height) * zoom
    pixmap = page.get_pixmap(matrix=fitz.Matrix(x_scale, y_scale), alpha=False)
    return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)


def _normalise_notice_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().upper()


def _page_has_centered_blank_notice(pdf_page: fitz.Page) -> bool:
    page_width = float(pdf_page.rect.width)
    page_center_x = page_width / 2.0
    center_tolerance = page_width * 0.2

    for block in pdf_page.get_text("blocks"):
        if len(block) < 5:
            continue
        text = _normalise_notice_text(str(block[4]))
        if text != "BLANK PAGE":
            continue
        x0, _, x1, _ = block[:4]
        block_center_x = (float(x0) + float(x1)) / 2.0
        if abs(block_center_x - page_center_x) <= center_tolerance:
            return True
    return False


def _scaled_bbox(bbox: List[float], zoom: float) -> Tuple[int, int, int, int]:
    return (
        int(float(bbox[0]) * zoom),
        int(float(bbox[1]) * zoom),
        int(float(bbox[2]) * zoom),
        int(float(bbox[3]) * zoom),
    )


def _clamp_bbox(
    bbox: Tuple[int, int, int, int],
    width: int,
    height: int,
) -> Optional[Tuple[int, int, int, int]]:
    x0, y0, x1, y1 = bbox
    x0 = max(0, min(x0, width))
    x1 = max(0, min(x1, width))
    y0 = max(0, min(y0, height))
    y1 = max(0, min(y1, height))
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def _draw_marker_highlight(
    crop: Image.Image,
    crop_bbox: Tuple[int, int, int, int],
    marker_bbox: Optional[List[float]],
    zoom: float,
) -> None:
    if not marker_bbox or len(marker_bbox) != 4:
        return
    marker = _scaled_bbox(marker_bbox, zoom)
    highlight = (
        marker[0] - crop_bbox[0],
        marker[1] - crop_bbox[1],
        marker[2] - crop_bbox[0],
        marker[3] - crop_bbox[1],
    )
    if highlight[2] <= 0 or highlight[3] <= 0 or highlight[0] >= crop.width or highlight[1] >= crop.height:
        return
    draw = ImageDraw.Draw(crop)
    draw.rectangle(highlight, outline="red", width=HIGHLIGHT_WIDTH)


def _is_blank_crop(
    crop: Image.Image,
    *,
    pixel_threshold: int,
    nonwhite_ratio: float,
) -> bool:
    grayscale = crop.convert("L")
    histogram = grayscale.histogram()
    dark_pixels = sum(histogram[: max(0, min(256, pixel_threshold))])
    total_pixels = grayscale.width * grayscale.height
    if total_pixels == 0:
        return True
    return (dark_pixels / total_pixels) <= nonwhite_ratio


def _stitch_chunks(chunks: List[Image.Image], label: str) -> Image.Image:
    font = ImageFont.load_default()
    width = max(chunk.width for chunk in chunks)
    body_height = sum(chunk.height for chunk in chunks) + SECTION_GAP * (len(chunks) - 1)
    canvas = Image.new("RGB", (width, HEADER_HEIGHT + body_height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, HEADER_HEIGHT), fill="#f0f0f0")
    draw.text((8, 6), label, fill="black", font=font)

    cursor_y = HEADER_HEIGHT
    for index, chunk in enumerate(chunks):
        canvas.paste(chunk, (0, cursor_y))
        cursor_y += chunk.height
        if index + 1 < len(chunks):
            separator_y = cursor_y + SECTION_GAP // 2
            draw.line((0, separator_y, width, separator_y), fill="#999999", width=1)
            cursor_y += SECTION_GAP
    return canvas


def _render_marker(
    document: fitz.Document,
    page_cache: Dict[int, Image.Image],
    blank_notice_cache: Dict[int, bool],
    marker: Dict[str, Any],
    label: str,
    output_path: Path,
    canvas_size: Tuple[float, float],
    zoom: float,
    skip_blank_pages: bool,
    blank_pixel_threshold: int,
    blank_nonwhite_ratio: float,
) -> Tuple[bool, int]:
    chunks: List[Image.Image] = []
    skipped_blank_pages = 0
    marker_page = marker.get("page_index")
    marker_bbox = marker.get("bbox")

    for page in _marker_pages(marker):
        page_index = page["page_index"]
        if page_index not in blank_notice_cache:
            blank_notice_cache[page_index] = _page_has_centered_blank_notice(
                document.load_page(page_index)
            )
        if skip_blank_pages and blank_notice_cache[page_index]:
            skipped_blank_pages += 1
            continue

        if page_index not in page_cache:
            page_cache[page_index] = _render_pdf_page(document, page_index, canvas_size, zoom)
        page_image = page_cache[page_index]
        crop_bbox = _clamp_bbox(_scaled_bbox(page["bbox"], zoom), page_image.width, page_image.height)
        if crop_bbox is None:
            continue
        crop = page_image.crop(crop_bbox)
        if (
            skip_blank_pages
            and page_index != marker_page
            and _is_blank_crop(
                crop,
                pixel_threshold=blank_pixel_threshold,
                nonwhite_ratio=blank_nonwhite_ratio,
            )
        ):
            skipped_blank_pages += 1
            continue
        if page_index == marker_page:
            _draw_marker_highlight(crop, crop_bbox, marker_bbox, zoom)
        chunks.append(crop)

    if not chunks:
        return False, skipped_blank_pages

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _stitch_chunks(chunks, label).save(output_path)
    return True, skipped_blank_pages


def render_screenshots(
    input_json: Path,
    pdf_dir: Path,
    output_dir: Path,
    zoom: float,
    *,
    skip_blank_pages: bool = True,
    blank_pixel_threshold: int = 245,
    blank_nonwhite_ratio: float = 0.003,
) -> Dict[str, int]:
    payload = _read_json(input_json)
    records = payload.get("records", [])
    canvas_by_paper = _infer_paper_canvas(records)

    pdf_cache: Dict[str, fitz.Document] = {}
    page_caches: Dict[str, Dict[int, Image.Image]] = {}
    blank_notice_caches: Dict[str, Dict[int, bool]] = {}
    rendered_selected = 0
    rendered_context = 0
    skipped_blank_pages = 0
    missing_pdfs: set[str] = set()

    try:
        for record in records:
            paper_code = record.get("paper_code")
            if not paper_code:
                continue

            pdf_path = pdf_dir / f"{paper_code}.pdf"
            if not pdf_path.exists():
                missing_pdfs.add(paper_code)
                continue

            if paper_code not in pdf_cache:
                pdf_cache[paper_code] = fitz.open(pdf_path)
                page_caches[paper_code] = {}
                blank_notice_caches[paper_code] = {}

            record_id = int(record.get("id") or 0)
            slug = _record_slug(record)
            paper_output = output_dir / paper_code
            selected_path = paper_output / f"{record_id:03d}_{slug}_selected.png"
            context_path = paper_output / f"{record_id:03d}_{slug}_question_context.png"
            selected_marker = record.get("qp_selected_entry") or {}
            context_marker = (record.get("qp_context_question") or {}).get("question") or {}
            canvas_size = canvas_by_paper.get(paper_code, (DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT))

            selected_exists, selected_skipped = _render_marker(
                pdf_cache[paper_code],
                page_caches[paper_code],
                blank_notice_caches[paper_code],
                selected_marker,
                f"{paper_code} {slug} selected",
                selected_path,
                canvas_size,
                zoom,
                skip_blank_pages,
                blank_pixel_threshold,
                blank_nonwhite_ratio,
            )
            context_exists, context_skipped = _render_marker(
                pdf_cache[paper_code],
                page_caches[paper_code],
                blank_notice_caches[paper_code],
                context_marker,
                f"{paper_code} {slug} question context",
                context_path,
                canvas_size,
                zoom,
                skip_blank_pages,
                blank_pixel_threshold,
                blank_nonwhite_ratio,
            )

            rendered_selected += int(selected_exists)
            rendered_context += int(context_exists)
            skipped_blank_pages += selected_skipped + context_skipped
            record["screenshots"] = {
                "selected_segment_path": str(selected_path),
                "selected_segment_exists": selected_exists,
                "question_context_path": str(context_path),
                "question_context_exists": context_exists,
                "source_root": str(output_dir),
                "renderer": "pdf_content_pages",
                "blank_pages_skipped": selected_skipped + context_skipped,
            }

    finally:
        for document in pdf_cache.values():
            document.close()

    summary = payload.setdefault("summary", {})
    summary["question_screenshot_records"] = len(records)
    summary["question_screenshots_selected_rendered"] = rendered_selected
    summary["question_screenshots_context_rendered"] = rendered_context
    summary["question_screenshot_output_dir"] = str(output_dir)
    summary["question_screenshot_missing_pdf_papers"] = sorted(missing_pdfs)
    summary["question_screenshot_blank_pages_skipped"] = skipped_blank_pages
    summary["question_screenshot_skip_blank_pages"] = skip_blank_pages
    summary["question_screenshot_blank_pixel_threshold"] = blank_pixel_threshold
    summary["question_screenshot_blank_nonwhite_ratio"] = blank_nonwhite_ratio
    _write_json(input_json, payload)

    return {
        "records": len(records),
        "selected": rendered_selected,
        "context": rendered_context,
        "blank_pages_skipped": skipped_blank_pages,
        "missing_pdfs": len(missing_pdfs),
    }


def main() -> int:
    args = parse_args()
    summary = render_screenshots(
        args.input_json,
        args.pdf_dir,
        args.output_dir,
        args.zoom,
        skip_blank_pages=not args.keep_blank_pages,
        blank_pixel_threshold=args.blank_pixel_threshold,
        blank_nonwhite_ratio=args.blank_nonwhite_ratio,
    )
    print(
        "Rendered "
        f"{summary['selected']} selected and {summary['context']} context screenshots "
        f"for {summary['records']} records into {args.output_dir}; "
        f"skipped {summary['blank_pages_skipped']} blank page chunks."
    )
    if summary["missing_pdfs"]:
        print(f"Missing PDFs for {summary['missing_pdfs']} papers.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
