from pathlib import Path
from typing import Any, Dict, Optional

import fitz
from PIL import Image, ImageDraw, ImageFont

from src.pipeline.parser.qsplitter import builder as _builder
from src.pipeline.parser.qsplitter import cluster as _cluster


def render_pdf_page(pdf_document: Any, page_index: int, image_bbox):
    pdf_page = pdf_document.load_page(page_index)
    target_width = image_bbox[2] - image_bbox[0]
    target_height = image_bbox[3] - image_bbox[1]
    x_scale = target_width / pdf_page.rect.width
    y_scale = target_height / pdf_page.rect.height
    pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(x_scale, y_scale), alpha=False)
    return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)


def draw_labeled_bbox(draw: ImageDraw.ImageDraw, bbox, label: str, color: str, font):
    draw.rectangle(bbox, outline=color, width=2)
    label_position = (bbox[0] + 2, max(0, bbox[1] - 14))
    text_bbox = draw.textbbox(label_position, label, font=font)
    draw.rectangle(text_bbox, fill="white", outline=color, width=1)
    draw.text(label_position, label, fill=color, font=font)


def build_hierarchical_marks_map(context: Dict[str, Any]):
    marks_by_target = {}
    all_candidates = (
        [(q, "question") for q in context["question_candidates"]]
        + [(p, "primary") for p in context["primary_subpart_markers"]]
        + [(s, "secondary") for s in context["secondary_subpart_markers"]]
    )

    for mark in context["marks_markers"]:
        mark_page = mark["page_index"]
        mark_y = mark["y"]
        candidates_above = [
            (marker, mtype)
            for marker, mtype in all_candidates
            if marker["page_index"] == mark_page and marker["y"] < mark_y
        ]

        if candidates_above:
            target_marker, target_type = max(candidates_above, key=lambda x: x[0]["y"])
            marks_by_target[(mark["page_index"], mark["line_id"])] = (
                target_type,
                (target_marker["page_index"], target_marker["line_id"]),
            )

    return marks_by_target


def _collect_segment_bbox_overlays(segmented_payload: Dict[str, Any]) -> dict[int, list[Dict[str, Any]]]:
    overlays_by_page: dict[int, list[Dict[str, Any]]] = {}

    def add_segment_pages(label: str, color: str, marker: Dict[str, Any]) -> None:
        for page in marker.get("content_pages", []):
            page_index = page.get("page_index")
            bbox = page.get("bbox")
            if not isinstance(page_index, int) or not isinstance(bbox, list) or len(bbox) != 4:
                continue
            overlays_by_page.setdefault(page_index, []).append(
                {"bbox": bbox, "label": label, "color": color}
            )

    for question in segmented_payload.get("questions", []):
        q_marker = question.get("question", {})
        q_text = q_marker.get("text", "?")
        add_segment_pages(f"Q {q_text}", "magenta", q_marker)

        for primary in question.get("primary_subparts", []):
            p_marker = primary.get("primary", {})
            p_text = p_marker.get("text", "?")
            add_segment_pages(f"P {p_text}", "deepskyblue", p_marker)

            for secondary in primary.get("secondary_subparts", []):
                s_marker = secondary.get("secondary", {})
                s_text = s_marker.get("text", "?")
                add_segment_pages(f"S {s_text}", "springgreen", s_marker)

    return overlays_by_page


def write_debug_page_images(
    context: Dict[str, Any],
    output_dir: Path,
    *,
    segmented_payload: Optional[Dict[str, Any]] = None,
    draw_segment_bboxes: bool = False,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    question_max_x = _builder.QUESTION_MARKER_MAX_X

    question_markers = sorted(context["question_candidates"], key=_builder.candidate_position)
    try:
        q_clusters = _cluster.cluster_candidates(question_markers, _builder.QUESTION_MARKER_LEEWAY, x_key="x")
        if q_clusters:

            def cluster_score(c):
                pages = len(set(m["page_index"] for m in c["members"]))
                return (pages, c.get("size", 0), c.get("quality", 0))

            best = max(q_clusters, key=cluster_score)["id"]
            question_markers = [m for m in question_markers if m.get("cluster_id") == best]
    except Exception:
        pass

    marks_map = build_hierarchical_marks_map(context)
    segment_overlays = (
        _collect_segment_bbox_overlays(segmented_payload)
        if draw_segment_bboxes and segmented_payload is not None
        else {}
    )
    pdf_document = fitz.open(context["pdf_path"])

    try:
        for page_index, page in enumerate(context["data"]):
            page_image = render_pdf_page(pdf_document, page_index, page["image_bbox"])
            draw = ImageDraw.Draw(page_image)

            if not draw_segment_bboxes:
                draw.line([(question_max_x, 0), (question_max_x, page_image.height)], fill="orange", width=2)
                draw.text((question_max_x + 4, 4), f"Q x<= {question_max_x}", fill="orange", font=font)

                for entry in context["excluded_bboxes_by_page"][page_index]:
                    bbox = entry["bbox"] if isinstance(entry, dict) else entry
                    if bbox:
                        draw.rectangle(bbox, outline="red", width=2)

                for marker in question_markers:
                    if marker["page_index"] == page_index:
                        cluster_label = f"Q-{marker.get('cluster_id', '?')}"
                        draw_labeled_bbox(draw, marker["bbox"], cluster_label, "blue", font)

                for marker in context["primary_subpart_markers"]:
                    if marker["page_index"] == page_index:
                        cluster_label = f"P-{marker.get('cluster_id', '?')}"
                        draw_labeled_bbox(draw, marker["bbox"], cluster_label, "purple", font)

                for marker in context["secondary_subpart_markers"]:
                    if marker["page_index"] == page_index:
                        cluster_label = f"S-{marker.get('cluster_id', '?')}"
                        draw_labeled_bbox(draw, marker["bbox"], cluster_label, "green", font)

                for mark in context["marks_markers"]:
                    if mark["page_index"] != page_index:
                        continue
                    key = (mark["page_index"], mark["line_id"])
                    if key in marks_map:
                        target_type, _ = marks_map[key]
                        color = {"question": "gold", "primary": "cyan", "secondary": "lime"}.get(
                            target_type, "gold"
                        )
                    else:
                        color = "gold"
                    cluster_label = f"M-{mark.get('cluster_id', '?')}"
                    draw_labeled_bbox(draw, mark["bbox"], cluster_label, color, font)

            for overlay in segment_overlays.get(page_index, []):
                draw_labeled_bbox(
                    draw,
                    overlay["bbox"],
                    overlay["label"],
                    overlay["color"],
                    font,
                )

            output_path = output_dir / f"{context['paper_code']}_page_{page_index + 1:03d}.png"
            page_image.save(output_path)
    finally:
        pdf_document.close()
