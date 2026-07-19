"""Hand-authored candidate answers for grading-quality evaluation.

Fifteen questions spanning the three answer shapes in the corpus — fill-in-the-
blank, short-answer (a single construct/declaration), and long-answer (a whole
procedure/function) — each with a high / medium / low quality candidate and the
marks a competent human examiner would award against that record's marking
points. Running these through the grader (see ``__main__``) shows how closely
Qwen tracks the intended marks.

Each case is keyed by ``(paper_code, question_marker, primary_marker,
secondary_marker)`` exactly as in a record's ``segment_key`` so the runner can
match it regardless of record-id renumbering.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Each candidate: quality, the answer text, predicted marks (human ground truth),
# and a rationale naming the marking points hit/missed.
CASES: List[Dict[str, Any]] = [
    # ------------------------------------------------------------------ FILL-IN
    {
        "key": ("9608_s17_qp_21", "3", None, None),
        "type": "fill_in",
        "title": "Complete the StringClean function (remove non-alpha, lower-case)",
        "candidates": [
            {
                "quality": "high",
                "predicted": 10,
                "rationale": "All ten gradeable underlined parts present: param+return STRING, "
                "NextChar CHAR, OutString declared and initialised, LENGTH, MID, LCASE, the "
                "a..z test, concatenation, RETURN. (The bogus 'underlined' marking point is "
                "un-gradeable.)",
                "answer": (
                    "FUNCTION StringClean(InString : STRING) RETURNS STRING\n"
                    "DECLARE NextChar : CHAR\n"
                    "DECLARE OutString : STRING\n"
                    "DECLARE n : INTEGER\n"
                    "OutString ← \"\"\n"
                    "FOR n ← 1 TO LENGTH(InString)\n"
                    "    NextChar ← MID(InString, n, 1)\n"
                    "    NextChar ← LCASE(NextChar)\n"
                    "    IF NextChar >= 'a' AND NextChar <= 'z' THEN\n"
                    "        OutString ← OutString & NextChar\n"
                    "    ENDIF\n"
                    "NEXT n\n"
                    "RETURN OutString\n"
                    "ENDFUNCTION"
                ),
            },
            {
                "quality": "medium",
                "predicted": 6,
                "rationale": "OutString declared+initialised, char test, concatenation, RETURN, "
                "and MID-equivalent present, but LEN is the wrong built-in (not LENGTH), the "
                "string is indexed instead of using MID, LCASE is missing (so upper-case letters "
                "are wrongly dropped), and NextChar is not declared.",
                "answer": (
                    "FUNCTION StringClean(InString : STRING) RETURNS STRING\n"
                    "DECLARE OutString : STRING\n"
                    "OutString ← \"\"\n"
                    "FOR n ← 1 TO LEN(InString)\n"
                    "    IF InString[n] >= 'a' AND InString[n] <= 'z' THEN\n"
                    "        OutString ← OutString & InString[n]\n"
                    "    ENDIF\n"
                    "NEXT n\n"
                    "RETURN OutString\n"
                    "ENDFUNCTION"
                ),
            },
            {
                "quality": "low",
                "predicted": 1,
                "rationale": "Only the function heading resembles the answer; no cleaning logic, "
                "no loop, no built-ins.",
                "answer": (
                    "FUNCTION StringClean(InString) RETURNS STRING\n"
                    "OUTPUT InString\n"
                    "RETURN InString\n"
                    "ENDFUNCTION"
                ),
            },
        ],
    },
    {
        "key": ("9608_s17_qp_21", "4", "(b)", None),
        "type": "fill_in",
        "title": "Write the function header for the Card payment module",
        "candidates": [
            {
                "quality": "high",
                "predicted": 3,
                "rationale": "Function name + both correctly typed parameters (REAL, STRING) and "
                "RETURNS BOOLEAN — all three underlined parts.",
                "answer": "FUNCTION CardPayment(ParamA : REAL, ParamB : STRING) RETURNS BOOLEAN",
            },
            {
                "quality": "medium",
                "predicted": 2,
                "rationale": "Name and typed parameters correct, but the RETURNS BOOLEAN is missing.",
                "answer": "FUNCTION CardPayment(ParamA : REAL, ParamB : STRING)",
            },
            {
                "quality": "low",
                "predicted": 1,
                "rationale": "Function name present but parameters are untyped and there is no "
                "return type.",
                "answer": "FUNCTION CardPayment(A, B)",
            },
        ],
    },
    {
        "key": ("9608_s17_qp_22", "5", "(a)", "(ii)"),
        "type": "fill_in",
        "title": "Declare LogArray (up to 20 log entries)",
        "candidates": [
            {
                "quality": "high",
                "predicted": 2,
                "rationale": "Correct array bounds ARRAY[1:20] and element type STRING.",
                "answer": "DECLARE LogArray : ARRAY[1:20] OF STRING",
            },
            {
                "quality": "medium",
                "predicted": 1,
                "rationale": "Array declared with correct bounds, but the element type is wrong "
                "(INTEGER, not STRING).",
                "answer": "DECLARE LogArray : ARRAY[1:20] OF INTEGER",
            },
            {
                "quality": "low",
                "predicted": 0,
                "rationale": "Not declared as an array at all.",
                "answer": "DECLARE LogArray : STRING",
            },
        ],
    },
    {
        "key": ("9618_s23_qp_21", "2", "(b)", None),
        "type": "fill_in",
        "title": "Declare StartDate and assign the date 15/11/2005",
        "candidates": [
            {
                "quality": "high",
                "predicted": 3,
                "rationale": "DECLARE StartDate, type DATE, and assignment via SETDATE(15, 11, 2005).",
                "answer": (
                    "DECLARE StartDate : DATE\n"
                    "StartDate ← SETDATE(15, 11, 2005)"
                ),
            },
            {
                "quality": "medium",
                "predicted": 2,
                "rationale": "Declaration name and DATE type correct, but the assignment uses a "
                "string literal instead of SETDATE.",
                "answer": (
                    "DECLARE StartDate : DATE\n"
                    "StartDate ← \"15/11/2005\""
                ),
            },
            {
                "quality": "low",
                "predicted": 1,
                "rationale": "Only the variable name is right; the type is STRING not DATE and no "
                "SETDATE is used.",
                "answer": (
                    "DECLARE StartDate : STRING\n"
                    "StartDate ← \"15/11/2005\""
                ),
            },
        ],
    },
    {
        "key": ("9618_w24_qp_23", "4", "(a)", None),
        "type": "fill_in",
        "title": "Complete the paper-checking loop (four blanks)",
        "candidates": [
            {
                "quality": "high",
                "predicted": 4,
                "rationale": "FOR upper bound 5, Upper ← GB[Index] + 2, and both boundary tests "
                "(Mark >= Lower AND Mark <= Upper).",
                "answer": (
                    "FOR Index ← 1 TO 5\n"
                    "Lower ← GB[Index] - 2\n"
                    "Upper ← GB[Index] + 2\n"
                    "IF Mark >= Lower AND Mark <= Upper THEN\n"
                    "OUTPUT \"Check this paper\"\n"
                    "ENDIF\n"
                    "NEXT Index"
                ),
            },
            {
                "quality": "medium",
                "predicted": 2,
                "rationale": "FOR bound 5 and Upper expression correct, but the comparisons use "
                "strict > / < so the boundary values are excluded (wrong operators).",
                "answer": (
                    "FOR Index ← 1 TO 5\n"
                    "Lower ← GB[Index] - 2\n"
                    "Upper ← GB[Index] + 2\n"
                    "IF Mark > Lower AND Mark < Upper THEN\n"
                    "OUTPUT \"Check this paper\"\n"
                    "ENDIF\n"
                    "NEXT Index"
                ),
            },
            {
                "quality": "low",
                "predicted": 1,
                "rationale": "Only the FOR upper bound is right; Upper is left as GB[Index] and "
                "the single test is wrong.",
                "answer": (
                    "FOR Index ← 1 TO 5\n"
                    "Lower ← GB[Index] - 2\n"
                    "Upper ← GB[Index]\n"
                    "IF Mark = Lower THEN\n"
                    "OUTPUT \"Check this paper\"\n"
                    "ENDIF\n"
                    "NEXT Index"
                ),
            },
        ],
    },
    # --------------------------------------------------------------- SHORT ANSWER
    {
        "key": ("9608_w19_qp_22", "3", "(a)", None),
        "type": "short",
        "title": "Declare Result array and initialise all elements to zero",
        "candidates": [
            {
                "quality": "high",
                "predicted": 3,
                "rationale": "Array of 10 INTEGERs declared, a loop over all elements, and the "
                "zero assignment inside the loop.",
                "answer": (
                    "DECLARE Result : ARRAY[0:9] OF INTEGER\n"
                    "DECLARE Index : INTEGER\n"
                    "FOR Index ← 0 TO 9\n"
                    "    Result[Index] ← 0\n"
                    "NEXT Index"
                ),
            },
            {
                "quality": "medium",
                "predicted": 2,
                "rationale": "Correct declaration and a zero assignment, but no loop (only one "
                "element initialised).",
                "answer": (
                    "DECLARE Result : ARRAY[0:9] OF INTEGER\n"
                    "Result[0] ← 0"
                ),
            },
            {
                "quality": "low",
                "predicted": 1,
                "rationale": "Only the array declaration is present; no initialisation.",
                "answer": "DECLARE Result : ARRAY[0:9] OF INTEGER",
            },
        ],
    },
    {
        "key": ("9618_s24_qp_22", "3", "(a)", "(i)"),
        "type": "short",
        "title": "Declare the record structure for type Component",
        "candidates": [
            {
                "quality": "high",
                "predicted": 4,
                "rationale": "TYPE/ENDTYPE, Item_Num + Reject fields, Stage field, and both Limit "
                "fields as REAL — all four marks.",
                "answer": (
                    "TYPE Component\n"
                    "DECLARE Item_Num : INTEGER\n"
                    "DECLARE Reject : BOOLEAN\n"
                    "DECLARE Stage : CHAR\n"
                    "DECLARE Limit_1 : REAL\n"
                    "DECLARE Limit_2 : REAL\n"
                    "ENDTYPE"
                ),
            },
            {
                "quality": "medium",
                "predicted": 2,
                "rationale": "TYPE/ENDTYPE present and Item_Num/Reject correct, but Stage is the "
                "wrong type and the Limit fields are INTEGER not REAL.",
                "answer": (
                    "TYPE Component\n"
                    "DECLARE Item_Num : INTEGER\n"
                    "DECLARE Reject : BOOLEAN\n"
                    "DECLARE Stage : STRING\n"
                    "DECLARE Limit_1 : INTEGER\n"
                    "DECLARE Limit_2 : INTEGER\n"
                    "ENDTYPE"
                ),
            },
            {
                "quality": "low",
                "predicted": 1,
                "rationale": "Only the TYPE/ENDTYPE wrapper is right; fields are missing/placeholder.",
                "answer": (
                    "TYPE Component\n"
                    "DECLARE Data : STRING\n"
                    "ENDTYPE"
                ),
            },
        ],
    },
    {
        "key": ("9618_s24_qp_23", "3", "(a)", "(i)"),
        "type": "short",
        "title": "Clause to check a component weight is within range",
        "candidates": [
            {
                "quality": "high",
                "predicted": 3,
                "rationale": "Correct record reference Batch[ThisIndex].Weight and both boundary "
                "checks combined with AND.",
                "answer": (
                    "IF Batch[ThisIndex].Weight >= Min AND Batch[ThisIndex].Weight <= Max THEN\n"
                    "    OUTPUT \"In range\"\n"
                    "ENDIF"
                ),
            },
            {
                "quality": "medium",
                "predicted": 2,
                "rationale": "Correct reference and one valid boundary, but the second boundary "
                "uses the wrong operator (> Max instead of <= Max) with AND, so it never holds.",
                "answer": (
                    "IF Batch[ThisIndex].Weight >= Min AND Batch[ThisIndex].Weight > Max THEN\n"
                    "    OUTPUT \"In range\"\n"
                    "ENDIF"
                ),
            },
            {
                "quality": "low",
                "predicted": 1,
                "rationale": "References the weight but checks a single bound only and omits the "
                "record/array indexing.",
                "answer": (
                    "IF Weight >= Min THEN\n"
                    "    OUTPUT \"In range\"\n"
                    "ENDIF"
                ),
            },
        ],
    },
    {
        "key": ("9618_w24_qp_22", "5", "(c)", None),
        "type": "short",
        "title": "Rewrite a CASE construct as a single IF (no CASE)",
        "candidates": [
            {
                "quality": "high",
                "predicted": 2,
                "rationale": "Correct IF...THEN...ELSE...ENDIF and both assignments with the right "
                "even/odd test.",
                "answer": (
                    "IF Index MOD 2 = 0 THEN\n"
                    "    ReturnValue ← TO_UPPER(RIGHT(Label, Count))\n"
                    "ELSE\n"
                    "    ReturnValue ← \"****\"\n"
                    "ENDIF"
                ),
            },
            {
                "quality": "medium",
                "predicted": 1,
                "rationale": "Correct IF/ELSE structure but the test is wrong (= 1) and the "
                "branches are swapped, so only the construct mark is earned.",
                "answer": (
                    "IF Index MOD 2 = 1 THEN\n"
                    "    ReturnValue ← \"****\"\n"
                    "ELSE\n"
                    "    ReturnValue ← TO_UPPER(Label)\n"
                    "ENDIF"
                ),
            },
            {
                "quality": "low",
                "predicted": 0,
                "rationale": "Still a CASE construct — the question explicitly forbids it.",
                "answer": (
                    "CASE OF Index MOD 2\n"
                    "    0 : ReturnValue ← TO_UPPER(RIGHT(Label, Count))\n"
                    "    1 : ReturnValue ← \"****\"\n"
                    "ENDCASE"
                ),
            },
        ],
    },
    {
        "key": ("9618_w25_qp_21", "3", "(a)", "(i)"),
        "type": "short",
        "title": "Declare the record structure for type RentalRecord",
        "candidates": [
            {
                "quality": "high",
                "predicted": 4,
                "rationale": "TYPE/ENDTYPE plus all six fields correctly typed (RentalID+CarID, "
                "DisCode+Start, Duration+Completed).",
                "answer": (
                    "TYPE RentalRecord\n"
                    "DECLARE RentalID : STRING\n"
                    "DECLARE CarID : INTEGER\n"
                    "DECLARE DisCode : CHAR\n"
                    "DECLARE Start : DATE\n"
                    "DECLARE Duration : INTEGER\n"
                    "DECLARE Completed : BOOLEAN\n"
                    "ENDTYPE"
                ),
            },
            {
                "quality": "medium",
                "predicted": 2,
                "rationale": "TYPE/ENDTYPE and the first pair correct, but Start is STRING not DATE "
                "and Completed is CHAR not BOOLEAN.",
                "answer": (
                    "TYPE RentalRecord\n"
                    "DECLARE RentalID : STRING\n"
                    "DECLARE CarID : INTEGER\n"
                    "DECLARE DisCode : CHAR\n"
                    "DECLARE Start : STRING\n"
                    "DECLARE Duration : INTEGER\n"
                    "DECLARE Completed : CHAR\n"
                    "ENDTYPE"
                ),
            },
            {
                "quality": "low",
                "predicted": 1,
                "rationale": "Only the TYPE/ENDTYPE wrapper is correct; fields are missing.",
                "answer": (
                    "TYPE RentalRecord\n"
                    "DECLARE RentalID : STRING\n"
                    "ENDTYPE"
                ),
            },
        ],
    },
    # ---------------------------------------------------------------- LONG ANSWER
    {
        "key": ("9608_s18_qp_22", "6", "(b)", None),
        "type": "long",
        "title": "Procedure Flip() to reflect a 5x8 image horizontally",
        "candidates": [
            {
                "quality": "high",
                "predicted": 8,
                "rationale": "Heading/ending, loop counters, temp variable, nested loops with "
                "correct 1..5 / 1..4 iterations, swap via temp, and correct source/destination "
                "column indexing (j and 9-j).",
                "answer": (
                    "PROCEDURE Flip()\n"
                    "DECLARE temp : INTEGER\n"
                    "DECLARE i : INTEGER\n"
                    "DECLARE j : INTEGER\n"
                    "FOR i ← 1 TO 5\n"
                    "    FOR j ← 1 TO 4\n"
                    "        temp ← Picture[i, j]\n"
                    "        Picture[i, j] ← Picture[i, 9 - j]\n"
                    "        Picture[i, 9 - j] ← temp\n"
                    "    NEXT j\n"
                    "NEXT i\n"
                    "ENDPROCEDURE"
                ),
            },
            {
                "quality": "medium",
                "predicted": 5,
                "rationale": "Heading/ending, counters, temp, and a nested-loop swap, but the "
                "inner loop runs 1..8 so every pixel is swapped twice (image ends unchanged) — "
                "wrong iteration count and destination selection.",
                "answer": (
                    "PROCEDURE Flip()\n"
                    "DECLARE temp : INTEGER\n"
                    "DECLARE i : INTEGER\n"
                    "DECLARE j : INTEGER\n"
                    "FOR i ← 1 TO 5\n"
                    "    FOR j ← 1 TO 8\n"
                    "        temp ← Picture[i, j]\n"
                    "        Picture[i, j] ← Picture[i, 9 - j]\n"
                    "        Picture[i, 9 - j] ← temp\n"
                    "    NEXT j\n"
                    "NEXT i\n"
                    "ENDPROCEDURE"
                ),
            },
            {
                "quality": "low",
                "predicted": 2,
                "rationale": "Correct heading/ending and a nested loop, but no temp and the "
                "assignment overwrites data instead of swapping.",
                "answer": (
                    "PROCEDURE Flip()\n"
                    "DECLARE i : INTEGER\n"
                    "DECLARE j : INTEGER\n"
                    "FOR i ← 1 TO 5\n"
                    "    FOR j ← 1 TO 8\n"
                    "        Picture[i, j] ← Picture[i, 9 - j]\n"
                    "    NEXT j\n"
                    "NEXT i\n"
                    "ENDPROCEDURE"
                ),
            },
        ],
    },
    {
        "key": ("9608_s18_qp_23", "6", "(b)", None),
        "type": "long",
        "title": "Function Clip(MaxVal) clamps pixels and returns whether any changed",
        "candidates": [
            {
                "quality": "high",
                "predicted": 9,
                "rationale": "Function heading with MaxVal returning BOOLEAN, flag declared and "
                "initialised FALSE, loop counters, nested 1..8 loops, access + compare element, "
                "clamp to MaxVal, set flag, and RETURN flag after loops.",
                "answer": (
                    "FUNCTION Clip(MaxVal : INTEGER) RETURNS BOOLEAN\n"
                    "DECLARE i : INTEGER\n"
                    "DECLARE j : INTEGER\n"
                    "DECLARE ClipFlag : BOOLEAN\n"
                    "ClipFlag ← FALSE\n"
                    "FOR i ← 1 TO 8\n"
                    "    FOR j ← 1 TO 8\n"
                    "        IF Picture[i, j] > MaxVal THEN\n"
                    "            Picture[i, j] ← MaxVal\n"
                    "            ClipFlag ← TRUE\n"
                    "        ENDIF\n"
                    "    NEXT j\n"
                    "NEXT i\n"
                    "RETURN ClipFlag\n"
                    "ENDFUNCTION"
                ),
            },
            {
                "quality": "medium",
                "predicted": 6,
                "rationale": "Heading, counters, nested loops, access, compare and clamp present, "
                "but the flag is never declared/initialised or set, and RETURN is missing — the "
                "return-value marks are lost.",
                "answer": (
                    "FUNCTION Clip(MaxVal : INTEGER) RETURNS BOOLEAN\n"
                    "DECLARE i : INTEGER\n"
                    "DECLARE j : INTEGER\n"
                    "FOR i ← 1 TO 8\n"
                    "    FOR j ← 1 TO 8\n"
                    "        IF Picture[i, j] > MaxVal THEN\n"
                    "            Picture[i, j] ← MaxVal\n"
                    "        ENDIF\n"
                    "    NEXT j\n"
                    "NEXT i\n"
                    "ENDFUNCTION"
                ),
            },
            {
                "quality": "low",
                "predicted": 2,
                "rationale": "Heading and a single loop only; no nesting, no per-element compare, "
                "no flag, no return.",
                "answer": (
                    "FUNCTION Clip(MaxVal : INTEGER) RETURNS BOOLEAN\n"
                    "DECLARE i : INTEGER\n"
                    "FOR i ← 1 TO 8\n"
                    "    OUTPUT Picture[i]\n"
                    "NEXT i\n"
                    "ENDFUNCTION"
                ),
            },
        ],
    },
    {
        "key": ("9608_s19_qp_21", "5", "(b)", None),
        "type": "long",
        "title": "Procedure TestRand() — count RAND calls to generate all of 1..50",
        "candidates": [
            {
                "quality": "high",
                "predicted": 8,
                "rationale": "Array of 50 declared, initialise loop, conditional loop until all "
                "found, random 1..50 in loop, count each call, check if already generated, record "
                "new ones, and output the total after the loop.",
                "answer": (
                    "PROCEDURE TestRand()\n"
                    "DECLARE MyArray : ARRAY[1:50] OF BOOLEAN\n"
                    "DECLARE Attempts : INTEGER\n"
                    "DECLARE NumFound : INTEGER\n"
                    "DECLARE ThisRndNumber : INTEGER\n"
                    "DECLARE Index : INTEGER\n"
                    "FOR Index ← 1 TO 50\n"
                    "    MyArray[Index] ← FALSE\n"
                    "NEXT Index\n"
                    "NumFound ← 0\n"
                    "Attempts ← 0\n"
                    "WHILE NumFound < 50\n"
                    "    ThisRndNumber ← 1 + INT(RAND(50))\n"
                    "    Attempts ← Attempts + 1\n"
                    "    IF MyArray[ThisRndNumber] = FALSE THEN\n"
                    "        MyArray[ThisRndNumber] ← TRUE\n"
                    "        NumFound ← NumFound + 1\n"
                    "    ENDIF\n"
                    "ENDWHILE\n"
                    "OUTPUT \"Number of calls to RAND() was \", Attempts\n"
                    "ENDPROCEDURE"
                ),
            },
            {
                "quality": "medium",
                "predicted": 4,
                "rationale": "Array + initialise loop, a conditional loop, random in range, and "
                "output present, but no counting of calls and no 'already generated' check, so "
                "the loop is really just counting iterations and can terminate early.",
                "answer": (
                    "PROCEDURE TestRand()\n"
                    "DECLARE MyArray : ARRAY[1:50] OF BOOLEAN\n"
                    "DECLARE NumFound : INTEGER\n"
                    "DECLARE ThisRndNumber : INTEGER\n"
                    "DECLARE Index : INTEGER\n"
                    "FOR Index ← 1 TO 50\n"
                    "    MyArray[Index] ← FALSE\n"
                    "NEXT Index\n"
                    "NumFound ← 0\n"
                    "WHILE NumFound < 50\n"
                    "    ThisRndNumber ← 1 + INT(RAND(50))\n"
                    "    NumFound ← NumFound + 1\n"
                    "ENDWHILE\n"
                    "OUTPUT \"Done\"\n"
                    "ENDPROCEDURE"
                ),
            },
            {
                "quality": "low",
                "predicted": 1,
                "rationale": "Generates one random number and outputs it; no array, no loop to "
                "cover all values, no counting.",
                "answer": (
                    "PROCEDURE TestRand()\n"
                    "DECLARE ThisRndNumber : INTEGER\n"
                    "ThisRndNumber ← 1 + INT(RAND(50))\n"
                    "OUTPUT ThisRndNumber\n"
                    "ENDPROCEDURE"
                ),
            },
        ],
    },
    {
        "key": ("9618_s25_qp_21", "7", "(b)", "(i)"),
        "type": "long",
        "title": "Procedure AddNewCustomers() — append new customers to a file",
        "candidates": [
            {
                "quality": "high",
                "predicted": 8,
                "rationale": "Variables typed, read the file to EOF and close, reopen for append "
                "and close, extract last CustomerID and convert to integer, count-controlled loop "
                "for NumToAdd, increment + output the new ID, build the line and write it.",
                "answer": (
                    "PROCEDURE AddNewCustomers(NumToAdd : INTEGER)\n"
                    "DECLARE CustomerID : INTEGER\n"
                    "DECLARE Count : INTEGER\n"
                    "DECLARE Line : STRING\n"
                    "DECLARE NewLine : STRING\n"
                    "OPENFILE \"Loyalty.txt\" FOR READ\n"
                    "WHILE NOT EOF(\"Loyalty.txt\")\n"
                    "    READFILE \"Loyalty.txt\", Line\n"
                    "ENDWHILE\n"
                    "CLOSEFILE \"Loyalty.txt\"\n"
                    "CustomerID ← STR_TO_NUM(LEFT(Line, 6))\n"
                    "OPENFILE \"Loyalty.txt\" FOR APPEND\n"
                    "FOR Count ← 1 TO NumToAdd\n"
                    "    CustomerID ← CustomerID + 1\n"
                    "    OUTPUT CustomerID\n"
                    "    NewLine ← NUM_TO_STR(CustomerID) & \",0\"\n"
                    "    WRITEFILE \"Loyalty.txt\", NewLine\n"
                    "NEXT Count\n"
                    "CLOSEFILE \"Loyalty.txt\"\n"
                    "ENDPROCEDURE"
                ),
            },
            {
                "quality": "medium",
                "predicted": 4,
                "rationale": "Variables declared, reads to EOF and closes, and a count-controlled "
                "loop that writes lines — but it never reopens in APPEND (overwrites / reads and "
                "writes the same open mode), and the last CustomerID is not extracted, so IDs are "
                "wrong.",
                "answer": (
                    "PROCEDURE AddNewCustomers(NumToAdd : INTEGER)\n"
                    "DECLARE CustomerID : INTEGER\n"
                    "DECLARE Count : INTEGER\n"
                    "DECLARE Line : STRING\n"
                    "OPENFILE \"Loyalty.txt\" FOR READ\n"
                    "WHILE NOT EOF(\"Loyalty.txt\")\n"
                    "    READFILE \"Loyalty.txt\", Line\n"
                    "ENDWHILE\n"
                    "CLOSEFILE \"Loyalty.txt\"\n"
                    "CustomerID ← 0\n"
                    "FOR Count ← 1 TO NumToAdd\n"
                    "    CustomerID ← CustomerID + 1\n"
                    "    WRITEFILE \"Loyalty.txt\", NUM_TO_STR(CustomerID)\n"
                    "NEXT Count\n"
                    "ENDPROCEDURE"
                ),
            },
            {
                "quality": "low",
                "predicted": 1,
                "rationale": "Heading and variable declarations only; no file handling and no loop "
                "to add customers.",
                "answer": (
                    "PROCEDURE AddNewCustomers(NumToAdd : INTEGER)\n"
                    "DECLARE CustomerID : INTEGER\n"
                    "OUTPUT \"Adding customers\"\n"
                    "ENDPROCEDURE"
                ),
            },
        ],
    },
    {
        "key": ("9608_s19_qp_23", "6", "(b)", None),
        "type": "long",
        "title": "Function ProcessArray() — build contact file, count missing numbers",
        "candidates": [
            {
                "quality": "high",
                "predicted": 9,
                "rationale": "Header returning INTEGER + ending, count declared and initialised, "
                "FOR over 40 elements, skip blanks, SearchFile and store result, add '*No number' "
                "when empty and increment count, CALL AddToFile, RETURN count after the loop.",
                "answer": (
                    "FUNCTION ProcessArray() RETURNS INTEGER\n"
                    "DECLARE NoTelNumber : INTEGER\n"
                    "DECLARE Index : INTEGER\n"
                    "DECLARE ThisName : STRING\n"
                    "DECLARE StudentData : STRING\n"
                    "NoTelNumber ← 0\n"
                    "FOR Index ← 1 TO 40\n"
                    "    ThisName ← ClassList[Index]\n"
                    "    IF ThisName <> \"\" THEN\n"
                    "        StudentData ← SearchFile(ThisName)\n"
                    "        IF StudentData = \"\" THEN\n"
                    "            StudentData ← ThisName & \"*No number\"\n"
                    "            NoTelNumber ← NoTelNumber + 1\n"
                    "        ENDIF\n"
                    "        CALL AddToFile(StudentData, \"ClassContact.txt\")\n"
                    "    ENDIF\n"
                    "NEXT Index\n"
                    "RETURN NoTelNumber\n"
                    "ENDFUNCTION"
                ),
            },
            {
                "quality": "medium",
                "predicted": 5,
                "rationale": "Header/return, count init, FOR over 40, SearchFile used and "
                "AddToFile called, and RETURN — but blanks are not skipped and the empty-result "
                "case (add '*No number' + increment count) is missing.",
                "answer": (
                    "FUNCTION ProcessArray() RETURNS INTEGER\n"
                    "DECLARE NoTelNumber : INTEGER\n"
                    "DECLARE Index : INTEGER\n"
                    "DECLARE ThisName : STRING\n"
                    "DECLARE StudentData : STRING\n"
                    "NoTelNumber ← 0\n"
                    "FOR Index ← 1 TO 40\n"
                    "    ThisName ← ClassList[Index]\n"
                    "    StudentData ← SearchFile(ThisName)\n"
                    "    CALL AddToFile(StudentData, \"ClassContact.txt\")\n"
                    "NEXT Index\n"
                    "RETURN NoTelNumber\n"
                    "ENDFUNCTION"
                ),
            },
            {
                "quality": "low",
                "predicted": 2,
                "rationale": "Header/return and a FOR over the array only; no SearchFile, no "
                "AddToFile, no missing-number handling.",
                "answer": (
                    "FUNCTION ProcessArray() RETURNS INTEGER\n"
                    "DECLARE Index : INTEGER\n"
                    "FOR Index ← 1 TO 40\n"
                    "    OUTPUT ClassList[Index]\n"
                    "NEXT Index\n"
                    "RETURN 0\n"
                    "ENDFUNCTION"
                ),
            },
        ],
    },
]
