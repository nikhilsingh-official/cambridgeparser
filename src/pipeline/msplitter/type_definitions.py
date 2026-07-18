from typing import TypedDict, List, Any, Optional, Tuple, Dict

# Basic OCR character entry
class Char(TypedDict, total=False):
    text: str
    bbox: List[float]
    bbox_valid: bool
    is_bold: bool
    font_name: str

# Text line produced by OCR or fitz
class TextLine(TypedDict, total=False):
    text: str
    bbox: List[float]
    chars: List[Char]
    line_id: Tuple[int, int]

# Page representation
class PageData(TypedDict, total=False):
    image_bbox: List[float]
    text_lines: List[TextLine]

# Candidate / marker entry
class Candidate(TypedDict, total=False):
    text: str
    type: str
    bbox: List[float]
    x: float
    y: float
    page_index: int
    line_id: Any
    cluster_id: int

# Exclusion region entry
class ExcludedRegion(TypedDict, total=False):
    bbox: List[float]
    block_type: str

# Context returned by load_paper_context
class PaperContext(TypedDict, total=False):
    paper_code: str
    pdf_dir: str
    pdf_path: str
    ocr_path: str
    marker_path: str
    data: List[PageData]
    excluded_bboxes_by_page: List[List[ExcludedRegion]]
    question_candidates: List[Candidate]
    primary_subpart_markers: List[Candidate]
    secondary_subpart_markers: List[Candidate]
    marks_markers: List[Candidate]

# Hierarchical output payload
class HierarchyPayload(TypedDict, total=False):
    paper_code: str
    questions: List[Dict[str, Any]]

__all__ = [
    "Char",
    "TextLine",
    "PageData",
    "Candidate",
    "ExcludedRegion",
    "PaperContext",
    "HierarchyPayload",
]
