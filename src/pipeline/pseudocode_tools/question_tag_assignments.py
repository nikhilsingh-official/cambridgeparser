"""Syllabus tags for every pseudocode-writing question record, assigned by hand.

Each record carries 4-5 tags drawn from :mod:`syllabus_tags`, chosen by reading
the question, the surrounding context, and the mark scheme together: the tags
describe what the candidate is asked to *write*, not just the words in the
prompt. A question whose stem says only "Write pseudocode for module X()" is
tagged from the module description and the mark points, which is where the
actual concepts live.

Tagging notes:

- A subpart is tagged for what that subpart asks. Where the subpart is a
  one-line declaration, the scenario it sits in supplies the remaining tags, so
  a two-mark array declaration inside a file-handling question keeps
  ``text-files`` --- that is the topic a student revising would find it under.
- Question variants that Cambridge repeats verbatim across the 11/12/13 and
  21/22/23 papers of a series get identical tags, by construction.
- ``built-in-functions`` marks any solution that must call a library routine
  from the pseudocode guide (LENGTH, MID, INT, RAND, DIV/MOD, the DATE
  functions); ``string-handling`` is reserved for the substring/concatenation
  work itself.

Keyed by ``(qp_paper_code, question_marker, primary_marker, secondary_marker)``
exactly as those appear in a record's ``segment_key``, matching the convention
in :mod:`marking_point_overrides`. Keying by segment rather than by record id
keeps the assignments correct when ``build_final_records`` renumbers records.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .syllabus_tags import validate_tags

TagKey = Tuple[str, Optional[str], Optional[str], Optional[str]]

# fmt: off
_TAGS: Dict[TagKey, Tuple[str, ...]] = {
    # 9608_s16_qp_21 Q2 (b) [6 marks]
    ("9608_s16_qp_21", "2", "(b)", None): ("structured-english", "input-output", "selection-if", "variables-constants", "operators-expressions"),
    # 9608_s16_qp_21 Q3 (a) [10 marks]
    ("9608_s16_qp_21", "3", "(a)", None): ("functions", "string-handling", "arrays-1d", "count-controlled-loop", "built-in-functions"),
    # 9608_s16_qp_22 Q2 (b) [6 marks]
    ("9608_s16_qp_22", "2", "(b)", None): ("structured-english", "input-output", "selection-if", "variables-constants", "operators-expressions"),
    # 9608_s16_qp_22 Q3 (a) [10 marks]
    ("9608_s16_qp_22", "3", "(a)", None): ("functions", "string-handling", "arrays-1d", "count-controlled-loop", "built-in-functions"),
    # 9608_s17_qp_21 Q1 (c) [4 marks]
    ("9608_s17_qp_21", "1", "(c)", None): ("pre-condition-loop", "variables-constants", "input-output", "operators-expressions"),
    # 9608_s17_qp_21 Q3 [11 marks]
    ("9608_s17_qp_21", "3", None, None): ("functions", "string-handling", "built-in-functions", "count-controlled-loop", "selection-if"),
    # 9608_s17_qp_21 Q4 (b) [3 marks]
    ("9608_s17_qp_21", "4", "(b)", None): ("structure-chart", "functions", "parameters", "data-types"),
    # 9608_s17_qp_22 Q1 (c) [4 marks]
    ("9608_s17_qp_22", "1", "(c)", None): ("post-condition-loop", "variables-constants", "input-output", "operators-expressions"),
    # 9608_s17_qp_22 Q3 [11 marks]
    ("9608_s17_qp_22", "3", None, None): ("functions", "string-handling", "built-in-functions", "count-controlled-loop", "selection-if"),
    # 9608_s17_qp_22 Q5 (a) (ii) [2 marks]
    ("9608_s17_qp_22", "5", "(a)", "(ii)"): ("arrays-1d", "data-types", "variables-constants", "text-files"),
    # 9608_s17_qp_23 Q1 (c) [4 marks]
    ("9608_s17_qp_23", "1", "(c)", None): ("pre-condition-loop", "variables-constants", "input-output", "operators-expressions"),
    # 9608_s17_qp_23 Q3 [11 marks]
    ("9608_s17_qp_23", "3", None, None): ("functions", "string-handling", "built-in-functions", "count-controlled-loop", "selection-if"),
    # 9608_s17_qp_23 Q4 (b) [3 marks]
    ("9608_s17_qp_23", "4", "(b)", None): ("structure-chart", "functions", "parameters", "data-types"),
    # 9608_s18_qp_21 Q6 (b) [8 marks]
    ("9608_s18_qp_21", "6", "(b)", None): ("arrays-2d", "nested-loops", "functions", "selection-if", "built-in-functions"),
    # 9608_s18_qp_22 Q6 (b) [8 marks]
    ("9608_s18_qp_22", "6", "(b)", None): ("arrays-2d", "nested-loops", "procedures", "array-processing", "variables-constants"),
    # 9608_s18_qp_23 Q2 (c) (ii) [4 marks]
    ("9608_s18_qp_23", "2", "(c)", "(ii)"): ("selection-case", "selection-if", "logic-statements", "variables-constants"),
    # 9608_s18_qp_23 Q6 (b) [9 marks]
    ("9608_s18_qp_23", "6", "(b)", None): ("arrays-2d", "nested-loops", "functions", "parameters", "selection-if"),
    # 9608_s19_qp_21 Q3 (a) [7 marks]
    ("9608_s19_qp_21", "3", "(a)", None): ("structured-english", "arrays-1d", "array-processing", "count-controlled-loop", "selection-if"),
    # 9608_s19_qp_21 Q4 (b) [4 marks]
    ("9608_s19_qp_21", "4", "(b)", None): ("arrays-2d", "nested-loops", "array-processing", "variables-constants"),
    # 9608_s19_qp_21 Q5 (b) [8 marks]
    ("9608_s19_qp_21", "5", "(b)", None): ("procedures", "built-in-functions", "arrays-1d", "pre-condition-loop", "selection-if"),
    # 9608_s19_qp_22 Q3 (a) (i) [3 marks]
    ("9608_s19_qp_22", "3", "(a)", "(i)"): ("structure-chart", "procedures", "parameters", "data-types"),
    # 9608_s19_qp_22 Q3 (a) (ii) [3 marks]
    ("9608_s19_qp_22", "3", "(a)", "(ii)"): ("structure-chart", "functions", "parameters", "data-types"),
    # 9608_s19_qp_22 Q5 (b) [6 marks]
    ("9608_s19_qp_22", "5", "(b)", None): ("text-files", "procedures", "parameters", "pre-condition-loop", "input-output"),
    # 9608_s19_qp_22 Q6 (c) [3 marks]
    ("9608_s19_qp_22", "6", "(c)", None): ("functions", "parameters", "data-types", "decomposition", "text-files"),
    # 9608_s19_qp_23 Q4 (a) [4 marks]
    ("9608_s19_qp_23", "4", "(a)", None): ("arrays-1d", "count-controlled-loop", "input-output", "variables-constants"),
    # 9608_s19_qp_23 Q6 (b) [9 marks]
    ("9608_s19_qp_23", "6", "(b)", None): ("functions", "arrays-1d", "count-controlled-loop", "selection-if", "text-files"),
    # 9608_s20_qp_21 Q2 (b) (ii) [2 marks]
    ("9608_s20_qp_21", "2", "(b)", "(ii)"): ("error-correction", "selection-if", "logic-statements", "string-handling"),
    # 9608_s20_qp_21 Q5 (a) [8 marks]
    ("9608_s20_qp_21", "5", "(a)", None): ("bubble-sort", "arrays-1d", "procedures", "post-condition-loop", "string-handling"),
    # 9608_s20_qp_21 Q6 (a) [8 marks]
    ("9608_s20_qp_21", "6", "(a)", None): ("procedures", "arrays-1d", "count-controlled-loop", "selection-if", "input-output"),
    # 9608_s20_qp_22 Q4 (a) [6 marks]
    ("9608_s20_qp_22", "4", "(a)", None): ("arrays-1d", "built-in-functions", "post-condition-loop", "linear-search", "nested-loops"),
    # 9608_s20_qp_22 Q6 (a) (i) [8 marks]
    ("9608_s20_qp_22", "6", "(a)", "(i)"): ("functions", "string-handling", "built-in-functions", "parameters", "operators-expressions"),
    # 9608_s20_qp_23 Q2 (b) (i) [3 marks]
    ("9608_s20_qp_23", "2", "(b)", "(i)"): ("structure-chart", "functions", "parameters", "data-types"),
    # 9608_s20_qp_23 Q2 (b) (ii) [3 marks]
    ("9608_s20_qp_23", "2", "(b)", "(ii)"): ("structure-chart", "procedures", "parameters", "data-types"),
    # 9608_s20_qp_23 Q2 (c) [5 marks]
    ("9608_s20_qp_23", "2", "(c)", None): ("structured-english", "arrays-2d", "count-controlled-loop", "selection-if", "array-processing"),
    # 9608_s20_qp_23 Q3 (b) (ii) [2 marks]
    ("9608_s20_qp_23", "3", "(b)", "(ii)"): ("error-correction", "string-handling", "count-controlled-loop", "validation", "operators-expressions"),
    # 9608_s20_qp_23 Q5 (a) [8 marks]
    ("9608_s20_qp_23", "5", "(a)", None): ("text-files", "functions", "pre-condition-loop", "string-handling", "linear-search"),
    # 9608_s20_qp_23 Q5 (b) (i) [8 marks]
    ("9608_s20_qp_23", "5", "(b)", "(i)"): ("text-files", "functions", "string-handling", "pre-condition-loop", "selection-if"),
    # 9608_w17_qp_21 Q1 (c) [4 marks]
    ("9608_w17_qp_21", "1", "(c)", None): ("selection-case", "selection-if", "procedures", "input-output"),
    # 9608_w17_qp_21 Q3 (a) [8 marks]
    ("9608_w17_qp_21", "3", "(a)", None): ("bubble-sort", "arrays-1d", "procedures", "post-condition-loop", "nested-loops"),
    # 9608_w17_qp_21 Q5 (a) [8 marks]
    ("9608_w17_qp_21", "5", "(a)", None): ("text-files", "procedures", "pre-condition-loop", "string-handling", "variables-constants"),
    # 9608_w17_qp_22 Q1 (d) (ii) [5 marks]
    ("9608_w17_qp_22", "1", "(d)", "(ii)"): ("selection-if", "selection-case", "logic-statements", "operators-expressions"),
    # 9608_w17_qp_22 Q5 [9 marks]
    ("9608_w17_qp_22", "5", None, None): ("text-files", "procedures", "pre-condition-loop", "selection-if", "string-handling"),
    # 9608_w17_qp_23 Q1 (c) [4 marks]
    ("9608_w17_qp_23", "1", "(c)", None): ("selection-case", "selection-if", "procedures", "input-output"),
    # 9608_w17_qp_23 Q3 (a) [8 marks]
    ("9608_w17_qp_23", "3", "(a)", None): ("bubble-sort", "arrays-1d", "procedures", "post-condition-loop", "nested-loops"),
    # 9608_w17_qp_23 Q5 (a) [8 marks]
    ("9608_w17_qp_23", "5", "(a)", None): ("text-files", "procedures", "pre-condition-loop", "string-handling", "variables-constants"),
    # 9608_w18_qp_21 Q2 (a) [8 marks]
    ("9608_w18_qp_21", "2", "(a)", None): ("flowchart", "functions", "selection-if", "parameters", "variables-constants"),
    # 9608_w18_qp_21 Q2 (c) (ii) [2 marks]
    ("9608_w18_qp_21", "2", "(c)", "(ii)"): ("variables-constants", "data-types", "identifier-table", "flowchart"),
    # 9608_w18_qp_21 Q5 [10 marks]
    ("9608_w18_qp_21", "5", None, None): ("text-files", "functions", "pre-condition-loop", "selection-if", "string-handling"),
    # 9608_w18_qp_22 Q2 (a) (i) [7 marks]
    ("9608_w18_qp_22", "2", "(a)", "(i)"): ("flowchart", "functions", "selection-if", "parameters", "built-in-functions"),
    # 9608_w18_qp_22 Q2 (a) (ii) [5 marks]
    ("9608_w18_qp_22", "2", "(a)", "(ii)"): ("validation", "functions", "post-condition-loop", "input-output", "logic-statements"),
    # 9608_w18_qp_22 Q3 (c) [4 marks]
    ("9608_w18_qp_22", "3", "(c)", None): ("linear-search", "arrays-1d", "stepwise-refinement", "array-processing"),
    # 9608_w18_qp_23 Q2 (a) (i) [5 marks]
    ("9608_w18_qp_23", "2", "(a)", "(i)"): ("flowchart", "functions", "selection-if", "parameters", "variables-constants"),
    # 9608_w18_qp_23 Q2 (a) (ii) [6 marks]
    ("9608_w18_qp_23", "2", "(a)", "(ii)"): ("validation", "functions", "post-condition-loop", "built-in-functions", "string-handling"),
    # 9608_w18_qp_23 Q3 (b) [3 marks]
    ("9608_w18_qp_23", "3", "(b)", None): ("array-processing", "arrays-1d", "stepwise-refinement", "count-controlled-loop"),
    # 9608_w18_qp_23 Q4 (d) (ii) [1 marks]
    ("9608_w18_qp_23", "4", "(d)", "(ii)"): ("variables-constants", "data-types", "arrays-2d", "functions"),
    # 9608_w19_qp_21 Q4 (b) [7 marks]
    ("9608_w19_qp_21", "4", "(b)", None): ("arrays-1d", "string-handling", "count-controlled-loop", "built-in-functions", "selection-if"),
    # 9608_w19_qp_21 Q6 (c) [8 marks]
    ("9608_w19_qp_21", "6", "(c)", None): ("text-files", "procedures", "pre-condition-loop", "string-handling", "arrays-1d"),
    # 9608_w19_qp_21 Q6 (d) (i) [3 marks]
    ("9608_w19_qp_21", "6", "(d)", "(i)"): ("procedures", "parameters", "arrays-1d", "count-controlled-loop"),
    # 9608_w19_qp_22 Q3 (a) [3 marks]
    ("9608_w19_qp_22", "3", "(a)", None): ("arrays-1d", "count-controlled-loop", "variables-constants", "data-types"),
    # 9608_w19_qp_22 Q4 (a) [6 marks]
    ("9608_w19_qp_22", "4", "(a)", None): ("procedures", "parameters", "selection-if", "variables-constants", "logic-statements"),
    # 9608_w19_qp_22 Q6 (b) [9 marks]
    ("9608_w19_qp_22", "6", "(b)", None): ("text-files", "functions", "pre-condition-loop", "string-handling", "selection-if"),
    # 9608_w19_qp_23 Q5 [8 marks]
    ("9608_w19_qp_23", "5", None, None): ("functions", "string-handling", "count-controlled-loop", "selection-if", "built-in-functions"),
    # 9608_w19_qp_23 Q6 (a) (i) [3 marks]
    ("9608_w19_qp_23", "6", "(a)", "(i)"): ("arrays-2d", "data-types", "variables-constants", "text-files"),
    # 9608_w19_qp_23 Q6 (b) [7 marks]
    ("9608_w19_qp_23", "6", "(b)", None): ("procedures", "parameters", "arrays-2d", "input-output", "string-handling"),
    # 9618_s21_qp_21 Q2 (b) [2 marks]
    ("9618_s21_qp_21", "2", "(b)", None): ("procedures", "parameters", "data-types", "structure-chart"),
    # 9618_s21_qp_21 Q3 (b) [5 marks]
    ("9618_s21_qp_21", "3", "(b)", None): ("text-files", "procedures", "parameters", "pre-condition-loop", "selection-if"),
    # 9618_s21_qp_21 Q5 [8 marks]
    ("9618_s21_qp_21", "5", None, None): ("bubble-sort", "arrays-2d", "procedures", "post-condition-loop", "nested-loops"),
    # 9618_s21_qp_21 Q7 (a) [7 marks]
    ("9618_s21_qp_21", "7", "(a)", None): ("functions", "string-handling", "pre-condition-loop", "selection-if", "parameters"),
    # 9618_s21_qp_21 Q7 (c) [5 marks]
    ("9618_s21_qp_21", "7", "(c)", None): ("functions", "string-handling", "post-condition-loop", "built-in-functions", "parameters"),
    # 9618_s21_qp_22 Q5 (a) (i) [6 marks]
    ("9618_s21_qp_22", "5", "(a)", "(i)"): ("arrays-1d", "count-controlled-loop", "built-in-functions", "selection-if", "array-processing"),
    # 9618_s21_qp_22 Q6 [8 marks]
    ("9618_s21_qp_22", "6", None, None): ("procedures", "string-handling", "selection-case", "arrays-1d", "count-controlled-loop"),
    # 9618_s21_qp_22 Q8 (a) [5 marks]
    ("9618_s21_qp_22", "8", "(a)", None): ("functions", "linear-search", "arrays-1d", "post-condition-loop", "string-handling"),
    # 9618_s21_qp_22 Q8 (b) [8 marks]
    ("9618_s21_qp_22", "8", "(b)", None): ("procedures", "decomposition", "post-condition-loop", "string-handling", "selection-if"),
    # 9618_s21_qp_23 Q2 (b) [2 marks]
    ("9618_s21_qp_23", "2", "(b)", None): ("procedures", "parameters", "data-types", "structure-chart"),
    # 9618_s21_qp_23 Q3 (b) [5 marks]
    ("9618_s21_qp_23", "3", "(b)", None): ("text-files", "procedures", "parameters", "pre-condition-loop", "selection-if"),
    # 9618_s21_qp_23 Q5 [8 marks]
    ("9618_s21_qp_23", "5", None, None): ("bubble-sort", "arrays-2d", "procedures", "post-condition-loop", "nested-loops"),
    # 9618_s21_qp_23 Q7 (a) [7 marks]
    ("9618_s21_qp_23", "7", "(a)", None): ("functions", "string-handling", "pre-condition-loop", "selection-if", "parameters"),
    # 9618_s21_qp_23 Q7 (c) [5 marks]
    ("9618_s21_qp_23", "7", "(c)", None): ("functions", "string-handling", "post-condition-loop", "built-in-functions", "parameters"),
    # 9618_s23_qp_21 Q2 (b) [3 marks]
    ("9618_s23_qp_21", "2", "(b)", None): ("data-types", "variables-constants", "built-in-functions", "operators-expressions"),
    # 9618_s23_qp_21 Q4 [6 marks]
    ("9618_s23_qp_21", "4", None, None): ("functions", "string-handling", "count-controlled-loop", "parameters", "selection-if"),
    # 9618_s23_qp_21 Q6 [6 marks]
    ("9618_s23_qp_21", "6", None, None): ("arrays-2d", "nested-loops", "procedures", "array-processing", "built-in-functions"),
    # 9618_s23_qp_21 Q8 (a) [7 marks]
    ("9618_s23_qp_21", "8", "(a)", None): ("validation", "functions", "string-handling", "count-controlled-loop", "selection-if"),
    # 9618_s23_qp_22 Q2 (a) [1 marks]
    ("9618_s23_qp_22", "2", "(a)", None): ("data-types", "built-in-functions", "variables-constants", "operators-expressions"),
    # 9618_s23_qp_22 Q2 (b) [2 marks]
    ("9618_s23_qp_22", "2", "(b)", None): ("data-types", "built-in-functions", "operators-expressions", "variables-constants"),
    # 9618_s23_qp_22 Q4 [6 marks]
    ("9618_s23_qp_22", "4", None, None): ("functions", "string-handling", "count-controlled-loop", "parameters", "selection-if"),
    # 9618_s23_qp_22 Q6 [6 marks]
    ("9618_s23_qp_22", "6", None, None): ("procedures", "parameters", "string-handling", "count-controlled-loop", "input-output"),
    # 9618_s23_qp_22 Q8 (a) [7 marks]
    ("9618_s23_qp_22", "8", "(a)", None): ("validation", "functions", "string-handling", "selection-if", "built-in-functions"),
    # 9618_s23_qp_22 Q8 (b) [7 marks]
    ("9618_s23_qp_22", "8", "(b)", None): ("text-files", "procedures", "pre-condition-loop", "string-handling", "selection-if"),
    # 9618_s23_qp_23 Q2 (a) [2 marks]
    ("9618_s23_qp_23", "2", "(a)", None): ("data-types", "built-in-functions", "selection-if", "logic-statements"),
    # 9618_s23_qp_23 Q4 [6 marks]
    ("9618_s23_qp_23", "4", None, None): ("functions", "string-handling", "count-controlled-loop", "parameters", "selection-if"),
    # 9618_s23_qp_23 Q6 (a) [7 marks]
    ("9618_s23_qp_23", "6", "(a)", None): ("procedures", "parameters", "count-controlled-loop", "string-handling", "built-in-functions"),
    # 9618_s23_qp_23 Q8 (a) [8 marks]
    ("9618_s23_qp_23", "8", "(a)", None): ("text-files", "functions", "pre-condition-loop", "string-handling", "selection-if"),
    # 9618_s23_qp_23 Q8 (b) [6 marks]
    ("9618_s23_qp_23", "8", "(b)", None): ("text-files", "procedures", "pre-condition-loop", "string-handling", "input-output"),
    # 9618_s24_qp_21 Q4 [6 marks]
    ("9618_s24_qp_21", "4", None, None): ("functions", "arrays-1d", "array-processing", "count-controlled-loop", "built-in-functions"),
    # 9618_s24_qp_21 Q6 (a) [6 marks]
    ("9618_s24_qp_21", "6", "(a)", None): ("functions", "parameters", "operators-expressions", "logic-statements", "selection-if"),
    # 9618_s24_qp_21 Q8 (a) [8 marks]
    ("9618_s24_qp_21", "8", "(a)", None): ("functions", "string-handling", "pre-condition-loop", "built-in-functions", "selection-if"),
    # 9618_s24_qp_21 Q8 (b) [7 marks]
    ("9618_s24_qp_21", "8", "(b)", None): ("text-files", "functions", "pre-condition-loop", "decomposition", "string-handling"),
    # 9618_s24_qp_22 Q2 (b) [5 marks]
    ("9618_s24_qp_22", "2", "(b)", None): ("flowchart", "pre-condition-loop", "count-controlled-loop", "procedures", "nested-loops"),
    # 9618_s24_qp_22 Q3 (a) (i) [4 marks]
    ("9618_s24_qp_22", "3", "(a)", "(i)"): ("records", "data-types", "variables-constants", "identifier-table"),
    # 9618_s24_qp_22 Q3 (a) (ii) [2 marks]
    ("9618_s24_qp_22", "3", "(a)", "(ii)"): ("arrays-1d", "records", "data-types", "variables-constants"),
    # 9618_s24_qp_22 Q4 [5 marks]
    ("9618_s24_qp_22", "4", None, None): ("procedures", "input-output", "selection-if", "logic-statements", "operators-expressions"),
    # 9618_s24_qp_22 Q6 (a) [7 marks]
    ("9618_s24_qp_22", "6", "(a)", None): ("functions", "string-handling", "pre-condition-loop", "post-condition-loop", "built-in-functions"),
    # 9618_s24_qp_22 Q8 (b) [6 marks]
    ("9618_s24_qp_22", "8", "(b)", None): ("functions", "string-handling", "count-controlled-loop", "built-in-functions", "selection-if"),
    # 9618_s24_qp_22 Q8 (c) [8 marks]
    ("9618_s24_qp_22", "8", "(c)", None): ("text-files", "procedures", "pre-condition-loop", "decomposition", "parameters"),
    # 9618_s24_qp_23 Q3 (a) (i) [3 marks]
    ("9618_s24_qp_23", "3", "(a)", "(i)"): ("records", "validation", "logic-statements", "selection-if", "arrays-1d"),
    # 9618_s24_qp_23 Q6 (a) [6 marks]
    ("9618_s24_qp_23", "6", "(a)", None): ("procedures", "parameters", "string-handling", "built-in-functions", "operators-expressions"),
    # 9618_s24_qp_23 Q6 (b) (i) [2 marks]
    ("9618_s24_qp_23", "6", "(b)", "(i)"): ("functions", "parameters", "data-types", "decomposition"),
    # 9618_s24_qp_23 Q8 (a) [7 marks]
    ("9618_s24_qp_23", "8", "(a)", None): ("functions", "string-handling", "built-in-functions", "selection-if", "parameters"),
    # 9618_s24_qp_23 Q8 (b) [8 marks]
    ("9618_s24_qp_23", "8", "(b)", None): ("text-files", "procedures", "arrays-2d", "pre-condition-loop", "string-handling"),
    # 9618_s25_qp_21 Q3 [8 marks]
    ("9618_s25_qp_21", "3", None, None): ("structured-english", "post-condition-loop", "input-output", "selection-if", "built-in-functions"),
    # 9618_s25_qp_21 Q7 (a) [6 marks]
    ("9618_s25_qp_21", "7", "(a)", None): ("functions", "parameters", "pre-condition-loop", "operators-expressions", "input-output"),
    # 9618_s25_qp_21 Q7 (b) (i) [8 marks]
    ("9618_s25_qp_21", "7", "(b)", "(i)"): ("text-files", "procedures", "pre-condition-loop", "count-controlled-loop", "string-handling"),
    # 9618_s25_qp_22 Q3 [8 marks]
    ("9618_s25_qp_22", "3", None, None): ("built-in-functions", "post-condition-loop", "selection-if", "variables-constants", "input-output"),
    # 9618_s25_qp_22 Q5 (b) [8 marks]
    ("9618_s25_qp_22", "5", "(b)", None): ("text-files", "pre-condition-loop", "string-handling", "selection-if", "input-output"),
    # 9618_s25_qp_23 Q3 [7 marks]
    ("9618_s25_qp_23", "3", None, None): ("functions", "parameters", "count-controlled-loop", "built-in-functions", "input-output"),
    # 9618_s25_qp_23 Q5 [8 marks]
    ("9618_s25_qp_23", "5", None, None): ("functions", "string-handling", "count-controlled-loop", "built-in-functions", "selection-if"),
    # 9618_s25_qp_23 Q7 (a) (i) [5 marks]
    ("9618_s25_qp_23", "7", "(a)", "(i)"): ("procedures", "parameters", "data-types", "built-in-functions", "selection-if"),
    # 9618_s25_qp_23 Q7 (b) (i) [8 marks]
    ("9618_s25_qp_23", "7", "(b)", "(i)"): ("functions", "string-handling", "built-in-functions", "decomposition", "selection-if"),
    # 9618_w21_qp_21 Q2 (b) [6 marks]
    ("9618_w21_qp_21", "2", "(b)", None): ("flowchart", "pre-condition-loop", "selection-if", "procedures", "logic-statements"),
    # 9618_w21_qp_21 Q5 (c) [7 marks]
    ("9618_w21_qp_21", "5", "(c)", None): ("text-files", "functions", "arrays-1d", "count-controlled-loop", "string-handling"),
    # 9618_w21_qp_21 Q6 (a) [5 marks]
    ("9618_w21_qp_21", "6", "(a)", None): ("arrays-2d", "procedures", "parameters", "count-controlled-loop", "variables-constants"),
    # 9618_w21_qp_21 Q6 (b) [8 marks]
    ("9618_w21_qp_21", "6", "(b)", None): ("linear-search", "arrays-2d", "functions", "pre-condition-loop", "parameters"),
    # 9618_w21_qp_21 Q6 (c) [6 marks]
    ("9618_w21_qp_21", "6", "(c)", None): ("functions", "decomposition", "built-in-functions", "selection-if", "arrays-2d"),
    # 9618_w21_qp_22 Q1 (c) [4 marks]
    ("9618_w21_qp_22", "1", "(c)", None): ("built-in-functions", "operators-expressions", "string-handling", "data-types"),
    # 9618_w21_qp_22 Q3 (a) (i) [3 marks]
    ("9618_w21_qp_22", "3", "(a)", "(i)"): ("records", "data-types", "variables-constants", "identifier-table"),
    # 9618_w21_qp_22 Q3 (a) (ii) [2 marks]
    ("9618_w21_qp_22", "3", "(a)", "(ii)"): ("arrays-1d", "records", "data-types", "variables-constants"),
    # 9618_w21_qp_22 Q3 (b) [7 marks]
    ("9618_w21_qp_22", "3", "(b)", None): ("records", "arrays-1d", "procedures", "count-controlled-loop", "selection-if"),
    # 9618_w21_qp_22 Q5 (a) [7 marks]
    ("9618_w21_qp_22", "5", "(a)", None): ("text-files", "procedures", "parameters", "pre-condition-loop", "selection-if"),
    # 9618_w21_qp_22 Q6 (d) [6 marks]
    ("9618_w21_qp_22", "6", "(d)", None): ("procedures", "decomposition", "built-in-functions", "selection-if", "arrays-2d"),
    # 9618_w21_qp_23 Q2 (b) [6 marks]
    ("9618_w21_qp_23", "2", "(b)", None): ("flowchart", "pre-condition-loop", "selection-if", "procedures", "logic-statements"),
    # 9618_w21_qp_23 Q5 (c) [7 marks]
    ("9618_w21_qp_23", "5", "(c)", None): ("text-files", "functions", "arrays-1d", "count-controlled-loop", "string-handling"),
    # 9618_w21_qp_23 Q6 (a) [5 marks]
    ("9618_w21_qp_23", "6", "(a)", None): ("arrays-2d", "procedures", "parameters", "count-controlled-loop", "variables-constants"),
    # 9618_w21_qp_23 Q6 (b) [8 marks]
    ("9618_w21_qp_23", "6", "(b)", None): ("linear-search", "arrays-2d", "functions", "pre-condition-loop", "parameters"),
    # 9618_w21_qp_23 Q6 (c) [6 marks]
    ("9618_w21_qp_23", "6", "(c)", None): ("functions", "decomposition", "built-in-functions", "selection-if", "arrays-2d"),
    # 9618_w22_qp_21 Q5 [5 marks]
    ("9618_w22_qp_21", "5", None, None): ("arrays-1d", "array-processing", "procedures", "count-controlled-loop", "built-in-functions"),
    # 9618_w22_qp_21 Q7 (a) (i) [7 marks]
    ("9618_w22_qp_21", "7", "(a)", "(i)"): ("procedures", "string-handling", "built-in-functions", "operators-expressions", "selection-if"),
    # 9618_w22_qp_21 Q7 (a) (ii) [1 marks]
    ("9618_w22_qp_21", "7", "(a)", "(ii)"): ("functions", "parameters", "data-types", "string-handling"),
    # 9618_w22_qp_21 Q8 (a) [7 marks]
    ("9618_w22_qp_21", "8", "(a)", None): ("text-files", "functions", "pre-condition-loop", "selection-if", "parameters"),
    # 9618_w22_qp_21 Q8 (c) [8 marks]
    ("9618_w22_qp_21", "8", "(c)", None): ("text-files", "procedures", "decomposition", "post-condition-loop", "selection-if"),
    # 9618_w22_qp_22 Q5 [4 marks]
    ("9618_w22_qp_22", "5", None, None): ("logic-statements", "selection-if", "operators-expressions", "procedures"),
    # 9618_w22_qp_22 Q6 (a) [7 marks]
    ("9618_w22_qp_22", "6", "(a)", None): ("functions", "pre-condition-loop", "parameters", "operators-expressions", "selection-if"),
    # 9618_w22_qp_22 Q7 (b) [8 marks]
    ("9618_w22_qp_22", "7", "(b)", None): ("bubble-sort", "arrays-1d", "procedures", "post-condition-loop", "nested-loops"),
    # 9618_w22_qp_22 Q7 (c) (iii) [1 marks]
    ("9618_w22_qp_22", "7", "(c)", "(iii)"): ("arrays-1d", "records", "data-types", "variables-constants"),
    # 9618_w22_qp_23 Q5 (a) (i) [6 marks]
    ("9618_w22_qp_23", "5", "(a)", "(i)"): ("procedures", "parameters", "string-handling", "built-in-functions", "data-types"),
    # 9618_w22_qp_23 Q6 (b) [6 marks]
    ("9618_w22_qp_23", "6", "(b)", None): ("functions", "parameters", "selection-if", "logic-statements", "variables-constants"),
    # 9618_w22_qp_23 Q7 (a) [8 marks]
    ("9618_w22_qp_23", "7", "(a)", None): ("procedures", "arrays-1d", "input-output", "pre-condition-loop", "selection-if"),
    # 9618_w22_qp_23 Q7 (b) (i) [6 marks]
    ("9618_w22_qp_23", "7", "(b)", "(i)"): ("functions", "arrays-1d", "post-condition-loop", "linear-search", "decomposition"),
    # 9618_w23_qp_21 Q4 (a) [6 marks]
    ("9618_w23_qp_21", "4", "(a)", None): ("functions", "arrays-1d", "count-controlled-loop", "linear-search", "parameters"),
    # 9618_w23_qp_21 Q4 (b) [3 marks]
    ("9618_w23_qp_21", "4", "(b)", None): ("arrays-2d", "logic-statements", "selection-if", "operators-expressions"),
    # 9618_w23_qp_21 Q6 (a) [7 marks]
    ("9618_w23_qp_21", "6", "(a)", None): ("procedures", "parameters", "string-handling", "selection-if", "built-in-functions"),
    # 9618_w23_qp_21 Q8 (a) [7 marks]
    ("9618_w23_qp_21", "8", "(a)", None): ("text-files", "procedures", "parameters", "pre-condition-loop", "string-handling"),
    # 9618_w23_qp_22 Q4 (a) [6 marks]
    ("9618_w23_qp_22", "4", "(a)", None): ("procedures", "input-output", "pre-condition-loop", "selection-if", "operators-expressions"),
    # 9618_w23_qp_22 Q6 (a) [6 marks]
    ("9618_w23_qp_22", "6", "(a)", None): ("text-files", "procedures", "parameters", "count-controlled-loop", "string-handling"),
    # 9618_w23_qp_22 Q8 (a) [7 marks]
    ("9618_w23_qp_22", "8", "(a)", None): ("functions", "arrays-2d", "linear-search", "post-condition-loop", "selection-if"),
    # 9618_w23_qp_22 Q8 (b) [7 marks]
    ("9618_w23_qp_22", "8", "(b)", None): ("adt-stack", "procedures", "string-handling", "selection-if", "decomposition"),
    # 9618_w23_qp_23 Q2 (c) [2 marks]
    ("9618_w23_qp_23", "2", "(c)", None): ("arrays-1d", "data-types", "variables-constants", "array-processing"),
    # 9618_w23_qp_23 Q4 (a) [6 marks]
    ("9618_w23_qp_23", "4", "(a)", None): ("procedures", "count-controlled-loop", "built-in-functions", "input-output", "variables-constants"),
    # 9618_w23_qp_23 Q6 [6 marks]
    ("9618_w23_qp_23", "6", None, None): ("functions", "string-handling", "selection-if", "built-in-functions", "parameters"),
    # 9618_w23_qp_23 Q7 (b) (i) [3 marks]
    ("9618_w23_qp_23", "7", "(b)", "(i)"): ("records", "data-types", "structure-chart", "variables-constants"),
    # 9618_w23_qp_23 Q7 (b) (ii) [2 marks]
    ("9618_w23_qp_23", "7", "(b)", "(ii)"): ("procedures", "parameters", "records", "structure-chart"),
    # 9618_w23_qp_23 Q8 (a) [7 marks]
    ("9618_w23_qp_23", "8", "(a)", None): ("text-files", "procedures", "pre-condition-loop", "decomposition", "string-handling"),
    # 9618_w23_qp_23 Q8 (c) [7 marks]
    ("9618_w23_qp_23", "8", "(c)", None): ("procedures", "post-condition-loop", "input-output", "decomposition", "string-handling"),
    # 9618_w24_qp_21 Q2 [6 marks]
    ("9618_w24_qp_21", "2", None, None): ("procedures", "selection-if", "variables-constants", "operators-expressions", "decomposition"),
    # 9618_w24_qp_21 Q4 (c) [6 marks]
    ("9618_w24_qp_21", "4", "(c)", None): ("records", "functions", "parameters", "built-in-functions", "validation"),
    # 9618_w24_qp_21 Q6 (b) [7 marks]
    ("9618_w24_qp_21", "6", "(b)", None): ("functions", "data-types", "built-in-functions", "arrays-1d", "selection-if"),
    # 9618_w24_qp_21 Q8 (a) [6 marks]
    ("9618_w24_qp_21", "8", "(a)", None): ("functions", "arrays-1d", "count-controlled-loop", "selection-if", "logic-statements"),
    # 9618_w24_qp_21 Q8 (b) [8 marks]
    ("9618_w24_qp_21", "8", "(b)", None): ("text-files", "procedures", "arrays-2d", "count-controlled-loop", "decomposition"),
    # 9618_w24_qp_22 Q2 (a) [6 marks]
    ("9618_w24_qp_22", "2", "(a)", None): ("functions", "string-handling", "count-controlled-loop", "built-in-functions", "parameters"),
    # 9618_w24_qp_22 Q2 (b) (i) [2 marks]
    ("9618_w24_qp_22", "2", "(b)", "(i)"): ("arrays-2d", "data-types", "variables-constants", "array-processing"),
    # 9618_w24_qp_22 Q3 (b) [4 marks]
    ("9618_w24_qp_22", "3", "(b)", None): ("adt-stack", "arrays-1d", "functions", "selection-if", "variables-constants"),
    # 9618_w24_qp_22 Q4 [6 marks]
    ("9618_w24_qp_22", "4", None, None): ("procedures", "parameters", "post-condition-loop", "operators-expressions", "input-output"),
    # 9618_w24_qp_22 Q5 (c) [2 marks]
    ("9618_w24_qp_22", "5", "(c)", None): ("selection-if", "selection-case", "built-in-functions", "operators-expressions"),
    # 9618_w24_qp_22 Q6 (a) [7 marks]
    ("9618_w24_qp_22", "6", "(a)", None): ("procedures", "arrays-1d", "built-in-functions", "post-condition-loop", "input-output"),
    # 9618_w24_qp_22 Q8 (a) [7 marks]
    ("9618_w24_qp_22", "8", "(a)", None): ("records", "arrays-1d", "procedures", "pre-condition-loop", "selection-if"),
    # 9618_w24_qp_22 Q8 (b) [7 marks]
    ("9618_w24_qp_22", "8", "(b)", None): ("text-files", "records", "procedures", "count-controlled-loop", "string-handling"),
    # 9618_w24_qp_23 Q2 (a) [5 marks]
    ("9618_w24_qp_23", "2", "(a)", None): ("count-controlled-loop", "input-output", "selection-if", "variables-constants", "operators-expressions"),
    # 9618_w24_qp_23 Q4 (a) [4 marks]
    ("9618_w24_qp_23", "4", "(a)", None): ("arrays-1d", "count-controlled-loop", "selection-if", "logic-statements", "operators-expressions"),
    # 9618_w24_qp_23 Q4 (b) (ii) [6 marks]
    ("9618_w24_qp_23", "4", "(b)", "(ii)"): ("arrays-1d", "procedures", "nested-loops", "count-controlled-loop", "array-processing"),
    # 9618_w24_qp_23 Q6 [7 marks]
    ("9618_w24_qp_23", "6", None, None): ("functions", "data-types", "built-in-functions", "post-condition-loop", "selection-if"),
    # 9618_w24_qp_23 Q8 (a) [7 marks]
    ("9618_w24_qp_23", "8", "(a)", None): ("records", "arrays-1d", "procedures", "count-controlled-loop", "selection-if"),
    # 9618_w24_qp_23 Q8 (b) [7 marks]
    ("9618_w24_qp_23", "8", "(b)", None): ("text-files", "records", "procedures", "count-controlled-loop", "arrays-1d"),
    # 9618_w25_qp_21 Q3 (a) (i) [4 marks]
    ("9618_w25_qp_21", "3", "(a)", "(i)"): ("records", "data-types", "variables-constants", "identifier-table"),
    # 9618_w25_qp_21 Q3 (a) (ii) [2 marks]
    ("9618_w25_qp_21", "3", "(a)", "(ii)"): ("arrays-1d", "records", "data-types", "variables-constants"),
    # 9618_w25_qp_21 Q4 (a) [6 marks]
    ("9618_w25_qp_21", "4", "(a)", None): ("arrays-1d", "procedures", "pre-condition-loop", "input-output", "selection-if"),
    # 9618_w25_qp_21 Q6 (b) [7 marks]
    ("9618_w25_qp_21", "6", "(b)", None): ("validation", "functions", "string-handling", "count-controlled-loop", "built-in-functions"),
    # 9618_w25_qp_22 Q4 (a) [4 marks]
    ("9618_w25_qp_22", "4", "(a)", None): ("arrays-1d", "data-types", "count-controlled-loop", "variables-constants"),
    # 9618_w25_qp_22 Q4 (b) [5 marks]
    ("9618_w25_qp_22", "4", "(b)", None): ("nested-loops", "count-controlled-loop", "arrays-1d", "operators-expressions"),
    # 9618_w25_qp_22 Q6 [7 marks]
    ("9618_w25_qp_22", "6", None, None): ("functions", "parameters", "string-handling", "selection-case", "built-in-functions"),
    # 9618_w25_qp_22 Q8 (a) [7 marks]
    ("9618_w25_qp_22", "8", "(a)", None): ("records", "arrays-1d", "procedures", "count-controlled-loop", "selection-if"),
    # 9618_w25_qp_23 Q3 [5 marks]
    ("9618_w25_qp_23", "3", None, None): ("adt-stack", "records", "functions", "arrays-1d", "selection-if"),
    # 9618_w25_qp_23 Q4 [6 marks]
    ("9618_w25_qp_23", "4", None, None): ("string-handling", "arrays-1d", "procedures", "pre-condition-loop", "built-in-functions"),
    # 9618_w25_qp_23 Q5 (b) (ii) [2 marks]
    ("9618_w25_qp_23", "5", "(b)", "(ii)"): ("selection-case", "arrays-1d", "operators-expressions", "variables-constants"),
    # 9618_w25_qp_23 Q6 (b) [7 marks]
    ("9618_w25_qp_23", "6", "(b)", None): ("validation", "functions", "string-handling", "count-controlled-loop", "built-in-functions"),
    # 9618_w25_qp_23 Q8 (b) [7 marks]
    ("9618_w25_qp_23", "8", "(b)", None): ("records", "arrays-1d", "functions", "count-controlled-loop", "string-handling"),
}
# fmt: on


def tags_for_segment(
    paper_code: str,
    question_marker: Optional[str],
    primary_marker: Optional[str],
    secondary_marker: Optional[str],
) -> List[str]:
    """Return the tags for one segment, or ``[]`` when it has not been tagged.

    Validates on the way out so a hand-edit that breaks the vocabulary or the
    4-5 tag rule fails loudly at build time rather than shipping a bad tag to
    the website.
    """

    key = (paper_code, question_marker, primary_marker, secondary_marker)
    slugs = _TAGS.get(key)
    if slugs is None:
        return []
    return validate_tags(list(slugs), context=f"segment {key}")


def tagged_segment_count() -> int:
    """Number of segments with curated tags; used by build-time reporting."""

    return len(_TAGS)
