# Learn topic research

Research date: 2026-08-13.

Primary sources checked:

- Cambridge International AS & A Level Computer Science 9618 syllabus for 2027, 2028 and 2029, supplied in [`computer-science-syllabus-9618.pdf`](reference/computer-science-syllabus-9618.pdf).
- The website's 176 unique published pseudocode-writing records (deduplicated from 194 source records) in [`pseudocode_question_records.json`](../src/website/frontend/public/resources/pseudocode_question_records.json).
- The repository's controlled syllabus vocabulary in [`syllabus_tags.py`](../src/pipeline/pseudocode_tools/syllabus_tags.py) and hand-assigned record tags in [`question_tag_assignments.py`](../src/pipeline/pseudocode_tools/question_tag_assignments.py).

## Recommendation

Populate Learn with a compact core curriculum in this order:

1. **Selection and iteration** — `IF` / `CASE`, `FOR`, `WHILE`, and `REPEAT`; choosing the right loop.
2. **Procedures, functions, and parameters** — decomposition, return values, `BYREF` / `BYVAL`, and reusable modules.
3. **Strings and built-in functions** — traversal, slicing, concatenation, character conversion, `DIV` / `MOD`, and other supplied routines.
4. **Arrays and array processing** — 1D and 2D arrays, bounds, traversal, totals, counts, extrema, and nested loops.
5. **Linear search and binary search** — implement both and explain why binary search requires ordered data.
6. **Bubble sort and insertion sort** — implement, trace, and compare them on differently ordered inputs.
7. **Records and validation** — define and process records; range, format, length, presence, existence, limit, and check-digit validation.
8. **Text files** — open, read to EOF, write, append, and close; extend later to serial, sequential, and random files.
9. **Stacks, queues, and linked lists** — operations, appropriate use cases, and array-backed implementations.
10. **Binary trees and dictionaries** — find, insert, delete where required, and relate these structures to other ADTs.
11. **Problem decomposition and stepwise refinement** — move from a scenario, structured English, flowchart, or structure chart to small testable modules.
12. **Recursion and complexity** — base cases, call-stack unwinding, tracing, and introductory Big O time/space comparisons.

This ordering gives the first screen to the concepts students encounter most in the site's question bank, while keeping the four named search/sort algorithms and the major A Level structures explicitly required by the current syllabus. A later **Programming paradigms** collection can cover OOP, imperative/procedural programming, declarative programming, exception handling, and testing/debugging; these are syllabus-backed but are not represented in the current pseudocode-writing corpus.

## What appears in the current corpus

