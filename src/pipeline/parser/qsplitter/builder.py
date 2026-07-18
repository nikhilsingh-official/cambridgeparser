import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .type_definitions import PaperContext, Candidate, HierarchyPayload, ExcludedRegion

from .io import load_json, write_json
from .markers import (
    classify_subpart_marker,
    extract_parenthetical_markers,
    extract_bracketed_marks,
    extract_leading_question_number,
    extract_question_number_from_math_text,
    can_cast_to_int,
    collect_marker_exclusion_bboxes,
    is_in_excluded_region,
    looks_like_marks_pattern,
)
from .cluster import cluster_candidates, select_column_clusters, select_marks_cluster
from .fitz_backend import build_pages_from_fitz
from .debug import write_reading_order_file
from .segmentation import build_segmented_questions


# Paths are intentionally not hardcoded here. Callers must pass pdf_dir, ocr_dir and marker_dir from CLI.

# Heuristic knobs for the production corpus. Keep changes here paired with a
# full qsplitter batch run, because small coordinate shifts can reclassify
# question numbers as code/list numbers or move subparts between columns.
QUESTION_MARKER_MAX_X = 78
SUBPART_MARKER_LEEWAY_VAL = 5.0
MARKS_MARKER_LEEWAY = 1.5
FITZ_TEXT_PRIMARY = True
REQUIRE_BOLD_MARKERS = True

# Marker output contains layout blocks that look like text but should not seed
# questions/subparts. Old 2015 papers have different page-header behavior, so
# load_paper_context relaxes header filtering for those papers below.
QUESTION_EXCLUDED_BLOCK_TYPES = {"PageHeader", "PageFooter"}
EXCLUDED_MARKER_BLOCK_TYPES = {"Picture", "PageHeader", "PageFooter"}
EXCLUSION_OVERRIDES = {
    "9608_s15_qp_13": {11: {"Picture"}},
    "9608_s17_qp_11": {1: {"Picture"}},
    "9608_w19_qp_12": {2: {"Picture"}},
    "9618_s24_qp_21": {5: {"Picture"}},
    "9618_s25_qp_12": {4: {"PageHeader"}},
    "9618_s25_qp_21": {14: {"PageHeader"}},
    "9618_w24_qp_22": {18: {"Picture"}},
    "9618_w24_qp_23": {8: {"PageHeader"}},
    "9618_w25_qp_21": {14: {"PageHeader"}, 16: {"PageHeader"}},
}


def candidate_position(candidate: Dict[str, Any]):
    return candidate["page_index"], candidate["y"], candidate["x"]


def _leading_nonempty_count(chars, upto_index: int) -> int:
    """Count non-empty character texts from start of line up to and including upto_index."""
    count = 0
    for i in range(0, upto_index + 1):
        if (chars[i].get("text") or "").strip():
            count += 1
    return count


def marker_key(marker: Dict[str, Any]):
    return (marker["page_index"], tuple(marker.get("line_id", [])))


def _build_candidate(
    text: str,
    bbox: List[float],
    page_index: int,
    line_index: int,
    marker_type: str,
    *,
    x_anchor: str = "left",
    **extra: Any,
) -> Candidate:
    x = bbox[0] if x_anchor == "left" else bbox[2]
    candidate: Candidate = {
        "text": text,
        "type": marker_type,
        "bbox": bbox,
        "x": x,
        "y": bbox[1],
        "page_index": page_index,
        "line_id": (page_index, line_index),
    }
    candidate.update(extra)
    return candidate


def _has_visible_digit_char(text_line: Dict[str, Any]) -> bool:
    return any(
        char.get("bbox_valid") and can_cast_to_int(char.get("text"))
        for char in text_line["chars"]
    )


def _marker_has_bold_signal(
    chars,
    start_index: int = 0,
    end_index: Optional[int] = None,
    *,
    require_bold: Optional[bool] = None,
) -> bool:
    """Optionally require bold marker glyphs when fitz font metadata is available."""
    if require_bold is None:
        require_bold = REQUIRE_BOLD_MARKERS
    if not require_bold:
        return True
    if end_index is None:
        end_index = len(chars)
    visible_chars = [
        char for char in chars[start_index:end_index] if (char.get("text") or "").strip()
    ]
    bold_values = [bool(char.get("is_bold")) for char in visible_chars if "is_bold" in char]
    if not bold_values:
        return True
    return any(bold_values)


