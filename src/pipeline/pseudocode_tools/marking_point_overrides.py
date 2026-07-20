"""Curated marking-point overrides for a few one-off mark-scheme conventions.

Nine records in the corpus use conventions that no general parser handles
cleanly — error/correction lists, single-line answers, "one mark per gap
(boldened)", "one mark per highlighted phrase", numbered code-clause marks — and
each appears on only one or two scattered papers. Rather than add fragile
heuristics that risk the working extractor for the sake of nine records, their
marking points are transcribed by hand here and applied by ``build_final_records``
**only as a last-resort fallback**: they are used when both the text scanner and
the underlined-span recovery return nothing, so they can never override a
successful parse.

Keyed by ``(qp_paper_code, question_marker, primary_marker, secondary_marker)``
exactly as those appear in a record's ``segment_key`` (primary/secondary markers
keep their parentheses; absent markers are ``None``). Each value carries the
transcribed point texts and, where the parsed node lacked one, the mark total.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

OverrideKey = Tuple[str, Optional[str], Optional[str], Optional[str]]

# fmt: off
_OVERRIDES: Dict[OverrideKey, Dict[str, Any]] = {
    # 9608_s20_qp_21 q5(a): the record is scoped to the empty (a) container; the
    # 8-mark SortContacts procedure lives at (a)(i) and is marked "one mark per
    # highlighted phrase". Transcribed as the eight markable phrases of the
    # flag-controlled bubble sort.
    ("9608_s20_qp_21", "5", "(a)", None): {
        "max_marks": 8,
        "points": [
            "PROCEDURE SortContacts() heading and ENDPROCEDURE",
            "Declare and initialise Boundary (e.g. Boundary <- 999) and a Temp variable",
            "REPEAT ... UNTIL NoSwaps outer loop with the flag reset (NoSwaps <- TRUE) each pass",
            "FOR J <- 1 TO Boundary inner loop",
            "Extract FirstName and SecondName using RIGHT()/LENGTH()",
            "Compare IF FirstName > SecondName",
            "Swap Directory[J] and Directory[J + 1] using Temp",
            "Set NoSwaps <- FALSE on a swap and decrement Boundary each pass",
        ],
    },
    # 9608_s20_qp_23 q3(b)(ii): "one mark per line number with correction" — two
    # errors to find and correct.
    ("9608_s20_qp_23", "3", "(b)", "(ii)"): {
        "points": [
            "Line 26 correction: FOR Index <- 1 TO StrLen",
            "Line 41 correction: NumOther <- StrLen - (NumDigit + NumUpper)",
        ],
    },
    # 9608_w18_qp_23 q4(d)(ii): single-line answer, one mark.
    ("9608_w18_qp_23", "4", "(d)", "(ii)"): {
        "points": ["CONSTANT LastElement = 200"],
    },
    # 9618_s23_qp_22 q2(a): single-line answer, one mark.
    ("9618_s23_qp_22", "2", "(a)", None): {
        "points": ["MyDOB <- SETDATE(17, 11, 2007)"],
    },
    # 9618_w22_qp_21 q7(a)(ii): single-line function header, one mark.
    ("9618_w22_qp_21", "7", "(a)", "(ii)"): {
        "points": ["FUNCTION Calculate(Expression : STRING) RETURNS REAL"],
    },
    # 9618_w22_qp_22 q5: "one mark per IF...THEN...ENDIF clause" — four clauses,
    # each a code block that the bare-digit code guard rightly refuses to parse.
    ("9618_w22_qp_22", "5", None, None): {
        "points": [
            "IF A AND B AND C THEN CALL Sub1() ENDIF",
            "IF (A AND B) AND NOT C THEN CALL Sub2() ENDIF",
            "IF (NOT A) AND (NOT C) THEN CALL Sub3() ENDIF",
            "IF (NOT A) AND C THEN CALL Sub4() ENDIF",
        ],
    },
    # 9618_w22_qp_22 q7(c)(iii): single-line declaration, one mark.
    ("9618_w22_qp_22", "7", "(c)", "(iii)"): {
        "points": ["DECLARE Error : ARRAY[1:500] OF ErrorRec"],
    },
    # 9618_w24_qp_22 q3(b): "one mark per gap" — the four gaps recovered from the
    # emboldened spans of the Push() solution.
    ("9618_w24_qp_22", "3", "(b)", None): {
        "points": [
            "IF OnStack = 60 / >59 (SP outside the range 1 to 60) THEN",
            "RETURN FALSE (stack already full)",
            "ThisStack[SP] <- ThisValue",
            "SP <- SP + 1",
        ],
    },
    # 9618_w25_qp_22 q4(b): "one mark per gap (boldened)" — the five emboldened
    # gaps of the nested-loop CheckTotal solution.
    ("9618_w25_qp_22", "4", "(b)", None): {
        "points": [
            "EasyQ initialised to 0 (FOR EasyQ <- 0)",
            "EasyQ loop STEP 3",
            "HardQ upper bound 20 (TO 20)",
            "HardQ loop STEP 5",
            "Array index HardQ + EasyQ (CheckTotal[HardQ + EasyQ])",
        ],
    },
}
# fmt: on


def override_marking_points(
    paper_code: str,
    question_marker: Any,
    primary_marker: Any,
    secondary_marker: Any,
) -> Optional[Dict[str, Any]]:
    """Return {"points": [...], "max_marks": int|None} for a curated record, else None."""

    key = (
        paper_code,
        str(question_marker) if question_marker is not None else None,
        primary_marker,
        secondary_marker,
    )
    entry = _OVERRIDES.get(key)
    if entry is None:
        return None
    points: List[Dict[str, Any]] = [
        {
            "id": f"mp{index}",
            "text": text,
            "marks": 1,
            "confidence": "high",
            "style": "manual_override",
            "alt_group": 0,
        }
        for index, text in enumerate(entry["points"], start=1)
    ]
    return {"points": points, "max_marks": entry.get("max_marks")}
