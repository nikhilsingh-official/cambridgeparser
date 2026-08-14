import argparse
import json
from copy import deepcopy
from pathlib import Path

from src.resources.paths import (
    MARKER_OUTPUT_DIR,
    NORMALIZED_MARKER_OUTPUT_DIR,
    SOURCE_OCR_DIR,
)

SURYA_OCR_OUTPUT_DIR = SOURCE_OCR_DIR


def load_json(path):
    """Load a JSON document from disk."""
    with path.open() as f:
        return json.load(f)


def write_json(path, document):
    """Write a JSON document to disk, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(document, f, indent=2)


def scale_point(point, source_page_bbox, target_page_bbox):
    """Scale one x/y point from marker page space into OCR image space."""
    source_width = source_page_bbox[2] - source_page_bbox[0]
    source_height = source_page_bbox[3] - source_page_bbox[1]
    target_width = target_page_bbox[2] - target_page_bbox[0]
    target_height = target_page_bbox[3] - target_page_bbox[1]

    x_scale = target_width / source_width
    y_scale = target_height / source_height

    return [
        target_page_bbox[0] + (point[0] - source_page_bbox[0]) * x_scale,
        target_page_bbox[1] + (point[1] - source_page_bbox[1]) * y_scale,
    ]


def scale_bbox(bbox, source_page_bbox, target_page_bbox):
    """Scale one bbox from marker page space into OCR image space."""
    top_left = scale_point([bbox[0], bbox[1]], source_page_bbox, target_page_bbox)
    bottom_right = scale_point([bbox[2], bbox[3]], source_page_bbox, target_page_bbox)
    return [top_left[0], top_left[1], bottom_right[0], bottom_right[1]]


def normalize_geometry(node, source_page_bbox, target_page_bbox):
    """Recursively scale bbox and polygon fields inside one marker page subtree."""
    if isinstance(node, dict):
        normalized = {}

        for key, value in node.items():
            if key == "bbox":
                normalized[key] = scale_bbox(value, source_page_bbox, target_page_bbox)
            elif key == "polygon":
                normalized[key] = [
                    scale_point(point, source_page_bbox, target_page_bbox) for point in value
                ]
            else:
                normalized[key] = normalize_geometry(value, source_page_bbox, target_page_bbox)

        return normalized

    if isinstance(node, list):
        return [normalize_geometry(item, source_page_bbox, target_page_bbox) for item in node]

    return deepcopy(node)


def normalize_marker_document(marker_document, ocr_pages):
    """Normalize every page in the main marker document into OCR image coordinates."""
    normalized_document = deepcopy(marker_document)
    normalized_pages = []

    for page_index, marker_page in enumerate(marker_document["children"]):
        source_page_bbox = marker_page["bbox"]
        target_page_bbox = ocr_pages[page_index]["image_bbox"]
        normalized_pages.append(normalize_geometry(marker_page, source_page_bbox, target_page_bbox))

    normalized_document["children"] = normalized_pages
    return normalized_document


def normalize_marker_meta(meta_document, marker_document, ocr_pages):
    """Normalize geometry stored in marker meta output, such as TOC polygons."""
    normalized_meta = deepcopy(meta_document)
    normalized_toc = []

    for item in meta_document.get("table_of_contents", []):
        page_index = item["page_id"]
        source_page_bbox = marker_document["children"][page_index]["bbox"]
        target_page_bbox = ocr_pages[page_index]["image_bbox"]

        normalized_item = deepcopy(item)
        normalized_item["polygon"] = [
            scale_point(point, source_page_bbox, target_page_bbox)
            for point in item["polygon"]
        ]
        normalized_toc.append(normalized_item)

    normalized_meta["table_of_contents"] = normalized_toc
    return normalized_meta


def normalize_paper(paper_code, marker_output_dir, ocr_output_dir, normalized_output_dir):
    """Normalize one paper's marker files into OCR image coordinates."""
    ocr_path = ocr_output_dir / paper_code / "results.json"
    marker_path = marker_output_dir / paper_code / f"{paper_code}.json"
    marker_meta_path = marker_output_dir / paper_code / f"{paper_code}_meta.json"

    if not ocr_path.exists() or not marker_path.exists():
        return False

    ocr_document = load_json(ocr_path)
    marker_document = load_json(marker_path)
    ocr_pages = ocr_document[paper_code]

    normalized_marker_document = normalize_marker_document(marker_document, ocr_pages)
    normalized_marker_path = normalized_output_dir / paper_code / f"{paper_code}.json"
    write_json(normalized_marker_path, normalized_marker_document)

    if marker_meta_path.exists():
        marker_meta_document = load_json(marker_meta_path)
        normalized_meta_document = normalize_marker_meta(
            marker_meta_document, marker_document, ocr_pages
        )
        normalized_meta_path = normalized_output_dir / paper_code / f"{paper_code}_meta.json"
        write_json(normalized_meta_path, normalized_meta_document)

    return True


def parse_args():
    """Parse CLI arguments for one-paper or all-paper normalization."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", help="Normalize one paper code only.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Normalize every paper found in marker_output with matching OCR output.",
    )
    parser.add_argument(
        "--marker-output-dir",
        type=Path,
        default=MARKER_OUTPUT_DIR,
        help="Directory containing raw marker output.",
    )
    parser.add_argument(
        "--ocr-dir",
        type=Path,
        default=SURYA_OCR_OUTPUT_DIR,
        help="Directory containing OCR output directories with results.json files.",
    )
    parser.add_argument(
        "--normalized-output-dir",
        type=Path,
        default=NORMALIZED_MARKER_OUTPUT_DIR,
        help="Directory where normalized marker output will be written.",
    )
    return parser.parse_args()


def main():
    """Run marker normalization for one paper or for all available papers."""
    args = parse_args()

    if args.paper:
        normalize_paper(
            args.paper,
            args.marker_output_dir,
            args.ocr_dir,
            args.normalized_output_dir,
        )
        return 0

    if args.all:
        paper_codes = sorted(path.name for path in args.marker_output_dir.iterdir() if path.is_dir())
        for paper_code in paper_codes:
            normalize_paper(
                paper_code,
                args.marker_output_dir,
                args.ocr_dir,
                args.normalized_output_dir,
            )
        return 0

    raise SystemExit("Pass --paper <paper_code> or --all.")


if __name__ == "__main__":
    raise SystemExit(main())
