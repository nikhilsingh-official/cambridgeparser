"""Controlled syllabus-tag vocabulary for pseudocode-writing question records.

Every tag maps to a numbered subsection of the Cambridge International AS & A
Level Computer Science 9618 syllabus (``Computer Science Syllabus.pdf`` in the
repository root). Tagging against the syllabus rather than free-form keywords
keeps the labels stable, lets the website group questions the way a teaching
scheme does, and makes a wrong tag checkable: if no syllabus subsection covers
it, it does not belong in the vocabulary.

Only the sections a *pseudocode-writing* question can exercise are represented.
Papers 1/3 theory areas (data representation, networks, ethics, ...) are out of
scope by construction, with the exception of 6.2 data validation, which turns up
constantly as the thing an algorithm has to implement.

The per-record assignments live in :mod:`question_tag_assignments`; this module
owns the vocabulary and the validation used when they are applied.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple


class SyllabusTag(NamedTuple):
    """One vocabulary entry: a stable slug bound to a syllabus subsection."""

    slug: str
    label: str
    syllabus_ref: str
    description: str


# Top-level syllabus sections, named as the 9618 contents page names them. Only
# the sections the vocabulary draws on are listed. The website groups filter
# facets by these, so keeping the names here means the frontend needs no
# syllabus knowledge of its own.
SYLLABUS_SECTIONS: Dict[str, str] = {
    "6": "Security, privacy and data integrity",
    "9": "Algorithm Design and Problem-solving",
    "10": "Data Types and Structures",
    "11": "Programming",
    "12": "Software Development",
    "13": "Data Representation",
    "19": "Computational thinking and Problem-solving",
    "20": "Further Programming",
}


def section_of(syllabus_ref: str) -> str:
    """Top-level section number for a reference such as ``10.2 / 19.1``.

    Dual references name the AS subsection first and the A Level one second;
    grouping follows the first, so bubble sort files under 10 Data Types and
    Structures rather than 19.
    """

    return syllabus_ref.split("/")[0].strip().split(".")[0]


# fmt: off
_TAGS: List[SyllabusTag] = [
    # 6.2 Data Integrity — the validation methods an algorithm is asked to code.
    SyllabusTag("validation", "Data validation", "6.2",
                "Range, length, presence, format, or check-digit validation of input data."),

    # 9 Algorithm Design and Problem-solving
    SyllabusTag("abstraction", "Abstraction", "9.1",
                "Modelling a system by including only the essential detail."),
    SyllabusTag("decomposition", "Decomposition", "9.1",
                "Breaking a problem into sub-problems / program modules."),
    SyllabusTag("identifier-table", "Identifier table", "9.2",
                "Choosing identifier names and data types and recording them in an identifier table."),
    SyllabusTag("structured-english", "Structured English", "9.2",
                "Writing pseudocode from (or producing) a structured English description."),
    SyllabusTag("flowchart", "Flowchart", "9.2",
                "Writing pseudocode from a flowchart, or drawing a flowchart from pseudocode."),
    SyllabusTag("stepwise-refinement", "Stepwise refinement", "9.2",
                "Refining an algorithm to a level of detail that can be programmed."),
    SyllabusTag("logic-statements", "Logic statements", "9.2",
                "Using logic statements / Boolean conditions to define part of a solution."),

    # 10.1 Data Types and Records
    SyllabusTag("data-types", "Data types", "10.1",
                "Selecting and declaring non-composite types: INTEGER, REAL, CHAR, STRING, BOOLEAN, DATE."),
    SyllabusTag("records", "Record structures", "10.1",
                "Defining a record type and reading from / writing to its fields."),

    # 10.2 Arrays
    SyllabusTag("arrays-1d", "1D arrays", "10.2",
                "Declaring and using a one-dimensional array, including bounds and indexing."),
    SyllabusTag("arrays-2d", "2D arrays", "10.2",
                "Declaring and using a two-dimensional array, usually with nested loops."),
    SyllabusTag("array-processing", "Array processing", "10.2",
                "Traversing an array to total, count, find a maximum/minimum, or otherwise process its data."),
    SyllabusTag("bubble-sort", "Bubble sort", "10.2 / 19.1",
                "Implementing or completing a bubble sort, including flag- and boundary-optimised variants."),
    SyllabusTag("linear-search", "Linear search", "10.2 / 19.1",
                "Searching a data set item by item until a match is found."),

    # 10.3 Files
    SyllabusTag("text-files", "Text file handling", "10.3",
                "OPENFILE / READFILE / WRITEFILE / CLOSEFILE on line-based text files, including EOF."),

    # 10.4 / 19.1 Abstract Data Types
    SyllabusTag("adt-stack", "Stack", "10.4 / 19.1",
                "Push / pop operations on a stack, including its array implementation."),
    SyllabusTag("adt-queue", "Queue", "10.4 / 19.1",
                "Enqueue / dequeue operations on a (usually circular) queue."),
    SyllabusTag("adt-linked-list", "Linked list", "10.4 / 19.1",
                "Traversing, inserting into, or deleting from a linked list and its free list."),

    # 11.1 Programming Basics
    SyllabusTag("variables-constants", "Variables and constants", "11.1",
                "Declaring variables, declaring and initialising constants, and assigning values."),
    SyllabusTag("input-output", "Input and output", "11.1",
                "Keyboard input and console output, including prompts and formatted messages."),
    SyllabusTag("operators-expressions", "Operators and expressions", "11.1",
                "Arithmetic, relational, and logical operators used to build expressions."),
    SyllabusTag("built-in-functions", "Built-in functions", "11.1",
                "Calling library routines such as DIV, MOD, ROUND, RAND, or a supplied function."),
    SyllabusTag("string-handling", "String handling", "11.1",
                "String manipulation with LENGTH, LEFT, RIGHT, MID, UCASE, LCASE, and concatenation."),

    # 11.2 Constructs
    SyllabusTag("selection-if", "IF selection", "11.2",
                "IF ... THEN ... ELSE ... ENDIF, including nested IF statements."),
    SyllabusTag("selection-case", "CASE selection", "11.2",
                "CASE OF ... OTHERWISE ... ENDCASE structures."),
    SyllabusTag("count-controlled-loop", "Count-controlled loop", "11.2",
                "FOR ... NEXT loops, including a STEP value."),
    SyllabusTag("pre-condition-loop", "Pre-condition loop", "11.2",
                "WHILE ... ENDWHILE loops."),
    SyllabusTag("post-condition-loop", "Post-condition loop", "11.2",
                "REPEAT ... UNTIL loops."),
    SyllabusTag("nested-loops", "Nested loops", "11.2",
                "One loop inside another, typically to process a 2D structure or compare pairs."),

    # 11.3 Structured Programming
    SyllabusTag("procedures", "Procedures", "11.3",
                "Defining and calling a procedure with PROCEDURE ... ENDPROCEDURE / CALL."),
    SyllabusTag("functions", "Functions", "11.3",
                "Defining and calling a function that RETURNs a value used in an expression."),
    SyllabusTag("parameters", "Parameters", "11.3",
                "Passing parameters, including BYREF / BYVAL and matching argument types."),

    # 12 Software Development
    SyllabusTag("structure-chart", "Structure chart", "12.2",
                "Deriving pseudocode from a structure chart or expressing modules and their parameters."),
    SyllabusTag("state-transition", "State-transition diagram", "12.2",
                "Documenting or implementing an algorithm described by a state-transition diagram."),
    SyllabusTag("error-correction", "Error identification and correction", "12.3",
                "Locating syntax, logic, or run-time errors in given code and correcting them."),
    SyllabusTag("testing", "Testing and trace", "12.3",
                "Dry runs, trace tables, and choosing normal / abnormal / boundary test data."),

    # 13 Data Representation (A Level)
    SyllabusTag("user-defined-types", "User-defined types", "13.1",
                "Enumerated types, pointers, sets, and other user-defined non-composite types."),
    SyllabusTag("file-organisation", "File organisation and access", "13.2",
                "Serial, sequential, and random file organisation and the matching access methods."),
    SyllabusTag("hashing", "Hashing", "13.2",
                "Applying a hashing algorithm to place or locate a record in a random file."),

    # 19 Computational thinking and Problem-solving (A Level)
    SyllabusTag("binary-search", "Binary search", "19.1",
                "Implementing a binary search over ordered data."),
    SyllabusTag("insertion-sort", "Insertion sort", "19.1",
                "Implementing an insertion sort."),
    SyllabusTag("binary-tree", "Binary tree", "19.1",
                "Finding or inserting an item in a binary tree held in arrays."),
    SyllabusTag("graphs", "Graphs", "19.1",
                "Graph ADTs, adjacency matrices and lists."),
    SyllabusTag("dictionary", "Dictionary", "19.1",
                "Dictionary / key-value ADT operations."),
    SyllabusTag("complexity", "Algorithm complexity", "19.1",
                "Comparing algorithms by time or space cost, including Big O notation."),
    SyllabusTag("recursion", "Recursion", "19.2",
                "Writing or tracing an algorithm that calls itself, with a base case."),

    # 20 Further Programming (A Level)
    SyllabusTag("oop-classes", "Classes and objects", "20.1",
                "Designing classes, constructors, getters/setters, and instantiating objects."),
    SyllabusTag("inheritance", "Inheritance", "20.1",
                "Deriving a subclass from a superclass, including INHERITS and overriding."),
    SyllabusTag("polymorphism", "Polymorphism", "20.1",
                "Overridden methods resolved by the object's actual class."),
    SyllabusTag("encapsulation", "Encapsulation", "20.1",
                "PRIVATE attributes exposed through PUBLIC methods."),
    SyllabusTag("declarative-programming", "Declarative programming", "20.1",
                "Expressing a solution as facts and rules and satisfying a goal."),
    SyllabusTag("low-level-programming", "Low-level programming", "20.1",
                "Assembly-level code and addressing modes."),
    SyllabusTag("file-processing", "Random and sequential file processing", "20.2",
                "Opening in read/write/append mode and reading or writing whole records."),
    SyllabusTag("exception-handling", "Exception handling", "20.2",
                "TRY ... EXCEPT ... ENDTRY and deciding when exception handling is appropriate."),
]
# fmt: on

TAGS_BY_SLUG: Dict[str, SyllabusTag] = {tag.slug: tag for tag in _TAGS}
VALID_SLUGS = frozenset(TAGS_BY_SLUG)

MIN_TAGS_PER_QUESTION = 4
MAX_TAGS_PER_QUESTION = 5


def validate_tags(slugs: List[str], *, context: str = "") -> List[str]:
    """Return ``slugs`` unchanged, or raise ``ValueError`` describing the fault.

    Enforces the vocabulary, the 4-5 tag count the corpus is tagged to, and
    uniqueness. Raising rather than dropping keeps a typo from silently
    shrinking a question's tag set.
    """

    where = f" for {context}" if context else ""
    unknown = [slug for slug in slugs if slug not in VALID_SLUGS]
    if unknown:
        raise ValueError(f"unknown syllabus tag(s){where}: {', '.join(sorted(unknown))}")
    if len(set(slugs)) != len(slugs):
        raise ValueError(f"duplicate syllabus tag(s){where}: {', '.join(sorted(slugs))}")
    if not MIN_TAGS_PER_QUESTION <= len(slugs) <= MAX_TAGS_PER_QUESTION:
        raise ValueError(
            f"expected {MIN_TAGS_PER_QUESTION}-{MAX_TAGS_PER_QUESTION} tags{where}, got {len(slugs)}"
        )
    return slugs


def describe(slug: str) -> Dict[str, str]:
    """Expand a slug into the label/reference payload the website renders.

    Carries the section as well as the subsection so the filter panel can group
    facets ("11 Programming") straight from a record, without fetching the
    vocabulary separately or duplicating the section names in the frontend.
    """

    tag = TAGS_BY_SLUG[slug]
    section = section_of(tag.syllabus_ref)
    return {
        "slug": tag.slug,
        "label": tag.label,
        "syllabus_ref": tag.syllabus_ref,
        "section": section,
        "section_label": SYLLABUS_SECTIONS[section],
        "description": tag.description,
    }
