"""Canonical filesystem layout for source and generated resources.

Parser code should depend on these path constants for default locations, while
website code should read generated artifacts through the same constants. That
keeps generated data out of parser packages and gives the frontend one stable
resource root.
"""

from pathlib import Path

RESOURCE_ROOT = Path("resources")
GENERATED_RESOURCES_DIR = RESOURCE_ROOT / "generated"

SOURCE_PDF_DIR = RESOURCE_ROOT / "pdfs" / "cs_papers"
SOURCE_OCR_DIR = RESOURCE_ROOT / "ocr" / "surya_output"

MARKER_OUTPUT_DIR = GENERATED_RESOURCES_DIR / "marker_output"
NORMALIZED_MARKER_OUTPUT_DIR = GENERATED_RESOURCES_DIR / "normalized_marker_output"
QP_OUTPUT_DIR = GENERATED_RESOURCES_DIR / "qp_output"
MS_OUTPUT_DIR = GENERATED_RESOURCES_DIR / "ms_output"
PSEUDOCODE_WRITING_DIR = GENERATED_RESOURCES_DIR / "pseudocode_writing_hits"

PSEUDOCODE_WRITING_SELECTED_JSON = (
    PSEUDOCODE_WRITING_DIR / "pseudocode_writing_selected.json"
)
PSEUDOCODE_WRITING_CONTEXT_JSON = (
    PSEUDOCODE_WRITING_DIR / "pseudocode_writing_final_qp_ms_context.json"
)
PSEUDOCODE_MARKING_POINTS_JSON = (
    PSEUDOCODE_WRITING_DIR / "pseudocode_writing_final_qp_ms_marking_points.json"
)
PSEUDOCODE_QUESTION_RECORDS_JSON = (
    PSEUDOCODE_WRITING_DIR / "pseudocode_question_records.json"
)
PSEUDOCODE_QUESTION_SCREENSHOTS_DIR = (
    PSEUDOCODE_WRITING_DIR / "pseudocode_question_screenshots"
)
EXTRACTION_VALIDATION_JSON = PSEUDOCODE_WRITING_DIR / "extraction_validation.json"
MARKING_POINT_VALIDATION_JSON = (
    PSEUDOCODE_WRITING_DIR / "marking_point_validation.json"
)
GRADING_EVAL_RESULTS_JSON = PSEUDOCODE_WRITING_DIR / "grading_eval_results.json"
