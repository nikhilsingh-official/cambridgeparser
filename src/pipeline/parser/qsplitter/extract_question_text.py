"""Legacy bbox text extraction helpers.

The current production path gets segment text from
``qsplitter.segmentation.build_segmented_questions``. Keep this module only for
older experiments that consumed ``question_texts.json``.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import fitz  # PyMuPDF


def extract_text_from_bbox_fitz(pdf_path: str, page_index: int, bbox: List[float]) -> str:
    """
    Extract text from PDF using fitz.
    Args:
        pdf_path: Path to PDF file
        page_index: 0-based page index
        bbox: [x0, y0, x1, y1] bounding box
    Returns:
        Extracted text (may be empty if fitz finds nothing)
    """
    try:
        doc = fitz.open(pdf_path)
        if page_index >= len(doc):
            return ""
        
        page = doc[page_index]
        rect = fitz.Rect(bbox)
        text = page.get_text("text", clip=rect)
        doc.close()
        
        return text.strip()
    except Exception as e:
        print(f"Warning: fitz extraction failed for {pdf_path} page {page_index}: {e}")
        return ""


def extract_text_from_ocr(ocr_dir: Path, paper_code: str, page_index: int, bbox: List[float], tolerance: float = 5.0) -> str:
    """
    Extract text from OCR reading_order.txt using bbox overlap.
    Args:
        ocr_dir: Path to OCR output directory
        paper_code: Paper code (e.g., "9608_w18_qp_21")
        page_index: 0-based page index
        bbox: [x0, y0, x1, y1] target bounding box
        tolerance: Tolerance for bbox overlap matching
    Returns:
        Extracted text from OCR lines within bbox
    """
    reading_order_path = ocr_dir / paper_code / "reading_order.txt"
    
    if not reading_order_path.exists():
        return ""
    
    try:
        text_parts = []
        with open(reading_order_path) as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith("page"):
                    continue
                
                # Parse: page NNN line NNN bbox=[x0,y0,x1,y1] text=...
                match = re.match(r"page (\d+) line \d+ bbox=\[([\d., ]+)\] text=(.+)", line)
                if not match:
                    continue
                
                page_num = int(match.group(1))
                if page_num != page_index + 1:  # OCR is 1-indexed
                    continue
                
                bbox_str = match.group(2)
                text = match.group(3)
                
                try:
                    ocr_bbox = [float(x) for x in bbox_str.split(", ")]
                    # Check if OCR bbox overlaps with target bbox
                    if _bbox_overlap(ocr_bbox, bbox, tolerance):
                        text_parts.append(text)
                except:
                    continue
        
        return " ".join(text_parts)
    except Exception as e:
        print(f"Warning: OCR extraction failed for {paper_code} page {page_index}: {e}")
        return ""


def _bbox_overlap(bbox1: List[float], bbox2: List[float], tolerance: float = 5.0) -> bool:
    """
    Check if two bboxes overlap (with tolerance).
    Each bbox is [x0, y0, x1, y1]
    """
    x0_1, y0_1, x1_1, y1_1 = bbox1
    x0_2, y0_2, x1_2, y1_2 = bbox2
    
    # Check overlap: bbox1 overlaps bbox2 if they share any area
    # Allow tolerance on edges
    return (x0_1 < x1_2 + tolerance and x1_1 + tolerance > x0_2 and
            y0_1 < y1_2 + tolerance and y1_1 + tolerance > y0_2)


def extract_text_from_bbox(pdf_path: str, ocr_dir: Path, paper_code: str, 
                          page_index: int, bbox: List[float]) -> Tuple[str, str]:
    """
    Extract text from bbox using hybrid fitz + OCR approach.
    Args:
        pdf_path: Path to PDF file
        ocr_dir: Path to OCR output directory
        paper_code: Paper code
        page_index: 0-based page index
        bbox: [x0, y0, x1, y1] bounding box
    Returns:
        (extracted_text, source: "fitz" | "ocr" | "empty")
    """
    # Try fitz first
    text = extract_text_from_bbox_fitz(pdf_path, page_index, bbox)
    if text:
        return text, "fitz"
    
    # Fall back to OCR
    text = extract_text_from_ocr(ocr_dir, paper_code, page_index, bbox)
    if text:
        return text, "ocr"
    
    return "", "empty"


def extract_text_for_questions(paper_code: str, pdf_dir: Path, hierarchy_dir: Path, 
                               ocr_dir: Path) -> Dict:
    """
    Extract text for all questions and subparts in a paper.
    For questions: extract from question marker to first primary subpart (or page edge).
    For subparts: extract text following the subpart marker.
    
    Args:
        paper_code: Paper code
        pdf_dir: Directory containing PDFs
        hierarchy_dir: Directory containing hierarchy.json files
        ocr_dir: Directory containing OCR output
    Returns:
        {
            q_num: {
                "text": "question text",
                "source": "fitz|ocr|empty",
                "bbox": [x0, y0, x1, y1],
                "page_index": N,
                "primaries": [...]
            }
        }
    """
    # Load hierarchy
    hierarchy_path = hierarchy_dir / paper_code / "hierarchy.json"
    if not hierarchy_path.exists():
        print(f"Warning: No hierarchy.json for {paper_code}")
        return {}
    
    with open(hierarchy_path) as f:
        hierarchy = json.load(f)
    
    # Find PDF
    pdf_files = list(pdf_dir.glob(f"*{paper_code}*.pdf"))
    if not pdf_files:
        print(f"Warning: No PDF found for {paper_code}")
        return {}
    
    pdf_path = str(pdf_files[0])
    
    # Extract all OCR text lines for reference
    ocr_path = ocr_dir / paper_code / "reading_order.txt"
    ocr_lines = []
    if ocr_path.exists():
        with open(ocr_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("page"):
                    ocr_lines.append(line)
    
    result = {}
    questions = hierarchy.get("questions", [])
    
    for q_idx, question in enumerate(questions):
        q_marker = question["question"]["text"]
        q_bbox = question["question"]["bbox"]
        q_page = question["question"]["page_index"]
        
        # For question text: expand bbox from question marker downward to capture content
        # Get bbox of first primary subpart on same page to limit expansion
        first_primary_bbox = None
        for primary in question.get("primary_subparts", []):
            if primary["primary"]["page_index"] == q_page:
                first_primary_bbox = primary["primary"]["bbox"]
                break
        
        # Create expanded bbox: from question marker to first subpart (or bottom of page)
        if first_primary_bbox:
            # Extend from question y0 to first primary y0
            q_bbox_expanded = [
                q_bbox[0],           # x0
                q_bbox[1],           # y0 (question top)
                850,                 # x1 (page width)
                first_primary_bbox[1] - 5  # y1 (before first subpart, with buffer)
            ]
        else:
            # No subparts on same page - extend to page bottom
            q_bbox_expanded = [
                q_bbox[0],
                q_bbox[1],
                850,
                800  # Approximate page height
            ]
        
        text, source = extract_text_from_bbox(pdf_path, ocr_dir, paper_code, q_page, q_bbox_expanded)
        
        q_data = {
            "text": text,
            "source": source,
            "bbox": q_bbox,
            "page_index": q_page,
            "primaries": []
        }
        
        # Extract primary subparts
        for p_idx, primary in enumerate(question.get("primary_subparts", [])):
            p_marker = primary["primary"]["text"]
            p_bbox = primary["primary"]["bbox"]
            p_page = primary["primary"]["page_index"]
            
            # For subpart text: expand bbox from subpart marker downward
            # Look for next subpart (same primary or secondary) to limit expansion
            next_bbox = None
            
            # Check for next primary on same page
            for next_p in questions[q_idx].get("primary_subparts", [])[p_idx + 1:]:
                if next_p["primary"]["page_index"] == p_page:
                    next_bbox = next_p["primary"]["bbox"]
                    break
            
            # If no next primary, check for secondary subparts
            if not next_bbox and primary.get("secondary_subparts", []):
                first_secondary = primary["secondary_subparts"][0]["secondary"]
                if first_secondary["page_index"] == p_page:
                    next_bbox = first_secondary["bbox"]
            
            # Create expanded bbox
            if next_bbox:
                p_bbox_expanded = [
                    p_bbox[0],
                    p_bbox[1],
                    850,
                    next_bbox[1] - 5
                ]
            else:
                p_bbox_expanded = [
                    p_bbox[0],
                    p_bbox[1],
                    850,
                    800
                ]
            
            p_text, p_source = extract_text_from_bbox(pdf_path, ocr_dir, paper_code, p_page, p_bbox_expanded)
            
            p_data = {
                "text": p_text,
                "source": p_source,
                "marker": p_marker,
                "bbox": p_bbox,
                "page_index": p_page,
                "secondaries": []
            }
            
            # Extract secondary subparts
            for s_idx, secondary in enumerate(primary.get("secondary_subparts", [])):
                s_marker = secondary["secondary"]["text"]
                s_bbox = secondary["secondary"]["bbox"]
                s_page = secondary["secondary"]["page_index"]
                
                # For secondary: expand downward to next secondary or subpart
                next_s_bbox = None
                
                # Check for next secondary on same page
                for next_s in primary.get("secondary_subparts", [])[s_idx + 1:]:
                    if next_s["secondary"]["page_index"] == s_page:
                        next_s_bbox = next_s["secondary"]["bbox"]
                        break
                
                # Create expanded bbox
                if next_s_bbox:
                    s_bbox_expanded = [
                        s_bbox[0],
                        s_bbox[1],
                        850,
                        next_s_bbox[1] - 5
                    ]
                else:
                    s_bbox_expanded = [
                        s_bbox[0],
                        s_bbox[1],
                        850,
                        800
                    ]
                
                s_text, s_source = extract_text_from_bbox(pdf_path, ocr_dir, paper_code, s_page, s_bbox_expanded)
                
                s_data = {
                    "text": s_text,
                    "source": s_source,
                    "marker": s_marker,
                    "bbox": s_bbox,
                    "page_index": s_page
                }
                
                p_data["secondaries"].append(s_data)
            
            q_data["primaries"].append(p_data)
        
        result[f"q{q_marker}"] = q_data
    
    return result


def batch_extract_all_papers(pdf_dir: Path, hierarchy_dir: Path, ocr_dir: Path, 
                             output_dir: Path) -> Dict[str, Dict]:
    """
    Extract text for all papers.
    Saves results to output_dir/question_texts.json
    Returns: {paper_code: question_data}
    """
    all_results = {}
    
    # Find all hierarchy files
    papers = set()
    for hierarchy_file in hierarchy_dir.rglob("hierarchy.json"):
        paper_code = hierarchy_file.parent.name
        papers.add(paper_code)
    
    print(f"Extracting text for {len(papers)} papers...")
    
    for idx, paper_code in enumerate(sorted(papers), 1):
        print(f"  [{idx}/{len(papers)}] {paper_code}...", end=" ", flush=True)
        
        result = extract_text_for_questions(paper_code, pdf_dir, hierarchy_dir, ocr_dir)
        all_results[paper_code] = result
        
        print(f"OK ({len(result)} questions)")
    
    # Save to JSON
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "question_texts.json"
    
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nExtracted texts saved to {output_path}")
    
    return all_results


if __name__ == "__main__":
    import sys
    
    pdf_dir = Path("resources/pdfs/cs_papers_qp")
    hierarchy_dir = Path("output/qsplitter_all")
    ocr_dir = Path("resources/ocr/surya_output")
    output_dir = Path("output")
    
    batch_extract_all_papers(pdf_dir, hierarchy_dir, ocr_dir, output_dir)
