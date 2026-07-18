"""Legacy keyword-scoring classifier for extracted question text.

The maintained production selector is ``select_pseudocode_writing.py``, which
classifies write-pseudocode prompts directly from ``segmented_questions.json``.
This module remains for comparing against older ``question_texts.json`` runs.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# Pseudocode keywords with scoring weights
PSEUDOCODE_KEYWORDS = {
    # Control flow (high weight)
    "IF": 15, "THEN": 15, "ELSE": 15, "ELSE IF": 15, "ELSIF": 15,
    "ENDIF": 15, "END IF": 15,
    "FOR": 20, "WHILE": 20, "DO": 15, "UNTIL": 15, "REPEAT": 15, "LOOP": 15,
    "NEXT": 10, "ENDWHILE": 10, "ENDFOR": 10, "ENDLOOP": 10,
    
    # Subroutines (high weight)
    "PROCEDURE": 20, "PROCEDURE": 20, "FUNCTION": 15, "CALL": 15,
    "RETURN": 15, "DECLARE": 10, "ENDPROCEDURE": 10, "ENDFUNCTION": 10,
    
    # Data structures
    "ARRAY": 12, "RECORD": 12, "TYPE": 10, "CLASS": 10, "STRUCT": 10,
    
    # Operators
    "MOD": 12, "DIV": 12, "AND": 10, "OR": 10, "NOT": 10,
    
    # Values
    "TRUE": 8, "FALSE": 8, "NULL": 8, "POINTER": 8,
    
    # Assignment operators (lower weight - can appear in regular text)
    "←": 5, "↑": 5, "↓": 5, "↔": 5,
}

# Bulletproof question starters
PSEUDOCODE_STARTERS = [
    r"write\s+pseudocode",
    r"complete\s+the\s+pseudocode",
    r"what\s+does\s+the\s+following\s+pseudocode",
    r"trace\s+(through\s+)?the\s+pseudocode",
    r"this\s+pseudocode\s+algorithm",
    r"the\s+pseudocode\s+below",
    r"write\s+an\s+algorithm\s+in\s+pseudocode",
    r"write\s+.*algorithm",
    r"pseudocode.*procedure",
    r"pseudocode.*function",
]

# Phrases that indicate non-pseudocode questions
PSEUDOCODE_EXCLUSIONS = [
    r"declare\s+a\s+variable",
    r"describe\s+the\s+role",
    r"explain\s+how",
    r"identify\s+",
    r"list\s+",
    r"state\s+",
    r"define\s+",
    r"what\s+is\s+",
    r"name\s+",
    r"describe\s+",
]

# Compile patterns
STARTER_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PSEUDOCODE_STARTERS]
EXCLUSION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PSEUDOCODE_EXCLUSIONS]


def count_pseudocode_keywords(text: str) -> Tuple[int, int, List[str]]:
    """
    Count pseudocode keywords in text.
    Returns: (total_score, keyword_count, matched_keywords)
    """
    if not text:
        return 0, 0, []
    
    # Normalize text: uppercase for matching
    normalized = text.upper()
    
    total_score = 0
    keyword_count = 0
    matched_keywords = []
    
    # Count each keyword once per text (avoid double-counting)
    matched_set = set()
    
    for keyword, weight in PSEUDOCODE_KEYWORDS.items():
        # Use word boundary matching to avoid partial matches
        pattern = r'\b' + re.escape(keyword) + r'\b'
        matches = re.findall(pattern, normalized, re.IGNORECASE)
        
        if matches and keyword not in matched_set:
            count = len(matches)
            score = weight * count
            total_score += score
            keyword_count += count
            matched_keywords.append(f"{keyword}({count})")
            matched_set.add(keyword)
    
    return total_score, keyword_count, matched_keywords


def find_starter_match(text: str) -> Optional[str]:
    """
    Check if text matches any pseudocode starter phrase.
    Returns: matched phrase or None
    """
    if not text:
        return None
    
    # Check first 100 characters (where starters typically appear)
    start_text = text[:200].lower()
    
    for pattern in STARTER_PATTERNS:
        match = pattern.search(start_text)
        if match:
            return match.group()
    
    return None


def check_exclusion(text: str) -> bool:
    """
    Check if text matches any exclusion pattern.
    Returns: True if text should be excluded from pseudocode classification
    """
    if not text:
        return False
    
    start_text = text[:200].lower()
    
    for pattern in EXCLUSION_PATTERNS:
        if pattern.search(start_text):
            return True
    
    return False


def classify_text(text: str) -> Dict:
    """
    Classify whether a text segment is pseudocode-heavy.
    Args:
        text: Text to classify
    Returns:
        {
            "is_pseudocode": bool,
            "score": int,
            "reason": str,
            "keyword_matches": List[str],
            "starter_match": Optional[str],
            "has_exclusion": bool,
            "word_count": int
        }
    """
    if not text or not text.strip():
        return {
            "is_pseudocode": False,
            "score": 0,
            "reason": "Empty text",
            "keyword_matches": [],
            "starter_match": None,
            "has_exclusion": False,
            "word_count": 0
        }
    
    # Check for exclusions
    has_exclusion = check_exclusion(text)
    if has_exclusion:
        return {
            "is_pseudocode": False,
            "score": 0,
            "reason": "Matches non-pseudocode pattern (e.g., 'describe', 'explain')",
            "keyword_matches": [],
            "starter_match": None,
            "has_exclusion": True,
            "word_count": len(text.split())
        }
    
    # Check for starter phrase
    starter = find_starter_match(text)
    if starter:
        return {
            "is_pseudocode": True,
            "score": 100,
            "reason": f"Matches pseudocode starter: '{starter}'",
            "keyword_matches": [],
            "starter_match": starter,
            "has_exclusion": False,
            "word_count": len(text.split())
        }
    
    # Count keywords
    keyword_score, keyword_count, matched = count_pseudocode_keywords(text)
    word_count = len(text.split())
    
    # Bonus for length (pseudocode is typically longer)
    length_bonus = 5 if word_count > 200 else 0
    
    total_score = keyword_score + length_bonus
    
    # Determine if pseudocode
    # Require: 3+ keywords AND 2+ control flow keywords (IF/FOR/WHILE/PROCEDURE)
    has_control_flow = any(kw in matched for kw in 
                          ['IF(', 'FOR(', 'WHILE(', 'REPEAT(', 'DO(', 'PROCEDURE(', 'FUNCTION('])
    
    is_pseudocode = total_score >= 30 and keyword_count >= 3 and has_control_flow
    
    reason = f"{keyword_count} keywords, score={total_score}"
    if not has_control_flow and keyword_count >= 3:
        reason += " (no control flow keywords - uncertain)"
    
    return {
        "is_pseudocode": is_pseudocode,
        "score": total_score,
        "reason": reason,
        "keyword_matches": matched,
        "starter_match": None,
        "has_exclusion": False,
        "word_count": word_count
    }


def classify_question(question_data: Dict) -> Dict:
    """
    Classify a question and all its subparts.
    Args:
        question_data: Question data from extract_question_text
    Returns:
        {
            "is_pseudocode": bool (True if any part is pseudocode),
            "main": {classification result},
            "primaries": [{classification result + "marker"}],
            "secondaries_by_primary": [...]
        }
    """
    # Classify main question text
    main_classification = classify_text(question_data.get("text", ""))
    
    # Classify primaries
    primary_classifications = []
    for primary in question_data.get("primaries", []):
        p_class = classify_text(primary.get("text", ""))
        p_class["marker"] = primary.get("marker", "?")
        primary_classifications.append(p_class)
        
        # Classify secondaries within this primary
        secondaries = []
        for secondary in primary.get("secondaries", []):
            s_class = classify_text(secondary.get("text", ""))
            s_class["marker"] = secondary.get("marker", "?")
            secondaries.append(s_class)
        
        p_class["secondaries"] = secondaries
    
    # Main question is pseudocode if:
    # 1. Its own text is pseudocode, OR
    # 2. Any primary is pseudocode, OR
    # 3. Any secondary is pseudocode
    is_pseudocode = main_classification["is_pseudocode"]
    
    for primary in primary_classifications:
        if primary["is_pseudocode"]:
            is_pseudocode = True
        for secondary in primary.get("secondaries", []):
            if secondary["is_pseudocode"]:
                is_pseudocode = True
    
    return {
        "is_pseudocode": is_pseudocode,
        "main": main_classification,
        "primaries": primary_classifications
    }


def batch_classify_papers(text_data: Dict[str, Dict], output_dir: Path) -> Dict[str, Dict]:
    """
    Classify all questions across all papers.
    Args:
        text_data: {paper_code: {q_num: question_data}} from extract_question_text
        output_dir: Output directory
    Returns:
        {paper_code: {q_num: classification_result}}
    """
    results = {}
    total_papers = len(text_data)
    
    print(f"Classifying {total_papers} papers...")
    
    for idx, (paper_code, questions) in enumerate(sorted(text_data.items()), 1):
        paper_results = {}
        
        for q_num, question_data in questions.items():
            classification = classify_question(question_data)
            paper_results[q_num] = classification
        
        results[paper_code] = paper_results
        
        # Count pseudocode questions in this paper
        pseudocode_count = sum(1 for q in paper_results.values() if q["is_pseudocode"])
        print(f"  [{idx}/{total_papers}] {paper_code}: {pseudocode_count}/{len(paper_results)} pseudocode questions")
    
    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "pseudocode_classifications.json"
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nClassifications saved to {output_path}")
    
    return results


def generate_summary_report(text_data: Dict[str, Dict], classification_data: Dict[str, Dict], 
                           output_dir: Path) -> str:
    """
    Generate summary report of pseudocode classifications.
    """
    # Count statistics
    total_questions = 0
    total_pseudocode = 0
    total_pseudocode_primaries = 0
    total_pseudocode_secondaries = 0
    
    keyword_freq = {}
    
    for paper_code, papers_classes in classification_data.items():
        for q_num, classification in papers_classes.items():
            total_questions += 1
            
            if classification["is_pseudocode"]:
                total_pseudocode += 1
            
            # Count pseudocode primaries and secondaries
            for primary in classification.get("primaries", []):
                if primary["is_pseudocode"]:
                    total_pseudocode_primaries += 1
                
                # Track keywords in primary
                for kw in primary.get("keyword_matches", []):
                    kw_name = kw.split("(")[0]
                    keyword_freq[kw_name] = keyword_freq.get(kw_name, 0) + 1
                
                for secondary in primary.get("secondaries", []):
                    if secondary["is_pseudocode"]:
                        total_pseudocode_secondaries += 1
                    
                    # Track keyword frequency from secondary
                    for kw in secondary.get("keyword_matches", []):
                        kw_name = kw.split("(")[0]
                        keyword_freq[kw_name] = keyword_freq.get(kw_name, 0) + 1
            
            # Also count keywords in main
            for kw in classification.get("main", {}).get("keyword_matches", []):
                kw_name = kw.split("(")[0]
                keyword_freq[kw_name] = keyword_freq.get(kw_name, 0) + 1
    
    # Sort keywords by frequency
    top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Generate report
    report = f"""