def _marker_uses_monospace_font(chars, start_index: int = 0, end_index: Optional[int] = None) -> bool:
    """Detect Courier-style code line numbers when fitz font metadata is available."""
    if end_index is None:
        end_index = len(chars)
    visible_chars = [
        char for char in chars[start_index:end_index] if (char.get("text") or "").strip()
    ]
    font_names = [
        (char.get("font_name") or "").lower()
        for char in visible_chars
        if "font_name" in char
    ]
    if not font_names:
        return False
    return all("courier" in font_name or "mono" in font_name for font_name in font_names)


def _extract_question_candidate_from_math_line(
    text_line: Dict[str, Any],
    page_index: int,
    line_index: int,
    page_exclusions: List[ExcludedRegion],
    *,
    require_bold: Optional[bool] = None,
) -> Optional[Candidate]:
    question_number = extract_question_number_from_math_text(text_line["text"])
    if question_number is None:
        return None
    if _has_visible_digit_char(text_line):
        return None
    if not _marker_has_bold_signal(text_line["chars"], require_bold=require_bold):
        return None
    if text_line["bbox"][0] > QUESTION_MARKER_MAX_X:
        return None
    if is_in_excluded_region(text_line["bbox"], page_exclusions):
        return None

    return _build_candidate(
        question_number,
        text_line["bbox"],
        page_index,
        line_index,
        "numeric",
    )


def _extract_question_candidate_from_digit_run(
    text_line: Dict[str, Any],
    page_index: int,
    line_index: int,
    page_exclusions: List[ExcludedRegion],
    *,
    require_bold: Optional[bool] = None,
) -> Optional[Candidate]:
    marker = extract_leading_question_number(text_line["chars"])
    if marker is None:
        return None
    if not _marker_has_bold_signal(
        text_line["chars"],
        marker["start_index"],
        marker["end_index"] + 1,
        require_bold=require_bold,
    ):
        return None
    if _marker_uses_monospace_font(
        text_line["chars"],
        marker["start_index"],
        marker["end_index"] + 1,
    ):
        return None
    if _leading_nonempty_count(text_line["chars"], marker["start_index"]) > 2:
        return None
    if (marker["bbox"][0] - text_line["bbox"][0]) > 20:
        return None
    if marker["bbox"][0] > QUESTION_MARKER_MAX_X:
        return None
    if is_in_excluded_region(marker["bbox"], page_exclusions):
        return None

    return _build_candidate(
        marker["text"],
        marker["bbox"],
        page_index,
        line_index,
        "numeric",
    )


def extract_question_candidates(
    data: List[Dict[str, Any]],
    excluded_bboxes_by_page: List[List[ExcludedRegion]],
    *,
    require_bold: Optional[bool] = None,
) -> List[Candidate]:
    question_candidates: List[Candidate] = []
    for page_index, page in enumerate(data):
        page_exclusions = excluded_bboxes_by_page[page_index]
        for line_index, text_line in enumerate(page["text_lines"]):
            math_candidate = _extract_question_candidate_from_math_line(
                text_line,
                page_index,
                line_index,
                page_exclusions,
                require_bold=require_bold,
            )
            if math_candidate is not None:
                question_candidates.append(math_candidate)
                continue

            digit_candidate = _extract_question_candidate_from_digit_run(
                text_line,
                page_index,
                line_index,
                page_exclusions,
                require_bold=require_bold,
            )
            if digit_candidate is not None:
                question_candidates.append(digit_candidate)

    return sorted(question_candidates, key=candidate_position)


