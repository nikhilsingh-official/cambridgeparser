from typing import Any, Dict, List
import fitz
from .geometry import scale_pdf_bbox


def _span_is_bold(span: Dict[str, Any]) -> bool:
    font_name = (span.get("font") or "").lower()
    flags = span.get("flags") or 0
    try:
        flags = int(flags)
    except (TypeError, ValueError):
        flags = 0
    return "bold" in font_name or bool(flags & 16)


def build_text_lines_from_fitz(pdf_page: Any, image_bbox: List[float]) -> List[Dict[str, Any]]:
    raw = pdf_page.get_text("rawdict")
    text_lines = []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            chars = []
            for span in line.get("spans", []):
                is_bold = _span_is_bold(span)
                for char in span.get("chars", []):
                    char_text = char.get("c")
                    if char_text is None:
                        continue
                    bbox = scale_pdf_bbox(char["bbox"], pdf_page.rect, image_bbox)
                    chars.append({
                        "text": char_text,
                        "bbox": bbox,
                        "bbox_valid": True,
                        "is_bold": is_bold,
                        "font_name": span.get("font"),
                    })
            if not chars:
                continue
            line_bbox = scale_pdf_bbox(line["bbox"], pdf_page.rect, image_bbox)
            line_text = "".join(char["text"] for char in chars)
            text_lines.append({"text": line_text, "bbox": line_bbox, "chars": chars})
    return text_lines


def build_pages_from_fitz(pdf_path: str, image_bbox_by_page: List[List[float]], ocr_pages: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    pages = []
    pdf_document = fitz.open(pdf_path)
    try:
        for page_index, pdf_page in enumerate(pdf_document):
            image_bbox = image_bbox_by_page[page_index]
            text_lines = build_text_lines_from_fitz(pdf_page, image_bbox)
            if not text_lines and ocr_pages and page_index < len(ocr_pages):
                text_lines = ocr_pages[page_index].get("text_lines", [])
            pages.append({"text_lines": text_lines, "image_bbox": image_bbox})
    finally:
        pdf_document.close()
    return pages