PSEUDOCODE QUESTION CLASSIFICATION SUMMARY
==========================================

Total Questions: {total_questions}
Questions with Pseudocode Content: {total_pseudocode} ({100*total_pseudocode/total_questions:.1f}%)
  - Main question text: {classification_data.get('_stats', {}).get('main_pseudocode', 0)}
  - Primary subparts: {total_pseudocode_primaries}
  - Secondary subparts: {total_pseudocode_secondaries}

Non-pseudocode Questions: {total_questions - total_pseudocode} ({100*(total_questions - total_pseudocode)/total_questions:.1f}%)

Top 20 Pseudocode Keywords by Frequency:
{chr(10).join(f"  {kw}: {count}" for kw, count in top_keywords)}

Classification Thresholds Used:
  - Starter phrase match: +100 points (auto-classify as pseudocode)
  - Pseudocode keyword: +{PSEUDOCODE_KEYWORDS.get('FOR', 'N/A')} points (FOR/WHILE/PROCEDURE)
  - Length bonus (>200 words): +5 points
  - Overall threshold: 30+ points AND 3+ keywords AND control flow keywords present
  
Notes:
  - Control flow keywords (IF, FOR, WHILE, PROCEDURE) weighted higher than generic keywords
  - Questions/subparts with "explain", "describe", "list" starters are excluded
  - Text extracted using hybrid fitz + OCR approach
"""
    
    # Save report
    report_path = output_dir / "pseudocode_classification_report.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to {report_path}")
    
    return report


if __name__ == "__main__":
    # Load extracted text data
    input_path = Path("output/question_texts.json")
    output_dir = Path("output")
    
    if not input_path.exists():
        print(f"Error: {input_path} not found. Run extract_question_text.py first.")
        exit(1)
    
    with open(input_path) as f:
        text_data = json.load(f)
    
    # Classify
    classification_data = batch_classify_papers(text_data, output_dir)
    
    # Generate report
    generate_summary_report(text_data, classification_data, output_dir)