def extract_subpart_candidates(
    data: List[Dict[str, Any]],
    excluded_bboxes_by_page: List[List[ExcludedRegion]],
    *,
    require_bold: Optional[bool] = None,
) -> List[Candidate]:
    subpart_candidates: List[Candidate] = []
    for page_index, page in enumerate(data):
        page_exclusions = excluded_bboxes_by_page[page_index]
        for line_index, text_line in enumerate(page["text_lines"]):
            for marker in extract_parenthetical_markers(text_line["text"], text_line["chars"]):
                subpart_kind = classify_subpart_marker(marker["text"])
                if subpart_kind is None:
                    continue
                is_alpha = subpart_kind == "alpha"
                is_roman = subpart_kind == "roman"
                is_ambiguous = subpart_kind == "ambiguous"
                if not _marker_has_bold_signal(
                    text_line["chars"],
                    marker["start_index"],
                    marker["end_index"],
                    require_bold=require_bold,
                ):
                    continue
                if is_in_excluded_region(marker["bbox"], page_exclusions):
                    continue
                subpart_candidates.append(
                    _build_candidate(
                        marker["text"],
                        marker["bbox"],
                        page_index,
                        line_index,
                        subpart_kind,
                        x_anchor="right",
                        marker_kind=subpart_kind,
                        is_alpha=is_alpha,
                        is_roman=is_roman,
                        is_ambiguous=is_ambiguous,
                    )
                )

    return subpart_candidates


def extract_marks_candidates(
    data: List[Dict[str, Any]],
    excluded_bboxes_by_page: List[List[ExcludedRegion]],
) -> List[Candidate]:
    marks_candidates: List[Candidate] = []
    for page_index, page in enumerate(data):
        page_exclusions = excluded_bboxes_by_page[page_index]
        for line_index, text_line in enumerate(page["text_lines"]):
            for mark in extract_bracketed_marks(text_line["text"], text_line["chars"]):
                if is_in_excluded_region(mark["bbox"], page_exclusions) and not looks_like_marks_pattern(
                    mark.get("line_text", "")
                ):
                    continue
                marks_candidates.append(
                    _build_candidate(
                        mark["text"],
                        mark["bbox"],
                        page_index,
                        line_index,
                        "marks",
                        x_anchor="right",
                    )
                )

    return marks_candidates


def split_subpart_candidates(
    question_candidates: List[Candidate],
    subpart_candidates: List[Candidate],
) -> Tuple[List[Candidate], List[Candidate]]:
    primary_subpart_markers: List[Candidate] = []
    secondary_subpart_markers: List[Candidate] = []

    column_clusters = cluster_candidates(subpart_candidates, SUBPART_MARKER_LEEWAY_VAL, x_key="x")
    primary_cluster, secondary_cluster = select_column_clusters(column_clusters)

    if not question_candidates or primary_cluster is None:
        return primary_subpart_markers, secondary_subpart_markers

    def cluster_kind(cluster_members: List[Candidate]) -> str:
        has_alpha = any(member.get("marker_kind") == "alpha" for member in cluster_members)
        has_roman = any(member.get("marker_kind") == "roman" for member in cluster_members)
        if has_alpha and not has_roman:
            return "alpha"
        if has_roman and not has_alpha:
            return "roman"
        if has_alpha and has_roman:
            return "mixed"
        return "unknown"

    cluster_kinds = {
        cluster["id"]: cluster_kind(cluster["members"]) for cluster in column_clusters
    }

    for idx, question in enumerate(question_candidates):
        start_pos = candidate_position(question)
        end_pos = (
            candidate_position(question_candidates[idx + 1])
            if idx + 1 < len(question_candidates)
            else None
        )
         
        # When comparing positions, allow a small y-tolerance (5 points) for same-page markers
        # This handles cases where subpart markers and question numbers are on the same line
        # but have slightly different bounding box y-coordinates.
        Y_TOLERANCE = 5.0
         
        def position_in_segment(candidate_pos, start_pos, end_pos, tolerance=Y_TOLERANCE):
            cand_page, cand_y, _cand_x = candidate_pos
            start_page, start_y, _start_x = start_pos
             
            # Check if candidate is on same page as start
            if cand_page == start_page:
                # If on same page, allow if y is within tolerance of start_y, or after start_y
                if cand_y >= start_y - tolerance:
                    if end_pos is None:
                        return True
                    end_page, end_y, end_x = end_pos
                    if cand_page < end_page or (cand_page == end_page and cand_y < end_y):
                        return True
                return False
           # Otherwise, use standard position comparison
            return candidate_pos >= start_pos and (end_pos is None or candidate_pos < end_pos)
         
        segment = [
            candidate
            for candidate in subpart_candidates
            if position_in_segment(candidate_position(candidate), start_pos, end_pos)
        ]
        for candidate in segment:
            kind = candidate.get("marker_kind")
            cluster_id = candidate.get("cluster_id")
            column_kind = cluster_kinds.get(cluster_id, "unknown")
            if kind in {"alpha", "roman"}:
                resolved = kind
            elif kind == "ambiguous":
                if column_kind in {"alpha", "roman"}:
                    resolved = column_kind
                else:
                    resolved = "roman" if cluster_id == secondary_cluster else "alpha"
            else:
                resolved = None
            candidate["resolved_kind"] = resolved
        secondary_clusters_for_segment = {
            candidate["cluster_id"]
            for candidate in segment
            if candidate.get("resolved_kind") == "roman"
            and candidate.get("cluster_id") != primary_cluster
        }
        has_secondary = bool(secondary_clusters_for_segment)
        for candidate in segment:
            if (
                candidate["cluster_id"] in secondary_clusters_for_segment
                and candidate.get("resolved_kind") == "roman"
            ):
                secondary_subpart_markers.append(candidate)
                continue
            if candidate["cluster_id"] != primary_cluster:
                continue
            if has_secondary and candidate.get("resolved_kind") != "alpha":
                continue
            if not has_secondary and candidate.get("resolved_kind") not in {"alpha", "roman"}:
                continue
            primary_subpart_markers.append(candidate)

    return primary_subpart_markers, secondary_subpart_markers