The source set contains 194 records from 50 question papers. The canonical builder merges 18 exact parallel-paper repeats, leaving 176 unique published questions while retaining every removed paper in provenance. Each record carries four or five controlled tags. Those tags were assigned by reading the question, context, and mark scheme, not by keyword matching; parallel-paper variants deliberately receive identical tags. Sources: [`question_tag_assignments.py`, assignment method](../src/pipeline/pseudocode_tools/question_tag_assignments.py#L1-L26); [`syllabus_tags.py`, validation rule](../src/pipeline/pseudocode_tools/syllabus_tags.py#L203-L224).

The following groups count a record once if it has any tag in that group. Groups overlap, so percentages should not be added.

| Learn area | Records | Share of 176 | Tags included |
| --- | ---: | ---: | --- |
| Selection and iteration | 142 | 80.7% | IF, CASE, count-/pre-/post-condition loops, nested loops |
| Modular programming | 130 | 73.9% | functions, procedures, parameters, decomposition |
| Strings and library routines | 87 | 49.4% | string handling, built-in functions |
| Arrays and array processing | 69 | 39.2% | 1D arrays, 2D arrays, array processing |
| Algorithm design and decomposition | 35 | 19.9% | decomposition, stepwise refinement, structured English, flowcharts, structure charts |
| Text files | 31 | 17.6% | text-file handling |
| Records | 19 | 10.8% | record structures |
| Linear search | 8 | 4.5% | linear search |
| Data validation | 9 | 5.1% | validation |
| Bubble sort | 4 | 2.3% | bubble sort |
| Stack | 3 | 1.7% | stack ADT |

The highest individual tag counts further support the ordering: IF selection appears in 79 records; functions and procedures in 65 each; string handling in 63; built-in functions in 51; parameters and count-controlled loops in 50 each; 1D arrays in 50; variables/constants in 38; pre-condition loops in 36; text files in 31; 2D arrays in 19; and records in 19. The vocabulary definitions for these topics are in [`syllabus_tags.py`](../src/pipeline/pseudocode_tools/syllabus_tags.py#L82-L144).

Frequency was calculated directly from the published record tags with the equivalent of:

```python
group_count = sum(
    bool({tag["slug"] for tag in record["syllabus_tags"]} & group_tags)
    for record in records
)
```

The current corpus has no tagged questions for binary search, insertion sort, queue, linked list, binary tree, dictionary, recursion, Big O complexity, OOP, or exception handling. The repository records these absences deliberately in [`test_syllabus_tags.py`](../tests/test_syllabus_tags.py#L96-L129). Absence here should not be read as syllabus unimportance: this website resource is a pseudocode-writing subset, and the syllabus says Paper 2 covers sections 9–12 while the advanced practical programming assessment covers sections 19–20 (syllabus p. 40).

## Syllabus evidence

### Core pseudocode and methodologies

- **Algorithm design:** sections 9.1–9.2 require abstraction, decomposition, input/process/output, sequence/selection/iteration, structured English, flowcharts, pseudocode, and stepwise refinement (syllabus pp. 27–28). The local tag vocabulary maps these to stable Learn concepts in [`syllabus_tags.py`](../src/pipeline/pseudocode_tools/syllabus_tags.py#L66-L80).
- **Arrays, Linear Search, and Bubble Sort:** section 10.2 requires 1D/2D arrays and array processing and explicitly names bubble sort and linear search (syllabus p. 28). The repository preserves the dual AS/A Level references for the algorithms in [`syllabus_tags.py`](../src/pipeline/pseudocode_tools/syllabus_tags.py#L88-L98).
- **Programming constructs:** sections 11.1–11.2 require variables, constants, expressions, input/output, built-ins, `IF`, `CASE`, and count-, pre-, and post-condition loops, including choosing a suitable loop (syllabus p. 29).
- **Structured programming:** section 11.3 requires procedures, functions, parameters by reference/value, arguments, return values, and efficient pseudocode (syllabus p. 30).
- **Program design:** section 12.2 requires decomposition via structure charts, parameters between modules, and deriving pseudocode from a structure chart (syllabus p. 30). Section 12.1 also defines waterfall, iterative, and RAD development life cycles, but those are less suitable as initial hands-on pseudocode lessons.
- **Testing:** section 12.3 requires error identification/correction, testing methods, test strategies/plans, and normal, abnormal, and boundary/extreme data (syllabus p. 31). This is a strong later Learn collection despite only two current error-correction-tagged records and no testing-tagged records.

### Data structures and persistent data

- **Records:** section 10.1 requires defining a record structure and reading/writing its fields (syllabus p. 28).
- **Text files:** section 10.3 requires pseudocode for line-based text files (syllabus p. 28).
- **Stacks, queues, and linked lists:** section 10.4 introduces all three, their operations and use cases, and array-backed implementations. At AS Level, candidates need not write full pseudocode implementations of these structures (syllabus p. 29).
- **Data validation:** section 6.2 names range, format, length, presence, existence, limit, and check-digit checks (syllabus p. 24). Although section 6 is theory, validation appears in nine writing records and belongs in an applied Learn path.
- **Advanced files and hashing:** section 13.2 covers serial/sequential/random file organisation, access methods, and hashing (syllabus p. 32). These can follow the introductory text-files lesson.

### Advanced algorithms and programming

- **Searching and sorting:** section 19.1 requires algorithms for linear search, binary search, insertion sort, and bubble sort, including binary-search preconditions and performance considerations (syllabus p. 37).
- **Advanced ADTs:** section 19.1 requires search/insert/delete algorithms across stacks, queues, linked lists, and binary trees, plus dictionaries, graph concepts, ADT composition, and Big O time/space comparison (syllabus p. 37).
- **Recursion:** section 19.2 requires writing and tracing recursive algorithms, knowing when recursion is beneficial, and understanding stacks and unwinding (syllabus p. 37).
- **Programming paradigms:** section 20.1 covers imperative/procedural, object-oriented, declarative, and low-level programming. Its OOP vocabulary includes classes, objects, methods, inheritance, polymorphism, aggregation, encapsulation, getters, and setters (syllabus p. 38).
- **Exception handling:** section 20.2 requires file-processing code and appropriate exception handling (syllabus p. 38).

## Scope guidance for the Learn UI

Use corpus frequency to order lessons, not to exclude syllabus requirements. In particular, Linear Search and Bubble Sort should be visible early because they occur in the question bank and are named at both AS and A Level. Binary Search and Insertion Sort should sit beside them even with zero current records because section 19.1 explicitly requires implementations.

Keep AS and A Level expectations clear inside each lesson. For example, the AS syllabus asks students to use stack/queue/linked-list operations without writing full implementations, while A Level asks for specific find/insert/delete algorithms. Likewise, graph search with A* and Dijkstra's is named in section 18.1, but the syllabus explicitly says candidates need not write graph setup/access/search algorithms (syllabus p. 36); it should be an enrichment lesson rather than an initial pseudocode drill.
