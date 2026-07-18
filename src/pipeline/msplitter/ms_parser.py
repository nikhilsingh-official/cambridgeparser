from __future__ import annotations

import argparse
import html as html_lib
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import fitz

from .io import load_json, write_json

QUESTION_CELL = "question"
ANSWER_CELL = "answer"
MARKS_CELL = "marks"
SECONDARY_ROMAN_PATTERN = r"(?:i|ii|iii|iv|v|vi|vii|viii|ix|x)"

def _render_table_debug_image(
    pdf_path: Path,
    page_index: int,
    table: Dict[str, Any],
    cells_by_column: Dict[str, List[Dict[str, Any]]],
    row_boundaries: List[Dict[str, Any]],
    marker_page_bbox: Optional[List[float]],
    output_path: Path,
) -> None:
    """Render a debug image showing table cells, columns, and rows.
    
    Transforms coordinates from marker space to PDF/image space using page boundaries.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print(f"Warning: PIL not available, skipping debug image for {output_path}", file=sys.stderr)
        return
    
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    
    # Get PDF page dimensions and marker space dimensions
    pdf_page_rect = page.rect
    pdf_page_bbox = [pdf_page_rect.x0, pdf_page_rect.y0, pdf_page_rect.x1, pdf_page_rect.y1]
    
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    doc.close()
    
    # Image scale factor (we're rendering at 2x scale)
    image_scale = 2.0
    image_bbox = [
        0,
        0,
        pix.width,
        pix.height,
    ]
    
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    draw = ImageDraw.Draw(img, "RGBA")
    
    def transform_bbox_to_image(marker_bbox: List[float]) -> tuple:
        """Transform marker space coordinates to image space."""
        if not marker_page_bbox:
            # Fallback: assume 1:1 scaling
            x0 = int(marker_bbox[0] * image_scale)
            y0 = int(marker_bbox[1] * image_scale)
            x1 = int(marker_bbox[2] * image_scale)
            y1 = int(marker_bbox[3] * image_scale)
        else:
            # Transform from marker space to PDF space, then to image space
            marker_width = float(marker_page_bbox[2]) - float(marker_page_bbox[0])
            marker_height = float(marker_page_bbox[3]) - float(marker_page_bbox[1])
            pdf_width = float(pdf_page_bbox[2]) - float(pdf_page_bbox[0])
            pdf_height = float(pdf_page_bbox[3]) - float(pdf_page_bbox[1])
            
            if marker_width > 0 and marker_height > 0:
                x_scale = pdf_width / marker_width
                y_scale = pdf_height / marker_height
                
                pdf_x0 = float(pdf_page_bbox[0]) + (float(marker_bbox[0]) - float(marker_page_bbox[0])) * x_scale
                pdf_y0 = float(pdf_page_bbox[1]) + (float(marker_bbox[1]) - float(marker_page_bbox[1])) * y_scale
                pdf_x1 = float(pdf_page_bbox[0]) + (float(marker_bbox[2]) - float(marker_page_bbox[0])) * x_scale
                pdf_y1 = float(pdf_page_bbox[1]) + (float(marker_bbox[3]) - float(marker_page_bbox[1])) * y_scale
            else:
                pdf_x0, pdf_y0, pdf_x1, pdf_y1 = marker_bbox
            
            # Convert PDF coords to image coords (with 2x scale)
            x0 = int(pdf_x0 * image_scale)
            y0 = int(pdf_y0 * image_scale)
            x1 = int(pdf_x1 * image_scale)
            y1 = int(pdf_y1 * image_scale)
        
        return (x0, y0, x1, y1)
    
    # Draw row boundaries (orange horizontal lines)
    for row in row_boundaries:
        y1_img, y2_img = transform_bbox_to_image([0, row["y1"], 100, row["y2"]])[1], transform_bbox_to_image([0, row["y1"], 100, row["y2"]])[3]
        table_x0, table_x1 = transform_bbox_to_image([table["bbox"][0], 0, table["bbox"][2], 100])[0], transform_bbox_to_image([table["bbox"][0], 0, table["bbox"][2], 100])[2]
        # Top of row
        draw.line([(table_x0, y1_img), (table_x1, y1_img)], fill=(255, 165, 0, 200), width=3)
        # Bottom of row
        draw.line([(table_x0, y2_img), (table_x1, y2_img)], fill=(255, 165, 0, 200), width=2)
    
    # Draw question cells (blue)
    for cell in cells_by_column.get("question", []):
        x0, y0, x1, y1 = transform_bbox_to_image(cell["bbox"])
        draw.rectangle([x0, y0, x1, y1], outline=(0, 0, 255, 255), width=2)
        draw.text((x0 + 5, y0 + 5), "Q", fill=(0, 0, 255, 255))
    
    # Draw answer cells (green)
    for cell in cells_by_column.get("answer", []):
        x0, y0, x1, y1 = transform_bbox_to_image(cell["bbox"])
        draw.rectangle([x0, y0, x1, y1], outline=(0, 255, 0, 255), width=2)
        draw.text((x0 + 5, y0 + 5), "A", fill=(0, 255, 0, 255))
    
    # Draw marks cells (red)
    for cell in cells_by_column.get("marks", []):
        x0, y0, x1, y1 = transform_bbox_to_image(cell["bbox"])
        draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0, 255), width=2)
        draw.text((x0 + 5, y0 + 5), "M", fill=(255, 0, 0, 255))
    
    # Draw table boundary (black)
    x0, y0, x1, y1 = transform_bbox_to_image(table["bbox"])
    draw.rectangle([x0, y0, x1, y1], outline=(0, 0, 0, 255), width=4)
    
    img.save(output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse mark scheme table rows into hierarchical JSON."
    )
    parser.add_argument("--paper", help="Single mark scheme paper code (e.g. 9608_w17_ms_21).")
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("resources/pdfs/cs_papers"),
        help="Directory containing mark scheme PDFs.",
    )
    parser.add_argument(
        "--marker-dir",
        type=Path,
        default=Path("resources/ocr/normalized_marker_output"),
        help="Directory containing normalized marker output.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/mark_scheme_segments"),
        help="Directory where parsed mark scheme outputs are written.",
    )
    parser.add_argument(
        "--debug-tables",
        action="store_true",
        help="Render debug images showing table cells, columns, and rows.",
    )
    return parser.parse_args()


def paper_year_from_code(paper_code: str) -> Optional[int]:
    match = re.search(r"_[sw](\d{2})_", paper_code)
    if not match:
        return None
    return 2000 + int(match.group(1))


def _strip_html_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", value)
    text = re.sub(r"(?i)</(p|div|tr|li|h\d)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text).replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    compact = "\n".join(line for line in lines if line)
    return compact.strip()


def _bbox_center_y(bbox: List[float]) -> float:
    return (float(bbox[1]) + float(bbox[3])) / 2.0


def _bbox_center_x(bbox: List[float]) -> float:
    return (float(bbox[0]) + float(bbox[2])) / 2.0


def _combine_bboxes(bboxes: Iterable[List[float]]) -> Optional[List[float]]:
    bboxes_list = [bbox for bbox in bboxes if bbox and len(bbox) == 4]
    if not bboxes_list:
        return None
    return [
        min(float(bbox[0]) for bbox in bboxes_list),
        min(float(bbox[1]) for bbox in bboxes_list),
        max(float(bbox[2]) for bbox in bboxes_list),
        max(float(bbox[3]) for bbox in bboxes_list),
    ]


def _bbox_intersection_width(left: List[float], right: List[float]) -> float:
    return max(0.0, min(float(left[2]), float(right[2])) - max(float(left[0]), float(right[0])))


def _cluster_rows(cells: List[Dict[str, Any]], tolerance: float = 6.0) -> List[List[Dict[str, Any]]]:
    ordered = sorted(cells, key=lambda cell: _bbox_center_y(cell["bbox"]))
    rows: List[List[Dict[str, Any]]] = []
    row_centers: List[float] = []

    for cell in ordered:
        center = _bbox_center_y(cell["bbox"])
        if not rows:
            rows.append([cell])
            row_centers.append(center)
            continue

        if abs(center - row_centers[-1]) <= tolerance:
            rows[-1].append(cell)
            row_centers[-1] = sum(_bbox_center_y(item["bbox"]) for item in rows[-1]) / len(rows[-1])
        else:
            rows.append([cell])
            row_centers.append(center)

    for row in rows:
        row.sort(key=lambda cell: _bbox_center_x(cell["bbox"]))

    return rows


def _find_header_row_index(rows: List[List[Dict[str, Any]]]) -> int:
    best_idx = -1
    best_score = -1
    for idx, row in enumerate(rows[: min(4, len(rows))]):
        cell_texts = [_strip_html_text(cell.get("html")).lower() for cell in row]
        score = 0
        # Check if the row contains header keywords (can be individual cells or partial text)
        has_question = any("question" in text for text in cell_texts)
        has_answer = any("answer" in text for text in cell_texts)
        has_marks = any("marks" in text for text in cell_texts)
        
        # A header row should have at least 2 of the 3 keywords
        if has_question:
            score += 1
        if has_answer:
            score += 1
        if has_marks:
            score += 1
        
        if score > best_score:
            best_score = score
            best_idx = idx
    return best_idx if best_score >= 2 else -1


def _infer_column_bboxes(header_row: List[Dict[str, Any]], table_bbox: Optional[List[float]]) -> Dict[str, List[float]]:
    q_cell = None
    a_cell = None
    m_cell = None
    for cell in header_row:
        cell_text = _strip_html_text(cell.get("html")).lower()
        if cell_text == "question":
            q_cell = cell
        elif cell_text == "answer":
            a_cell = cell
        elif cell_text == "marks":
            m_cell = cell

    if q_cell and m_cell:
        y0 = float(table_bbox[1]) if table_bbox and len(table_bbox) == 4 else min(
            float(cell["bbox"][1]) for cell in header_row
        )
        y1 = float(table_bbox[3]) if table_bbox and len(table_bbox) == 4 else max(
            float(cell["bbox"][3]) for cell in header_row
        )
        q_bbox = [
            float(q_cell["bbox"][0]),
            y0,
            float(q_cell["bbox"][2]),
            y1,
        ]
        answer_left = float(q_cell["bbox"][2])
        answer_right = float(m_cell["bbox"][0])
        if a_cell and answer_right <= answer_left:
            answer_left = float(a_cell["bbox"][0])
            answer_right = float(a_cell["bbox"][2])
        a_bbox = [answer_left, y0, answer_right, y1]
        m_bbox = [
            float(m_cell["bbox"][0]),
            y0,
            float(m_cell["bbox"][2]),
            y1,
        ]
        return {
            QUESTION_CELL: q_bbox,
            ANSWER_CELL: a_bbox,
            MARKS_CELL: m_bbox,
        }

    ordered = sorted(header_row, key=lambda cell: _bbox_center_x(cell["bbox"]))
    if len(ordered) >= 3:
        return {
            QUESTION_CELL: ordered[0]["bbox"],
            ANSWER_CELL: ordered[len(ordered) // 2]["bbox"],
            MARKS_CELL: ordered[-1]["bbox"],
        }

    if table_bbox and len(table_bbox) == 4:
        x0, y0, x1, y1 = [float(v) for v in table_bbox]
        width = x1 - x0
        q_bbox = [x0, y0, x0 + width * 0.22, y1]
        a_bbox = [x0 + width * 0.22, y0, x0 + width * 0.78, y1]
        m_bbox = [x0 + width * 0.78, y0, x1, y1]
        return {QUESTION_CELL: q_bbox, ANSWER_CELL: a_bbox, MARKS_CELL: m_bbox}

    return {
        QUESTION_CELL: [0.0, 0.0, 0.0, 0.0],
        ANSWER_CELL: [0.0, 0.0, 0.0, 0.0],
        MARKS_CELL: [0.0, 0.0, 0.0, 0.0],
    }


def _assign_column(cell_bbox: List[float], col_bboxes: Dict[str, List[float]]) -> str:
    best_label = QUESTION_CELL
    best_overlap = -1.0
    for label, bbox in col_bboxes.items():
        overlap = _bbox_intersection_width(cell_bbox, bbox)
        if overlap > best_overlap:
            best_overlap = overlap
            best_label = label
    return best_label


def _fitz_table_to_cells(fitz_table, page: fitz.Page) -> List[Dict[str, Any]]:
    """Convert a fitz Table to cell dictionaries with bbox and html text.
    
    Args:
        fitz_table: fitz.Table object from page.find_tables()
        page: fitz.Page object for text extraction
    
    Returns:
        List of cell dicts with keys: bbox (list [x0,y0,x1,y1]), html (string)
    """
    cells = []
    for row in fitz_table.rows:
        for cell_bbox in row.cells:
            if cell_bbox:  # Skip None cells (merged cells)
                # Extract text from cell
                text = page.get_text(clip=cell_bbox).strip()
                # Convert Rect/tuple to list bbox
                bbox = [cell_bbox[0], cell_bbox[1], cell_bbox[2], cell_bbox[3]] if isinstance(cell_bbox, (tuple, list)) else [
                    cell_bbox.x0, cell_bbox.y0, cell_bbox.x1, cell_bbox.y1
                ]
                cells.append({
                    "bbox": bbox,
                    "html": text,  # For consistency with Marker format
                    "id": None
                })
    return cells


def _extract_table_rows(table: Dict[str, Any], page_index: int, table_index: int, fitz_page: Optional[fitz.Page] = None) -> List[Dict[str, Any]]:
    # Support both Marker format (dict with children) and fitz format (fitz.Table)
    if fitz_page is not None and hasattr(table, 'rows'):
        # This is a fitz.Table object
        cells = _fitz_table_to_cells(table, fitz_page)
        table_bbox = [table.bbox[0], table.bbox[1], table.bbox[2], table.bbox[3]] if hasattr(table, 'bbox') else None
    else:
        # This is a Marker dict with children
        cells = [
            {"bbox": cell.get("bbox"), "html": cell.get("html"), "id": cell.get("id")}
            for cell in (table.get("children") or [])
            if cell.get("block_type") == "TableCell" and cell.get("bbox")
        ]
        table_bbox = table.get("bbox") if isinstance(table, dict) else None
    
    if not cells:
        return []

    rows = _cluster_rows(cells)
    if not rows:
        return []

    header_idx = _find_header_row_index(rows)
    if header_idx < 0:
        return []
    
    header_row = rows[header_idx]
    column_bboxes = _infer_column_bboxes(header_row, table_bbox)

    # Question-anchored row identification:
    # Use Question column cells as authoritative row boundaries
    all_data_cells = [cell for row in rows[header_idx + 1:] for cell in row]
    cells_by_column: Dict[str, List[Dict[str, Any]]] = {
        QUESTION_CELL: [],
        ANSWER_CELL: [],
        MARKS_CELL: [],
    }
    
    for cell in all_data_cells:
        label = _assign_column(cell["bbox"], column_bboxes)
        cells_by_column[label].append(cell)

    # Step 1: Extract Question column cells and use them as row boundaries
    question_cells = cells_by_column[QUESTION_CELL]
    question_cells_sorted = sorted(question_cells, key=lambda c: c["bbox"][1])  # Sort by y1 (top)
    
    # Step 2: Define row boundaries based on each Question cell's Y-extent
    # Each row is defined by [y1, y2] of the question cell
    row_boundaries: List[Dict[str, Any]] = []
    for q_cell in question_cells_sorted:
        y1 = float(q_cell["bbox"][1])  # Top of question cell
        y2 = float(q_cell["bbox"][3])  # Bottom of question cell
        row_boundaries.append({
            "y1": y1,
            "y2": y2,
            "question_cell": q_cell,
            "answer_cells": [],
            "marks_cells": []
        })
    
    # Step 3: Assign Answer and Marks cells to rows based on Y-overlap with question cells
    # A cell belongs to a row if its center Y is within the row's [y1, y2] range
    tolerance = 3.0  # Extra tolerance for cells straddling boundaries
    
    for answer_cell in cells_by_column[ANSWER_CELL]:
        cell_y1 = float(answer_cell["bbox"][1])
        cell_y2 = float(answer_cell["bbox"][3])
        
        # Find the row that this cell overlaps with
        for row in row_boundaries:
            # Check if cell overlaps with row's Y-range
            if cell_y1 < row["y2"] + tolerance and cell_y2 > row["y1"] - tolerance:
                row["answer_cells"].append(answer_cell)
                break
    
    for marks_cell in cells_by_column[MARKS_CELL]:
        cell_y1 = float(marks_cell["bbox"][1])
        cell_y2 = float(marks_cell["bbox"][3])
        
        # Find the row that this cell overlaps with
        for row in row_boundaries:
            # Check if cell overlaps with row's Y-range
            if cell_y1 < row["y2"] + tolerance and cell_y2 > row["y1"] - tolerance:
                row["marks_cells"].append(marks_cell)
                break
    
    # Step 4: Build output rows
    extracted: List[Dict[str, Any]] = []
    for local_row_idx, row in enumerate(row_boundaries):
        q_cell = row["question_cell"]
        a_cells = row["answer_cells"]
        m_cells = row["marks_cells"]
        
        question_text = _strip_html_text(q_cell.get("html")).strip()
        answer_text = "\n".join(
            _strip_html_text(cell.get("html")) for cell in a_cells if _strip_html_text(cell.get("html"))
        ).strip()
        marks_text = "\n".join(
            _strip_html_text(cell.get("html")) for cell in m_cells if _strip_html_text(cell.get("html"))
        ).strip()

        if not (question_text or answer_text or marks_text):
            continue

        all_row_cells = [q_cell] + a_cells + m_cells

        extracted.append(
            {
                "page_index": page_index,
                "table_index": table_index,
                "table_bbox": table_bbox,
                "row_index": local_row_idx,
                "row_bbox": _combine_bboxes(cell["bbox"] for cell in all_row_cells),
                "question_cell_text": question_text,
                "answer_cell_text": answer_text,
                "marks_cell_text": marks_text,
                "question_cell_bbox": q_cell["bbox"],
                "answer_cell_bbox": _combine_bboxes(cell["bbox"] for cell in a_cells),
                "marks_cell_bbox": _combine_bboxes(cell["bbox"] for cell in m_cells),
            }
        )

    return extracted



def parse_question_marker(marker_text: str) -> Optional[Dict[str, Optional[str]]]:
    cleaned = " ".join((marker_text or "").split())
    if not cleaned:
        return None

    match = re.match(r"^\s*(\d+)\s*(.*)$", cleaned)
    if not match:
        return None

    question_number = match.group(1)
    suffix = match.group(2) or ""
    paren_tokens = re.findall(r"\(\s*([A-Za-z0-9]+)\s*\)", suffix)

    primary_marker: Optional[str] = None
    secondary_marker: Optional[str] = None
    if paren_tokens:
        if re.fullmatch(r"[A-Za-z]", paren_tokens[0]):
            primary_marker = paren_tokens[0].lower()
        elif re.fullmatch(SECONDARY_ROMAN_PATTERN, paren_tokens[0].lower()):
            secondary_marker = paren_tokens[0].lower()
        if len(paren_tokens) >= 2 and re.fullmatch(SECONDARY_ROMAN_PATTERN, paren_tokens[1].lower()):
            secondary_marker = paren_tokens[1].lower()

    normalized = f"q{question_number}"
    if primary_marker:
        normalized += f"|({primary_marker})"
    if secondary_marker:
        normalized += f"|({secondary_marker})"

    return {
        "marker_text": cleaned,
        "question_number": question_number,
        "primary_marker": primary_marker,
        "secondary_marker": secondary_marker,
        "normalized_key": normalized,
    }


def _parse_marks_value(marks_text: str) -> Optional[int]:
    numbers = [int(value) for value in re.findall(r"\d+", marks_text or "")]
    if not numbers:
        return None
    return max(numbers)


def _split_marks_from_text(text: str) -> Tuple[str, str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return "", ""
    if re.fullmatch(r"\[\s*\d+\s*\]", cleaned):
        return "", cleaned
    match = re.search(r"\s*(\[\s*\d+\s*\])\s*$", cleaned)
    if not match:
        return cleaned, ""
    return cleaned[: match.start()].strip(), match.group(1).strip()


def _combine_text(existing: str, addition: str) -> str:
    addition_clean = (addition or "").strip()
    if not addition_clean:
        return existing
    if not existing:
        return addition_clean
    return f"{existing}\n{addition_clean}"


def _span_is_bold(font_name: str, flags: Any) -> bool:
    lower = (font_name or "").lower()
    try:
        flags_int = int(flags or 0)
    except (TypeError, ValueError):
        flags_int = 0
    return "bold" in lower or bool(flags_int & 16)


def _bbox_intersects(left: List[float], right: List[float]) -> bool:
    return not (
        float(left[2]) <= float(right[0])
        or float(right[2]) <= float(left[0])
        or float(left[3]) <= float(right[1])
        or float(right[3]) <= float(left[1])
    )


def _scale_bbox_between_spaces(
    bbox: List[float],
    source_page_bbox: List[float],
    target_page_bbox: List[float],
) -> List[float]:
    source_width = float(source_page_bbox[2]) - float(source_page_bbox[0])
    source_height = float(source_page_bbox[3]) - float(source_page_bbox[1])
    target_width = float(target_page_bbox[2]) - float(target_page_bbox[0])
    target_height = float(target_page_bbox[3]) - float(target_page_bbox[1])
    if source_width == 0 or source_height == 0:
        return [float(v) for v in bbox]

    x_scale = target_width / source_width
    y_scale = target_height / source_height
    return [
        float(target_page_bbox[0]) + (float(bbox[0]) - float(source_page_bbox[0])) * x_scale,
        float(target_page_bbox[1]) + (float(bbox[1]) - float(source_page_bbox[1])) * y_scale,
        float(target_page_bbox[0]) + (float(bbox[2]) - float(source_page_bbox[0])) * x_scale,
        float(target_page_bbox[1]) + (float(bbox[3]) - float(source_page_bbox[1])) * y_scale,
    ]


def _extract_pdf_font_metadata(
    pdf_document: Any,
    page_index: int,
    bbox: List[float],
    marker_page_bbox: Optional[List[float]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    if not bbox or len(bbox) != 4:
        return {"words": [], "spans": []}

    page = pdf_document.load_page(page_index)
    pdf_page_bbox = [0.0, 0.0, float(page.rect.width), float(page.rect.height)]
    marker_space_bbox = marker_page_bbox if marker_page_bbox and len(marker_page_bbox) == 4 else pdf_page_bbox
    pdf_bbox = _scale_bbox_between_spaces(bbox, marker_space_bbox, pdf_page_bbox)
    rect = fitz.Rect(pdf_bbox)

    words = []
    for word in page.get_text("words", clip=rect):
        x0, y0, x1, y1, text, block_no, line_no, word_no = word
        word_pdf_bbox = [float(x0), float(y0), float(x1), float(y1)]
        words.append(
            {
                "text": text,
                "bbox": _scale_bbox_between_spaces(word_pdf_bbox, pdf_page_bbox, marker_space_bbox),
                "pdf_bbox": word_pdf_bbox,
                "block_no": int(block_no),
                "line_no": int(line_no),
                "word_no": int(word_no),
            }
        )

    spans: List[Dict[str, Any]] = []
    text_dict = page.get_text("dict")
    clip_bbox = [float(v) for v in pdf_bbox]
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                span_text = span.get("text") or ""
                span_bbox = span.get("bbox")
                if not span_text.strip() or not span_bbox or len(span_bbox) != 4:
                    continue
                span_bbox_f = [float(v) for v in span_bbox]
                if not _bbox_intersects(span_bbox_f, clip_bbox):
                    continue
                spans.append(
                    {
                        "text": span_text,
                        "bbox": _scale_bbox_between_spaces(span_bbox_f, pdf_page_bbox, marker_space_bbox),
                        "pdf_bbox": span_bbox_f,
                        "font_name": span.get("font"),
                        "font_size": float(span.get("size") or 0.0),
                        "flags": int(span.get("flags") or 0),
                        "is_bold": _span_is_bold(span.get("font") or "", span.get("flags")),
                    }
                )

    for word in words:
        word_center_x = (word["bbox"][0] + word["bbox"][2]) / 2.0
        word_center_y = (word["bbox"][1] + word["bbox"][3]) / 2.0
        for span in spans:
            sx0, sy0, sx1, sy1 = span["bbox"]
            if sx0 <= word_center_x <= sx1 and sy0 <= word_center_y <= sy1:
                word["font_name"] = span.get("font_name")
                word["font_size"] = span.get("font_size")
                word["is_bold"] = span.get("is_bold")
                break

    return {"words": words, "spans": spans}


def _marker_dict(
    question_number: str,
    primary_marker: Optional[str] = None,
    secondary_marker: Optional[str] = None,
    marker_text: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    normalized = f"q{question_number}"
    if primary_marker:
        normalized += f"|({primary_marker})"
    if secondary_marker:
        normalized += f"|({secondary_marker})"
    if marker_text is None:
        marker_text = str(question_number)
        if primary_marker:
            marker_text += f"({primary_marker})"
        if secondary_marker:
            marker_text += f"({secondary_marker})"
    return {
        "marker_text": marker_text,
        "question_number": str(question_number),
        "primary_marker": primary_marker,
        "secondary_marker": secondary_marker,
        "normalized_key": normalized,
    }


def _parse_marker_with_context(
    text: str,
    current_marker: Optional[Dict[str, Optional[str]]],
) -> Tuple[Optional[Dict[str, Optional[str]]], str]:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return None, ""

    full_match = re.match(
        r"^(\d{1,2})\s*(?:\(\s*([A-Za-z])\s*\))?\s*(?:\(\s*([ivxlcdmIVXLCDM]+)\s*\))?\s*(.*)$",
        cleaned,
    )
    if full_match and (
        full_match.group(2)
        or not full_match.group(4)
        or float(full_match.group(1)) <= 20
    ):
        question_number = full_match.group(1)
        primary_marker = full_match.group(2).lower() if full_match.group(2) else None
        secondary_marker = full_match.group(3).lower() if full_match.group(3) else None
        remainder = (full_match.group(4) or "").strip()
        if not full_match.group(2) and remainder and not re.match(r"^\(", cleaned[len(question_number) :].strip()):
            return None, cleaned
        marker_text = question_number
        if primary_marker:
            marker_text += f"({primary_marker})"
        if secondary_marker:
            marker_text += f"({secondary_marker})"
        return _marker_dict(question_number, primary_marker, secondary_marker, marker_text), remainder

    relative_match = re.match(
        r"^\(\s*([A-Za-zivxlcdmIVXLCDM]+)\s*\)\s*(?:\(\s*([ivxlcdmIVXLCDM]+)\s*\))?\s*(.*)$",
        cleaned,
    )
    if not relative_match or not current_marker:
        return None, cleaned

    first = relative_match.group(1).lower()
    second = relative_match.group(2).lower() if relative_match.group(2) else None
    remainder = (relative_match.group(3) or "").strip()
    question_number = current_marker.get("question_number")
    if not question_number:
        return None, cleaned

    roman_first = bool(re.fullmatch(SECONDARY_ROMAN_PATTERN, first))
    if roman_first and current_marker.get("primary_marker") and not second:
        primary_marker = current_marker.get("primary_marker")
        secondary_marker = first
    else:
        primary_marker = first
        secondary_marker = second

    marker_text = f"{question_number}"
    if primary_marker:
        marker_text += f"({primary_marker})"
    if secondary_marker:
        marker_text += f"({secondary_marker})"
    return _marker_dict(question_number, primary_marker, secondary_marker, marker_text), remainder


def _new_node(marker_text: str, parsed: Dict[str, Optional[str]], row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": marker_text,
        "parsed_marker": {
            "question_number": parsed.get("question_number"),
            "primary_marker": parsed.get("primary_marker"),
            "secondary_marker": parsed.get("secondary_marker"),
            "normalized_key": parsed.get("normalized_key"),
        },
        "bbox": row.get("question_cell_bbox"),
        "page_index": row.get("page_index"),
        "answer_text": "",
        "marks_text": "",
        "marks_value": None,
        "content_pages": [],
        "answer_word_boxes": [],
        "marks_word_boxes": [],
        "answer_spans": [],
        "marks_spans": [],
    }


def _get_or_create_question_tree(
    questions_map: Dict[str, Dict[str, Any]],
    parsed: Dict[str, Optional[str]],
    row: Dict[str, Any],
) -> Dict[str, Any]:
    qnum = parsed["question_number"] or "?"
    question_key = str(qnum)
    question_entry = questions_map.get(question_key)
    if question_entry is None:
        question_node = _new_node(str(qnum), parsed, row)
        question_entry = {
            "question": question_node,
            "primary_map": {},
            "primary_subparts": [],
        }
        questions_map[question_key] = question_entry

    primary = parsed.get("primary_marker")
    secondary = parsed.get("secondary_marker")
    if not primary:
        return {"node": question_entry["question"], "container": question_entry}

    primary_map = question_entry["primary_map"]
    primary_entry = primary_map.get(primary)
    if primary_entry is None:
        primary_node = _new_node(f"({primary})", parsed, row)
        primary_entry = {
            "primary": primary_node,
            "secondary_map": {},
            "secondary_subparts": [],
        }
        primary_map[primary] = primary_entry
        question_entry["primary_subparts"].append(primary_entry)

    if not secondary:
        return {"node": primary_entry["primary"], "container": primary_entry}

    secondary_map = primary_entry["secondary_map"]
    secondary_entry = secondary_map.get(secondary)
    if secondary_entry is None:
        secondary_node = _new_node(f"({secondary})", parsed, row)
        secondary_entry = {"secondary": secondary_node}
        secondary_map[secondary] = secondary_entry
        primary_entry["secondary_subparts"].append(secondary_entry)

    return {"node": secondary_entry["secondary"], "container": secondary_entry}


def _append_row_to_node(
    node: Dict[str, Any],
    row: Dict[str, Any],
    answer_metadata: Dict[str, List[Dict[str, Any]]],
    marks_metadata: Dict[str, List[Dict[str, Any]]],
) -> None:
    node["answer_text"] = _combine_text(node.get("answer_text", ""), row.get("answer_cell_text", ""))
    node["marks_text"] = _combine_text(node.get("marks_text", ""), row.get("marks_cell_text", ""))

    marks_value = _parse_marks_value(row.get("marks_cell_text", ""))
    if marks_value is not None:
        prior = node.get("marks_value")
        node["marks_value"] = marks_value if prior is None else max(int(prior), marks_value)

    node["content_pages"].append(
        {
            "page_index": row.get("page_index"),
            "table_index": row.get("table_index"),
            "row_index": row.get("row_index"),
            "table_bbox": row.get("table_bbox"),
            "row_bbox": row.get("row_bbox"),
            "question_cell_bbox": row.get("question_cell_bbox"),
            "answer_cell_bbox": row.get("answer_cell_bbox"),
            "marks_cell_bbox": row.get("marks_cell_bbox"),
            "question_cell_text": row.get("question_cell_text", ""),
            "answer_text": row.get("answer_cell_text", ""),
            "marks_text": row.get("marks_cell_text", ""),
        }
    )

    node["answer_word_boxes"].extend(answer_metadata.get("words", []))
    node["marks_word_boxes"].extend(marks_metadata.get("words", []))
    node["answer_spans"].extend(answer_metadata.get("spans", []))
    node["marks_spans"].extend(marks_metadata.get("spans", []))


def _roman_to_int(value: str) -> int:
    roman = {
        "i": 1,
        "v": 5,
        "x": 10,
        "l": 50,
        "c": 100,
        "d": 500,
        "m": 1000,
    }
    total = 0
    prev = 0
    for char in reversed(value.lower()):
        num = roman.get(char, 0)
        if num < prev:
            total -= num
        else:
            total += num
            prev = num
    return total


def _sort_question_entries(questions_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    def q_sort_key(item: Tuple[str, Dict[str, Any]]) -> Tuple[int, str]:
        key = item[0]
        return (int(key), key) if key.isdigit() else (10**9, key)

    def p_sort_key(primary_entry: Dict[str, Any]) -> Tuple[int, str]:
        text = primary_entry["primary"].get("text", "")
        marker = re.sub(r"[()]", "", text).strip().lower()
        if len(marker) == 1 and marker.isalpha():
            return (ord(marker) - ord("a"), marker)
        return (10**9, marker)

    def s_sort_key(secondary_entry: Dict[str, Any]) -> Tuple[int, str]:
        text = secondary_entry["secondary"].get("text", "")
        marker = re.sub(r"[()]", "", text).strip().lower()
        if re.fullmatch(r"[ivxlcdm]+", marker):
            return (_roman_to_int(marker), marker)
        return (10**9, marker)

    questions_out: List[Dict[str, Any]] = []
    for _, q_entry in sorted(questions_map.items(), key=q_sort_key):
        primary_subparts_out = []
        for p_entry in sorted(q_entry["primary_subparts"], key=p_sort_key):
            secondary_out = [
                {"secondary": s_entry["secondary"]}
                for s_entry in sorted(p_entry["secondary_subparts"], key=s_sort_key)
            ]
            primary_subparts_out.append(
                {
                    "primary": p_entry["primary"],
                    "secondary_subparts": secondary_out,
                }
            )
        questions_out.append(
            {
                "question": q_entry["question"],
                "primary_subparts": primary_subparts_out,
            }
        )
    return questions_out


def _build_questions_from_rows(
    extracted_rows: List[Dict[str, Any]],
    pdf_document: Any,
    page_bboxes_by_index: Dict[int, List[float]],
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    questions_map: Dict[str, Dict[str, Any]] = {}
    unresolved_rows: List[Dict[str, Any]] = []
    current_marker: Optional[Dict[str, Optional[str]]] = None

    for row in extracted_rows:
        question_cell_text = (row.get("question_cell_text") or "").strip()
        parsed = parse_question_marker(question_cell_text) if question_cell_text else None
        continuation = False
        if parsed:
            current_marker = parsed
        elif current_marker and ((row.get("answer_cell_text") or "").strip() or (row.get("marks_cell_text") or "").strip()):
            parsed = current_marker
            continuation = True

        if not parsed:
            unresolved_rows.append({**row, "status": "unresolved_marker"})
            continue

        tree_ref = _get_or_create_question_tree(questions_map, parsed, row)
        node = tree_ref["node"]
        row_with_status = {
            **row,
            "status": "continuation" if continuation else "parsed",
            "parsed_marker": parsed,
        }

        answer_bbox = row.get("answer_cell_bbox")
        marks_bbox = row.get("marks_cell_bbox")
        marker_page_bbox = page_bboxes_by_index.get(int(row["page_index"]))
        answer_metadata = (
            _extract_pdf_font_metadata(pdf_document, int(row["page_index"]), answer_bbox, marker_page_bbox)
            if answer_bbox
            else {"words": [], "spans": []}
        )
        marks_metadata = (
            _extract_pdf_font_metadata(pdf_document, int(row["page_index"]), marks_bbox, marker_page_bbox)
            if marks_bbox
            else {"words": [], "spans": []}
        )
        _append_row_to_node(node, row_with_status, answer_metadata, marks_metadata)

    return questions_map, unresolved_rows


def _build_mark_scheme_hierarchy(mark_scheme: Dict[str, Any]) -> Dict[str, Any]:
    """Extract hierarchical structure from mark_scheme.json.
    
    The mark_scheme.json already has the hierarchical structure with 
    question entries containing primary_subparts. This function simply 
    cleans it up for output as hierarchy.json, removing internal fields
    like answer_word_boxes, content_pages, etc.
    """
    def clean_question_entry(q_dict):
        """Remove internal fields, keep text and marks."""
        if not q_dict:
            return q_dict
        return {
            "text": q_dict.get("text"),
            "parsed_marker": q_dict.get("parsed_marker"),
            "bbox": q_dict.get("bbox"),
            "page_index": q_dict.get("page_index"),
            "answer_text": q_dict.get("answer_text"),
            "marks_text": q_dict.get("marks_text"),
            "marks_value": q_dict.get("marks_value"),
        }
    
    hierarchy = {
        "paper_code": mark_scheme.get("paper_code"),
        "questions": []
    }
    
    for q_entry in mark_scheme.get("questions", []):
        cleaned = {
            "question": clean_question_entry(q_entry.get("question")),
            "primary_subparts": []
        }
        
        for primary in q_entry.get("primary_subparts", []):
            primary_cleaned = {
                "primary": clean_question_entry(primary.get("primary")),
                "secondary_subparts": []
            }
            
            for secondary in primary.get("secondary_subparts", []):
                secondary_cleaned = {
                    "secondary": clean_question_entry(secondary.get("secondary"))
                }
                primary_cleaned["secondary_subparts"].append(secondary_cleaned)
            
            cleaned["primary_subparts"].append(primary_cleaned)
        
        hierarchy["questions"].append(cleaned)
    
    return hierarchy


def parse_mark_scheme_paper(
    paper_code: str,
    pdf_dir: Path,
    marker_dir: Path,
    debug_tables: bool = False,
) -> Dict[str, Any]:
    """Parse one mark scheme into flat rows plus a question hierarchy.

    The main path is table-first: Marker table cells and PyMuPDF table
    detection are merged into rows before hierarchy building. The production
    audit still leaves some older 2015/2016 mark schemes empty; treat those as
    a parser coverage gap rather than silently falling back to a stale block
    parser.
    """
    """Parse mark scheme tables using fitz table detection (not Marker)."""
    pdf_path = resolve_pdf_path(paper_code, pdf_dir)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Use fitz table detection instead of Marker
    pdf_document = fitz.open(pdf_path)
    try:
        extracted_rows: List[Dict[str, Any]] = []
        for page_index in range(len(pdf_document)):
            page = pdf_document[page_index]
            table_finder = page.find_tables()
            tables = table_finder.tables
            
            for table_index, fitz_table in enumerate(tables):
                rows = _extract_table_rows(fitz_table, page_index, table_index, fitz_page=page)
                extracted_rows.extend(rows)
                
                # Render debug image if requested
                if debug_tables:
                    try:
                        # Convert fitz table for debug visualization
                        all_data_cells = _fitz_table_to_cells(fitz_table, page)
                        if all_data_cells:
                            table_rows = _cluster_rows(all_data_cells)
                            header_idx = _find_header_row_index(table_rows)
                            
                            debug_output_dir = Path("output/qsplitter/debug_tables")
                            debug_output_dir.mkdir(parents=True, exist_ok=True)
                            debug_file = debug_output_dir / f"{paper_code}_page{page_index:02d}_table{table_index:02d}.png"
                            
                            if header_idx >= 0:
                                # Valid table with header
                                header_row = table_rows[header_idx]
                                table_bbox = [fitz_table.bbox[0], fitz_table.bbox[1], fitz_table.bbox[2], fitz_table.bbox[3]]
                                column_bboxes = _infer_column_bboxes(header_row, table_bbox)
                                all_data_cells_below_header = [cell for row in table_rows[header_idx + 1:] for cell in row]
                                
                                cells_by_column = {
                                    QUESTION_CELL: [],
                                    ANSWER_CELL: [],
                                    MARKS_CELL: [],
                                }
                                for cell in all_data_cells_below_header:
                                    label = _assign_column(cell["bbox"], column_bboxes)
                                    cells_by_column[label].append(cell)
                                
                                question_cells = cells_by_column[QUESTION_CELL]
                                question_cells_sorted = sorted(question_cells, key=lambda c: c["bbox"][1])
                                
                                row_boundaries = []
                                for q_cell in question_cells_sorted:
                                    y1 = float(q_cell["bbox"][1])
                                    y2 = float(q_cell["bbox"][3])
                                    row_boundaries.append({
                                        "y1": y1,
                                        "y2": y2,
                                        "question_cell": q_cell,
                                    })
                            else:
                                # Invalid table
                                cells_by_column = {
                                    QUESTION_CELL: [],
                                    ANSWER_CELL: [],
                                    MARKS_CELL: all_data_cells,
                                }
                                row_boundaries = []
                            
                            _render_table_debug_image(
                                pdf_path,
                                page_index,
                                {"bbox": [fitz_table.bbox[0], fitz_table.bbox[1], fitz_table.bbox[2], fitz_table.bbox[3]]},
                                cells_by_column,
                                row_boundaries,
                                None,  # No marker page bbox for fitz
                                debug_file,
                            )
                            status = "valid" if rows and header_idx >= 0 else "invalid"
                            print(f"Wrote debug table image: {debug_file} ({status})")
                    except Exception as e:
                        print(f"Failed to render debug image: {e}", file=sys.stderr)

        extracted_rows.sort(
            key=lambda row: (
                int(row["page_index"]),
                float(row["row_bbox"][1]) if row.get("row_bbox") else 0.0,
                int(row.get("table_index") or 0),
                int(row.get("row_index") or 0),
            )
        )

        questions_map, unresolved_rows = _build_questions_from_rows(
            extracted_rows,
            pdf_document,
            {},  # No marker page bboxes for fitz tables
        )
        if not questions_map:
            # Fallback: if no tables found, try to extract from text blocks
            # (This assumes OCR text content is available)
            print(f"Warning: No table data extracted for {paper_code}, no text fallback available with fitz", file=sys.stderr)
            extracted_rows = []
            questions_map = {}
            unresolved_rows = []

        return {
            "paper_code": paper_code,
            "year": paper_year_from_code(paper_code),
            "questions": _sort_question_entries(questions_map),
            "rows": extracted_rows,
            "unresolved_rows": unresolved_rows,
            "source_paths": {
                "pdf_path": str(pdf_path),
                "marker_path": "(fitz table detection, not Marker)",
            },
        }
    finally:
        pdf_document.close()


def resolve_pdf_path(paper_code: str, pdf_dir: Path) -> Path:
    """Resolve a mark scheme PDF, allowing the repo's shared paper directory."""
    direct_path = pdf_dir / f"{paper_code}.pdf"
    if direct_path.exists():
        return direct_path

    sibling_shared_path = pdf_dir.parent / "cs_papers" / f"{paper_code}.pdf"
    if sibling_shared_path.exists():
        return sibling_shared_path

    shared_path = Path("resources/pdfs/cs_papers") / f"{paper_code}.pdf"
    if shared_path.exists():
        return shared_path

    return direct_path