def select_marks_candidates(marks_candidates: List[Candidate]) -> List[Candidate]:
    marks_clusters = cluster_candidates(marks_candidates, MARKS_MARKER_LEEWAY, x_key="x")
    marks_cluster = select_marks_cluster(marks_clusters)
    if marks_cluster is None:
        return []
    return [candidate for candidate in marks_candidates if candidate.get("cluster_id") == marks_cluster]


def load_paper_context(paper_code: str, pdf_dir: Path, ocr_dir: Path, marker_dir: Path) -> PaperContext:
    pdf_path = pdf_dir / f"{paper_code}.pdf"
    ocr_path = ocr_dir / paper_code / "results.json"
    marker_path = marker_dir / paper_code / f"{paper_code}.json"

    # Do not attempt flexible fallbacks — require explicit, existing inputs.
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not ocr_path.exists():
        raise FileNotFoundError(f"OCR results not found: {ocr_path}")
    if not marker_path.exists():
        raise FileNotFoundError(f"Marker JSON not found: {marker_path}")

    ocr_document = load_json(ocr_path)
    ocr_pages = ocr_document.get(paper_code, [])
    marker_document = load_json(marker_path)

    if ocr_pages:
        image_bbox_by_page = [page["image_bbox"] for page in ocr_pages]
    else:
        import fitz as _fitz
        pdf_document = _fitz.open(str(pdf_path))
        try:
            image_bbox_by_page = [
                [0, 0, pdf_page.rect.width, pdf_page.rect.height] for pdf_page in pdf_document
            ]
        finally:
            pdf_document.close()

    if FITZ_TEXT_PRIMARY:
        data = build_pages_from_fitz(str(pdf_path), image_bbox_by_page, ocr_pages)
    else:
        data = ocr_pages or []

    require_bold = REQUIRE_BOLD_MARKERS
    if require_bold:
        has_bold_true = any(
            char.get("is_bold")
            for page in data
            for line in page.get("text_lines", [])
            for char in line.get("chars", [])
            if "is_bold" in char
        )
        if not has_bold_true:
            require_bold = False

    question_excluded_types = set(QUESTION_EXCLUDED_BLOCK_TYPES)
    excluded_types = set(EXCLUDED_MARKER_BLOCK_TYPES)
    if "_s15_" in paper_code or "_w15_" in paper_code:
        question_excluded_types.discard("PageHeader")
        excluded_types.discard("PageHeader")

    question_excluded_bboxes_by_page = collect_marker_exclusion_bboxes(
        marker_document,
        question_excluded_types,
    )
    excluded_bboxes_by_page = collect_marker_exclusion_bboxes(
        marker_document,
        excluded_types,
    )

    overrides = EXCLUSION_OVERRIDES.get(paper_code)
    if overrides:
        for page_index, drop_types in overrides.items():
            if page_index < len(excluded_bboxes_by_page):
                excluded_bboxes_by_page[page_index] = [
                    entry
                    for entry in excluded_bboxes_by_page[page_index]
                    if entry.get("block_type") not in drop_types
                ]
            if page_index < len(question_excluded_bboxes_by_page):
                question_excluded_bboxes_by_page[page_index] = [
                    entry
                    for entry in question_excluded_bboxes_by_page[page_index]
                    if entry.get("block_type") not in drop_types
                ]

    question_candidates = extract_question_candidates(
        data,
        question_excluded_bboxes_by_page,
        require_bold=require_bold,
    )
    subpart_candidates = extract_subpart_candidates(
        data,
        excluded_bboxes_by_page,
        require_bold=require_bold,
    )
    marks_candidates = extract_marks_candidates(data, excluded_bboxes_by_page)
    primary_subpart_markers, secondary_subpart_markers = split_subpart_candidates(
        question_candidates,
        subpart_candidates,
    )
    marks_markers = select_marks_candidates(marks_candidates)

    return {
        "paper_code": paper_code,
        "pdf_dir": pdf_dir,
        "pdf_path": pdf_path,
        "ocr_path": ocr_path,
        "marker_path": marker_path,
        "data": data,
        "excluded_bboxes_by_page": excluded_bboxes_by_page,
        "question_candidates": question_candidates,
        "primary_subpart_markers": primary_subpart_markers,
        "secondary_subpart_markers": secondary_subpart_markers,
        "marks_markers": marks_markers,
    }


