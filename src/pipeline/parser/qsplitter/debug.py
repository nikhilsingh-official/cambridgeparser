from pathlib import Path
from typing import List
from .type_definitions import PageData


def write_reading_order_file(pages: List[PageData], output_path: Path) -> None:
    """Write a reading order file for debugging. Lists all text lines in document order."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered_lines = []
    for page_index, page in enumerate(pages):
        for line_index, line in enumerate(page["text_lines"]):
            bbox = line["bbox"]
            ordered_lines.append({
                "page_index": page_index,
                "line_index": line_index,
                "y": bbox[1],
                "x": bbox[0],
                "bbox": bbox,
                "text": line.get("text") or "",
            })

    ordered_lines.sort(key=lambda item: (item["page_index"], item["y"], item["x"]))
    with output_path.open("w") as f:
        for line in ordered_lines:
            page_num = line["page_index"] + 1
            f.write(
                f"page {page_num:03d} line {line['line_index']:03d} "
                f"bbox={line['bbox']} text={line['text']}\n"
            )