def iter_ms_papers(marker_dir: Path) -> Iterable[str]:
    for path in sorted(marker_dir.iterdir()):
        if not path.is_dir():
            continue
        code = path.name
        if "_ms_" in code and (path / f"{code}.json").exists():
            yield code


def process_mark_scheme_paper(
    paper_code: str,
    pdf_dir: Path,
    marker_dir: Path,
    output_dir: Path,
    debug_tables: bool = False,
) -> Dict[str, Any]:
    payload = parse_mark_scheme_paper(paper_code, pdf_dir, marker_dir, debug_tables=debug_tables)
    write_json(output_dir / paper_code / "mark_scheme.json", payload)
    
    # Also write hierarchical structure
    hierarchy = _build_mark_scheme_hierarchy(payload)
    write_json(output_dir / paper_code / "hierarchy.json", hierarchy)
    
    return payload


def process_all_mark_scheme_papers(
    pdf_dir: Path,
    marker_dir: Path,
    output_dir: Path,
    debug_tables: bool = False,
) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for paper_code in iter_ms_papers(marker_dir):
        try:
            results[paper_code] = process_mark_scheme_paper(
                paper_code=paper_code,
                pdf_dir=pdf_dir,
                marker_dir=marker_dir,
                output_dir=output_dir,
                debug_tables=debug_tables,
            )
        except Exception as exc:
            print(f"mark scheme parser failed for {paper_code}: {exc}", file=sys.stderr)
            continue
    return results


def main() -> int:
    args = parse_args()
    debug_tables = args.debug_tables or bool(os.getenv("DEBUG_MS_PARSER"))
    
    if args.paper:
        payload = process_mark_scheme_paper(
            paper_code=args.paper,
            pdf_dir=args.pdf_dir,
            marker_dir=args.marker_dir,
            output_dir=args.output_dir,
            debug_tables=debug_tables,
        )
        print(
            f"Wrote mark scheme output for {args.paper} to "
            f"{args.output_dir / args.paper / 'mark_scheme.json'} "
            f"({len(payload.get('questions', []))} top-level questions)."
        )
        return 0

    results = process_all_mark_scheme_papers(
        pdf_dir=args.pdf_dir,
        marker_dir=args.marker_dir,
        output_dir=args.output_dir,
        debug_tables=debug_tables,
    )
    print(f"Processed {len(results)} mark scheme papers into {args.output_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