def find_previous_marker(markers: List[Dict[str, Any]], target: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    target_position = candidate_position(target)
    target_page, target_y, _target_x = target_position
    
    # When comparing positions, allow a small y-tolerance (5 points) for same-page markers
    # This handles cases where markers on the same line have slightly different y-coordinates.
    Y_TOLERANCE = 5.0
    
    prior_markers = []
    for marker in markers:
        marker_page, marker_y, _marker_x = candidate_position(marker)
        
        # Include marker if:
        # - Different page and marker comes before target, OR
        # - Same page and marker is within tolerance of target y (same line) but earlier, OR
        # - Same page and marker is above target (lower y)
        if marker_page < target_page:
            prior_markers.append(marker)
        elif marker_page == target_page:
            if marker_y <= target_y + Y_TOLERANCE:
                # On same page and on same line or above - always include
                prior_markers.append(marker)
        # else: marker is on later page, skip
    
    if not prior_markers:
        return None
    return max(prior_markers, key=candidate_position)


def build_hierarchical_structure(paper_code: str, pdf_dir: Path, ocr_dir: Path, marker_dir: Path, context: Optional[PaperContext] = None) -> HierarchyPayload:
    if context is None:
        context = load_paper_context(paper_code, pdf_dir, ocr_dir, marker_dir)

    question_markers = sorted(context["question_candidates"], key=candidate_position)
    primary_markers = sorted(context["primary_subpart_markers"], key=candidate_position)
    secondary_markers = sorted(context["secondary_subpart_markers"], key=candidate_position)

    primaries_by_question = {}
    for primary in primary_markers:
        question = find_previous_marker(question_markers, primary)
        if question is None:
            continue
        primaries_by_question.setdefault(marker_key(question), []).append(primary)

    for markers in primaries_by_question.values():
        markers.sort(key=candidate_position)

    secondaries_by_primary = {}
    for secondary in secondary_markers:
        question = find_previous_marker(question_markers, secondary)
        if question is None:
            continue
        primaries = primaries_by_question.get(marker_key(question), [])
        if not primaries:
            continue
        primary = find_previous_marker(primaries, secondary)
        if primary is None:
            continue
        secondaries_by_primary.setdefault(marker_key(primary), []).append(secondary)

    for markers in secondaries_by_primary.values():
        markers.sort(key=candidate_position)

    questions_out = []
    for question in question_markers:
        question_primaries = primaries_by_question.get(marker_key(question), [])
        primaries_out = []
        for primary in question_primaries:
            primaries_out.append(
                {
                    "primary": {"text": primary["text"], "bbox": primary["bbox"], "page_index": primary["page_index"], "x": primary["bbox"][0], "y": primary["bbox"][1], "line_id": primary.get("line_id")},
                    "secondary_subparts": [
                        {"secondary": {"text": secondary["text"], "bbox": secondary["bbox"], "page_index": secondary["page_index"], "x": secondary["bbox"][0], "y": secondary["bbox"][1], "line_id": secondary.get("line_id")}}
                        for secondary in secondaries_by_primary.get(marker_key(primary), [])
                    ],
                }
            )
        questions_out.append({"question": {"text": question["text"], "bbox": question["bbox"], "page_index": question["page_index"], "x": question["bbox"][0], "y": question["bbox"][1], "line_id": question.get("line_id")}, "primary_subparts": primaries_out})

    return {"paper_code": paper_code, "questions": questions_out}


def build_output_payload(paper_code: Optional[str], pdf_dir: Path, ocr_dir: Path, marker_dir: Path) -> HierarchyPayload:
    if paper_code is None:
        paper_code = os.environ.get("PAPER_CODE")
        if paper_code is None:
            raise SystemExit("Please provide paper_code either as argument or PAPER_CODE env var")
    return build_hierarchical_structure(paper_code, pdf_dir, ocr_dir, marker_dir)


def process_paper(
    paper_code: str,
    pdf_dir: Path,
    ocr_dir: Path,
    marker_dir: Path,
    output_dir: Path,
    *,
    debug_bboxes: bool = False,
) -> HierarchyPayload:
    """Build and persist hierarchy + segmented text outputs for one paper.

    Behavior:
    - Always returns the hierarchical payload.
    - Always writes:
      - hierarchy.json (marker hierarchy)
      - segmented_questions.json (marker coordinates + extracted text per segment)
    - When the QSPLITTER_DEBUG env var is set (truthy) or debug_bboxes=True, also writes
      reading-order and debug images with segment content bboxes overlaid.
    """
    context = load_paper_context(paper_code, pdf_dir, ocr_dir, marker_dir)
    payload = build_hierarchical_structure(paper_code, pdf_dir, ocr_dir, marker_dir, context=context)
    paper_output_dir = output_dir / paper_code
    paper_output_dir.mkdir(parents=True, exist_ok=True)
    write_json(paper_output_dir / "hierarchy.json", payload)

    segmented_payload = build_segmented_questions(
        paper_code=paper_code,
        hierarchy_payload=payload,
        pdf_dir=pdf_dir,
        ocr_dir=ocr_dir,
        context=context,
    )
    write_json(paper_output_dir / "segmented_questions.json", segmented_payload)

    # Conditionally write debug artifacts when env var is present
    debug_mode_enabled = bool(os.environ.get("QSPLITTER_DEBUG") or debug_bboxes)
    if debug_mode_enabled:
        # reading order
        write_reading_order_file(context["data"], paper_output_dir / "reading_order.txt")
        # render debug images using diagnostics module if available
        try:
            from src.pipeline.analysis.diagnostics.debug_renderer import write_debug_page_images

            write_debug_page_images(
                context,
                paper_output_dir,
                segmented_payload=segmented_payload,
                draw_segment_bboxes=True,
            )
        except Exception:
            # diagnostics optional — ignore failures here
            pass

    return payload


def process_all_papers(
    pdf_dir: Path,
    ocr_dir: Path,
    marker_dir: Path,
    output_dir: Path,
    *,
    debug_bboxes: bool = False,
) -> Dict[str, Any]:
    """Process every paper found in the normalized marker output directory.

    Returns a dict mapping paper_code -> payload
    """
    results: Dict[str, Any] = {}
    for path in marker_dir.iterdir():
        if not path.is_dir():
            continue
        paper_code = path.name
        try:
            payload = process_paper(
                paper_code,
                pdf_dir,
                ocr_dir,
                marker_dir,
                output_dir,
                debug_bboxes=debug_bboxes,
            )
            results[paper_code] = payload
        except Exception:
            # skip failing papers but keep going
            continue
    return results
