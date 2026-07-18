import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import fitz
from PIL import Image, ImageDraw, ImageFont


HEADER_HEIGHT = 24
SECTION_GAP = 8
TOP_PADDING = 16
BOTTOM_PADDING = 12
HIGHLIGHT_WIDTH = 3


def load_json(path: Path) -> Dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def render_pdf_page(pdf_document: Any, page_index: int, image_bbox: List[float], zoom: float) -> Image.Image:
    pdf_page = pdf_document.load_page(page_index)
    target_width = image_bbox[2] - image_bbox[0]
    target_height = image_bbox[3] - image_bbox[1]
    x_scale = (target_width / pdf_page.rect.width) * zoom
    y_scale = (target_height / pdf_page.rect.height) * zoom
    pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(x_scale, y_scale), alpha=False)
    return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)


def marker_name(text: str) -> str:
    safe = text.strip().replace("(", "").replace(")", "")
    safe = safe.replace("/", "_").replace(" ", "_")
    return safe or "marker"


def build_end_marker(page_index: int, y: float) -> Dict[str, Any]:
    return {"page_index": page_index, "y": y, "x": 0}


def crop_segment(
    page_images: List[Image.Image],
    image_bboxes: List[List[float]],
    start_marker: Dict[str, Any],
    end_marker: Dict[str, Any],
    label: str,
    zoom: float,
) -> Image.Image:
    font = ImageFont.load_default()
    chunks: List[Image.Image] = []
    for page_index in range(start_marker["page_index"], end_marker["page_index"] + 1):
        page_image = page_images[page_index]
        page_height = page_image.height
        start_y = TOP_PADDING if page_index == start_marker["page_index"] else 0
        end_y = page_height

        if page_index == start_marker["page_index"]:
            start_y = max(0, int((start_marker["y"] - TOP_PADDING) * zoom))
        if page_index == end_marker["page_index"]:
            if page_index == start_marker["page_index"]:
                end_y = max(
                    start_y + 1,
                    min(page_height, int((end_marker["y"] - 6) * zoom)),
                )
            else:
                end_y = max(1, min(page_height, int((end_marker["y"] - 6) * zoom)))

        if end_y <= start_y:
            end_y = min(page_height, start_y + int(120 * zoom))
        crop = page_image.crop((0, start_y, page_image.width, end_y))

        if page_index == start_marker["page_index"]:
            highlight = [
                int(start_marker["bbox"][0] * zoom),
                max(0, int((start_marker["bbox"][1] * zoom) - start_y)),
                int(start_marker["bbox"][2] * zoom),
                max(1, int((start_marker["bbox"][3] * zoom) - start_y)),
            ]
            draw = ImageDraw.Draw(crop)
            draw.rectangle(highlight, outline="red", width=HIGHLIGHT_WIDTH)

        chunks.append(crop)

    width = max(chunk.width for chunk in chunks)
    body_height = sum(chunk.height for chunk in chunks) + SECTION_GAP * (len(chunks) - 1)
    canvas = Image.new("RGB", (width, HEADER_HEIGHT + body_height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, HEADER_HEIGHT), fill="#f0f0f0")
    draw.text((8, 6), label, fill="black", font=font)

    cursor_y = HEADER_HEIGHT
    for idx, chunk in enumerate(chunks):
        canvas.paste(chunk, (0, cursor_y))
        cursor_y += chunk.height
        if idx + 1 < len(chunks):
            draw.line((0, cursor_y + SECTION_GAP // 2, width, cursor_y + SECTION_GAP // 2), fill="#999999", width=1)
            cursor_y += SECTION_GAP

    return canvas


def render_paper(
    paper_code: str,
    pdf_dir: Path,
    ocr_dir: Path,
    hierarchy_dir: Path,
    output_dir: Path,
    zoom: float,
) -> bool:
    pdf_path = pdf_dir / f"{paper_code}.pdf"
    ocr_path = ocr_dir / paper_code / "results.json"
    hierarchy_path = hierarchy_dir / paper_code / "hierarchy.json"
    if not pdf_path.exists() or not ocr_path.exists() or not hierarchy_path.exists():
        return False

    ocr_pages = load_json(ocr_path).get(paper_code, [])
    image_bboxes = [page["image_bbox"] for page in ocr_pages]
    hierarchy = load_json(hierarchy_path)
    paper_output_dir = output_dir / paper_code
    paper_output_dir.mkdir(parents=True, exist_ok=True)

    pdf_document = fitz.open(str(pdf_path))
    try:
        page_images = [
            render_pdf_page(pdf_document, page_index, image_bbox, zoom)
            for page_index, image_bbox in enumerate(image_bboxes)
        ]

        questions = hierarchy.get("questions", [])
        for q_index, question_entry in enumerate(questions):
            question_marker = question_entry["question"]
            if q_index + 1 < len(questions):
                question_end = questions[q_index + 1]["question"]
            else:
                last_page = len(image_bboxes) - 1
                question_end = build_end_marker(last_page, image_bboxes[last_page][3] + BOTTOM_PADDING)

            question_image = crop_segment(
                page_images,
                image_bboxes,
                question_marker,
                question_end,
                f"{paper_code} question {question_marker['text']}",
                zoom,
            )
            question_image.save(
                paper_output_dir / f"q_{q_index + 1:03d}_{marker_name(question_marker['text'])}.png"
            )

            primaries = question_entry.get("primary_subparts", [])
            for p_index, primary_entry in enumerate(primaries):
                primary_marker = primary_entry["primary"]
                if p_index + 1 < len(primaries):
                    primary_end = primaries[p_index + 1]["primary"]
                else:
                    primary_end = question_end
                primary_image = crop_segment(
                    page_images,
                    image_bboxes,
                    primary_marker,
                    primary_end,
                    f"{paper_code} question {question_marker['text']} primary {primary_marker['text']}",
                    zoom,
                )
                primary_image.save(
                    paper_output_dir
                    / f"q_{q_index + 1:03d}_p_{p_index + 1:02d}_{marker_name(primary_marker['text'])}.png"
                )

                secondaries = primary_entry.get("secondary_subparts", [])
                for s_index, secondary_entry in enumerate(secondaries):
                    secondary_marker = secondary_entry["secondary"]
                    if s_index + 1 < len(secondaries):
                        secondary_end = secondaries[s_index + 1]["secondary"]
                    else:
                        secondary_end = primary_end
                    secondary_image = crop_segment(
                        page_images,
                        image_bboxes,
                        secondary_marker,
                        secondary_end,
                        (
                            f"{paper_code} question {question_marker['text']} "
                            f"primary {primary_marker['text']} secondary {secondary_marker['text']}"
                        ),
                        zoom,
                    )
                    secondary_image.save(
                        paper_output_dir
                        / (
                            f"q_{q_index + 1:03d}_p_{p_index + 1:02d}_s_{s_index + 1:02d}_"
                            f"{marker_name(secondary_marker['text'])}.png"
                        )
                    )
    finally:
        pdf_document.close()
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render review screenshots from qsplitter hierarchy output."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--paper", help="Render one paper.")
    group.add_argument("--all", action="store_true", help="Render every paper with complete inputs.")
    parser.add_argument("--pdf-dir", type=Path, required=True, help="Directory containing PDF files.")
    parser.add_argument("--ocr-dir", type=Path, required=True, help="Directory containing OCR results (per-paper folders).")
    parser.add_argument("--hierarchy-dir", type=Path, required=True, help="Directory containing hierarchy.json files (per-paper folders).")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to write screenshot PNGs.")
    parser.add_argument("--zoom", type=float, default=2.0, help="Zoom level for rendering PDFs.")
    return parser.parse_args()


def iter_papers(hierarchy_dir: Path) -> Iterable[str]:
    """Iterate over all papers that have a hierarchy.json file."""
    for path in sorted(hierarchy_dir.iterdir()):
        if path.is_dir() and (path / "hierarchy.json").exists():
            yield path.name


def main() -> int:
    args = parse_args()
    paper_codes = [args.paper] if args.paper else list(iter_papers(args.hierarchy_dir))
    rendered = 0
    for paper_code in paper_codes:
        if render_paper(
            paper_code,
            args.pdf_dir,
            args.ocr_dir,
            args.hierarchy_dir,
            args.output_dir,
            args.zoom,
        ):
            rendered += 1
    print(f"Rendered screenshots for {rendered} papers into {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
