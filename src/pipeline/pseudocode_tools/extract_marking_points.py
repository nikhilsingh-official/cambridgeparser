"""Extract MP-style marking points from mark scheme text for pseudocode questions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


# One marking-point item, in any of the styles Cambridge mixes. The separator
# group in NUM_ITEM_PATTERN distinguishes real numbered items ("1. Text" /
# "1) Text" and the 9618-style bare "1 Text") from circled mark digits rendered
# inline with example code ("2 OUTPUT ..."): bare-digit items whose text looks
# like code are noise, rejected by a code guard at the call site.
MP_ITEM_PATTERN = re.compile(r"^\s*MP\s*(\d+)\b([.):\-\s]*)(.*)$", re.IGNORECASE)
NUM_ITEM_PATTERN = re.compile(r"^\s*(\d+)([.)])?\s+(.*)$")

# Rubric headers that introduce a marking list. "mark as follows" and the
# circled/descriptions phrasings are distinctive enough to match anywhere in a
# line (they carry leading context like "For loop-based solutions, mark as
# follows:"); the "N mark(s) for/per" family is anchored to the line start so it
# is not mistaken for the same words inside an item's description.
HEADER_PATTERNS = (
    re.compile(r"mark\s+as\s+follows", re.IGNORECASE),
    re.compile(r"mark\s+point.{0,40}?circled", re.IGNORECASE),
    re.compile(r"descriptions?\s+as\s+below", re.IGNORECASE),
    re.compile(
        r"^\s*(?:for\b[^:]{0,60}?,\s*)?(?:award\s+)?"
        r"(?:one|two|three|four|five|six|\d+)\s+marks?\s+(?:for|per)\b",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*award\s+(?:one|\d+)\s+marks?\b", re.IGNORECASE),
)
STOP_LINE_PATTERN = re.compile(
    r"^(total\b|answer\s+scheme\b|guidance\b)",
    re.IGNORECASE,
)
# Meta / guidance lines that close the current item without becoming one or
# extending it: notes, alternative-solution headings, example-solution labels,
# and standalone "OR" separators between answer variants.
META_BOUNDARY_PATTERN = re.compile(
    r"^(notes?\b|n\.?b\.?\b|alternative\b|example\s+(?:solution|of)"
    r"|expected\s+output|guidance\b|or)\s*:?\s*$",
    re.IGNORECASE,
)
META_PREFIX_PATTERN = re.compile(
    r"^(notes?\s*:|alternative\b|example\s+(?:solution|of)|expected\s+output|guidance\s*:)",
    re.IGNORECASE,
)
# Marking guidance that references points by number ("Mark points 7 and 8 must
# not be nested") is a note about how the listed marks combine, not a criterion.
# A digit right after "point(s)" separates it from the "Mark points as circled"
# rubric header, which never leads with a number.
MARK_POINT_NOTE_PATTERN = re.compile(r"^\s*mark\s+points?\s+\d", re.IGNORECASE)
# A boundary that introduces a *different solution*, so its marking points form a
# new alternative group (a "Note" or "Max" boundary does not — same solution).
ALT_MARKER_PATTERN = re.compile(r"^\s*(alternative|example\b.*\bsolution|or)\b", re.IGNORECASE)
LEADING_TRIM_PATTERN = re.compile(r"^[\s•\-\–\—:.)]+")

# Structured extraction additions. Cambridge mark schemes mix several rubric
# styles; each extracted point records which style produced it.
BULLET_LINE_PATTERN = re.compile("^\\s*(?:•|\uf0b7|\uf0a7|◦|▪|-|–|—)\\s*(.*)$")
# The "one mark per/for" subset drives the one_mark_bullet style and confidence.
ONE_MARK_HEADER_PATTERN = re.compile(
    r"^\s*(?:one|1)\s+marks?\s+(?:per|for)\b", re.IGNORECASE
)
MAX_MARKS_PATTERN = re.compile(r"^\s*max(?:imum)?\.?\s*(?:of\s*)?(\d+)\s*(?:marks?)?\b", re.IGNORECASE)
# A cap declared inside a header line: "One mark per point (Max 8):" or "1 mark
# for each of the following up to max 5 marks:". Such schemes deliberately list
# more criteria than there are marks, so the cap is what the grader must honour.
MAX_MARKS_INLINE_PATTERN = re.compile(
    r"(?:\(|\bup\s+to\s+)\s*max(?:imum)?\.?\s*(?:of\s+)?(\d+)", re.IGNORECASE
)
# The same cap written without a bracket or "up to": "Note: Max 7 marks" on a
# line of its own after the list, or "Mark as follows Max 6 marks:" above it.
# A bare "Max n" is only trusted on a line that is *about* the marking — inside
# a marking point "Max" is ordinary prose ("compare with Max 255").
MAX_MARKS_BARE_PATTERN = re.compile(
    r"\bmax(?:imum)?\.?\s*(?:of\s+)?(\d+)\b", re.IGNORECASE
)
MAX_MARKS_CONTEXT_PATTERN = re.compile(
    r"^\s*(?:notes?\b|n\.?b\.?\b)|\bmark(?:ed|ing)?\s+as\s+follows\b"
    r"|^\s*(?:one|1)\s+marks?\s+(?:per|for)\b",
    re.IGNORECASE,
)
# "Note: Max 7 if CharCount not used to store count" caps a *penalty*, not the
# list: it applies only when the student's answer has that fault, so it must
# never be read as the number of marking points on offer.
CONDITIONAL_MAX_PATTERN = re.compile(
    r"^\s*(?:marks?\b\s*)?(?:if|unless|when|where|provided|for)\b", re.IGNORECASE
)
CODE_LINE_PATTERN = re.compile(
    r"^\s*(?:DECLARE|CONSTANT|FUNCTION|ENDFUNCTION|PROCEDURE|ENDPROCEDURE|IF\b|ELSE\b|ENDIF|"
    r"WHILE\b|ENDWHILE|REPEAT\b|UNTIL\b|FOR\b|NEXT\b|CASE\b|ENDCASE|INPUT\b|OUTPUT\b|RETURNS?\b|"
    r"OPENFILE|READFILE|WRITEFILE|CLOSEFILE|CALL\b|TYPE\b|ENDTYPE)"
)
# Further hints that a line is example-solution code, not rubric prose: the
# pseudocode assignment arrow (real "<-" glyph or the mark-scheme font's
# private-use glyph) and end-of-block keywords.
CODE_HINT_PATTERN = re.compile("(?:\\u2190|\\uf0ac|:=|\\bENDFUNCTION\\b|\\bENDPROCEDURE\\b|\\bENDWHILE\\b|\\bENDFOR\\b)")
# A routine header opening an example solution, written in mixed case ("Function
# Status(Actual, Min, Max : INTEGER) RETURNS CHAR") where the case-sensitive
# keyword list above does not reach. The name-then-bracket shape alone is not
# enough — rubric items say "Function heading (inc parameters) and ending" — so a
# typed parameter or a RETURNS clause must also be present. The keyword list must
# stay case-sensitive for the same reason: rubric items legitimately begin "If
# Rnum is a duplicate ..." or "For each element ...".
_ROUTINE_HEAD = r"^\s*(?:FUNCTION|PROCEDURE)\s+[A-Za-z_]\w*\s*\("
CODE_HEADER_PATTERN = re.compile(
    rf"{_ROUTINE_HEAD}(?=[^)]*:)|{_ROUTINE_HEAD}[^)]*\)\s*RETURNS\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract MP1/MP2-style marking points from pseudocode mark scheme text."
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_writing_final_qp_ms_context.json"),
        help="Final pseudocode-writing JSON containing ms_entry data.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("pseudocode_writing_hits/pseudocode_writing_final_qp_ms_marking_points.json"),
        help="Output JSON with marking_points added to each record.",
    )
    return parser.parse_args()


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _normalize_marker(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("(") and text.endswith(")") and len(text) > 2:
        text = text[1:-1]
    return text


def _is_header(stripped: str) -> bool:
    return any(pattern.search(stripped) for pattern in HEADER_PATTERNS)


def _is_code_line(stripped: str) -> bool:
    return bool(
        CODE_LINE_PATTERN.match(stripped)
        or CODE_HEADER_PATTERN.match(stripped)
        or CODE_HINT_PATTERN.search(stripped)
    )


def _mp_item(stripped: str) -> Optional[tuple[int, str]]:
    """Return the (number, description) of a real MP-label item, or None.

    A genuine ``MPn`` rubric line carries a natural-language description. The
    inline convention (``MP1 MP2`` on a gap, or ``NEXT HardQ MP5`` appended to a
    code line) is rejected: MPn must open the line and must not be immediately
    followed by another MPn token. Out-of-sequence numbers (a wrapped
    "``MP4`` to generate ..." cross-reference) are filtered by the caller.

    A closing bracket straight after the number ("MP3) in a loop") closes a
    parenthetical that began on the previous line — "(after reasonable attempt
    at MP3)" — so it is a cross-reference, not a rubric item.
    """

    match = MP_ITEM_PATTERN.match(stripped)
    if not match:
        return None
    separator, remainder = match.group(2), match.group(3).strip()
    if ")" in separator:
        return None
    if re.match(r"^MP\s*\d", remainder, re.IGNORECASE):
        return None
    return int(match.group(1)), remainder


def _numbered_item(stripped: str, in_sequence: bool = False) -> Optional[str]:
    """The description of a numbered rubric item, or None if the line is noise.

    ``in_sequence`` says the caller has a rubric header and this line's number is
    the next one expected. That makes the line part of a list whose structure we
    can already see, so the code guard below is skipped: rubric items routinely
    *name* the construct they mark ("FOR loop", "CASE OF ThisMark ... ENDCASE",
    "OPENFILE in WRITE mode and subsequent CLOSE in a loop"), which is
    indistinguishable from code by wording alone.
    """
    match = NUM_ITEM_PATTERN.match(stripped)
    if not match:
        return None
    separator, text = match.group(2), match.group(3).strip()
    if not text or not re.search(r"[A-Za-z]", text):
        return None
    # A bare "2 OUTPUT ..." with no separator is a circled mark digit on a code
    # line, or a row of an expected-output table ("1 : OUTPUT \"1\""); leading
    # punctuation is stripped before the code check so both are rejected. Those
    # digits sit in the example solution and do not form a run, so an in-sequence
    # line after a header is never one of them.
    if separator is None and not in_sequence and _is_code_line(re.sub(r"^[^0-9A-Za-z]+", "", text)):
        return None
    return text


def _bullet_item(raw: str, in_list: bool = False) -> Optional[str]:
    """The description of a bulleted rubric item, or None if the line is noise.

    ``in_list`` says a rubric header has been seen, so the bullets below it are
    the marking list and a code-like one ("• OUTPUT statement") is still an item.
    Without that context the guard stands, to skip bulleted example code.
    """
    match = BULLET_LINE_PATTERN.match(raw)
    if not match:
        return None
    text = match.group(1).strip()
    if not text or (not in_list and _is_code_line(text)):
        return None
    return text


def _scan_rubric_items(
    lines: list[str],
) -> tuple[list[Dict[str, Any]], bool, bool]:
    """Scan mark-scheme lines into ordered marking-point items.

    Returns (items, header_seen, one_mark_header_seen). Each item is a dict with
    ``text``, ``style`` and a provisional ``confidence``. A single pass handles
    the three interchangeable Cambridge styles (MP labels, numbered lists,
    bullets) under optional headers; continuation lines extend the current item,
    while code lines and stop lines close it. Style priority and header gating
    are applied by the caller.
    """

    items: list[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    header_seen = False
    one_mark_header_seen = False
    last_mp_number = 0
    last_list_number = 0
    # Whether we are *currently* inside the rubric list. Unlike header_seen this
    # is revoked by any meta boundary: after "Expected output:" the numbered
    # lines below are a demonstration, not a continuation of the marking list.
    in_rubric_list = False
    group = 0
    group_has_items = False
    group_high_number = 0
    pending_alt = False

    def flush() -> None:
        nonlocal current
        if current is not None and current["text"].strip():
            items.append(current)
        current = None

    def begin_item(
        text: str, style: str, confidence: str, number: Optional[int] = None
    ) -> None:
        # A new rubric block only becomes a separate alternative group once its
        # numbering actually restarts. Mark schemes freely drop asides like
        # "ALTERNATIVE using nested IFs:" into the middle of one rubric, and the
        # list continues across them (MP3 after MP2), so the marker alone is not
        # enough. Unnumbered items have no restart to observe, so the marker
        # decides for them.
        nonlocal current, group, group_has_items, group_high_number, pending_alt
        if pending_alt and group_has_items and (number is None or number <= group_high_number):
            group += 1
            group_has_items = False
            group_high_number = 0
        pending_alt = False
        current = {"text": text, "style": style, "confidence": confidence, "group": group}
        group_has_items = True
        if number is not None:
            group_high_number = max(group_high_number, number)

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            flush()
            continue

        # Headers first: "Mark as follows" also matches the STOP "mark" prefix,
        # and "1 mark for each" also matches a numbered item, so header wins.
        # A header or an alternative-solution boundary starts a fresh rubric
        # block, so MP numbering restarts (an alternative may reuse "MP1").
        if _is_header(stripped) and not stripped.lower().startswith("mp"):
            flush()
            pending_alt = True
            header_seen = True
            in_rubric_list = True
            last_mp_number = 0
            last_list_number = 0
            if ONE_MARK_HEADER_PATTERN.search(stripped):
                one_mark_header_seen = True
            continue

        if (
            STOP_LINE_PATTERN.match(stripped)
            or MAX_MARKS_PATTERN.match(stripped)
            or META_BOUNDARY_PATTERN.match(stripped)
            or META_PREFIX_PATTERN.match(stripped)
            or MARK_POINT_NOTE_PATTERN.match(stripped)
        ):
            flush()
            if ALT_MARKER_PATTERN.match(stripped):
                pending_alt = True
            last_mp_number = 0
            last_list_number = 0
            in_rubric_list = False
            continue

        mp = _mp_item(stripped)
        if mp is not None and mp[0] > last_mp_number:
            flush()
            last_mp_number = mp[0]
            begin_item(mp[1], "mp_label", "high", number=mp[0])
            continue

        # A numbered-looking line that the code guard rejects (a circled mark
        # digit or an expected-output row) is a boundary, never a continuation.
        num_match = NUM_ITEM_PATTERN.match(stripped)
        if mp is None and num_match:
            number = int(num_match.group(1))
            text = _numbered_item(
                stripped, in_sequence=in_rubric_list and number == last_list_number + 1
            )
            # A real list counts upwards. A number that does not advance is a
            # wrapped description that happens to start with a digit ("...if not
            # equal write" / "3 lines to NewFile in a loop"), so it continues the
            # current item. Only an alternative rubric may restart the count.
            backwards = number <= last_list_number and not pending_alt
            if text is not None and not backwards:
                flush()
                last_list_number = number
                begin_item(
                    text, "numbered_list", "high" if header_seen else "medium", number=number
                )
                continue
            if text is not None and backwards:
                if current is not None:
                    current["text"] = f"{current['text']} {stripped}".strip()
                continue
            flush()
            continue

        bullet = _bullet_item(raw, in_list=in_rubric_list)
        if bullet is not None:
            flush()
            style = "one_mark_bullet" if one_mark_header_seen else "bullet"
            begin_item(bullet, style, "high" if header_seen else "medium")
            continue

        if _is_code_line(stripped):
            flush()
            continue

        # Otherwise a continuation of the current item's wrapped description.
        if current is not None:
            current["text"] = f"{current['text']} {stripped}".strip()

    flush()
    return items, header_seen, one_mark_header_seen


def _clean_item_text(text: str) -> str:
    """Drop stray annotation glyphs and collapse whitespace in an item.

    Cambridge marking tables sprinkle guillemets/private-use glyphs to bracket
    "linked" marks (e.g. "4 ... flip operation «" / "5 « Correct number of
    iterations"); they are annotation, not content. Meaningful ellipsis
    phrasing is preserved.
    """

    cleaned = re.sub("[«»‹›]", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def _detect_max_marks(lines: list[str]) -> Optional[int]:
    for line in lines:
        stripped = line.strip()
        match = MAX_MARKS_PATTERN.match(stripped)
        if match:
            return int(match.group(1))
        inline = MAX_MARKS_INLINE_PATTERN.search(stripped)
        if inline:
            return int(inline.group(1))
        if MAX_MARKS_CONTEXT_PATTERN.search(stripped):
            bare = MAX_MARKS_BARE_PATTERN.search(stripped)
            if bare and not CONDITIONAL_MAX_PATTERN.match(stripped[bare.end() :]):
                return int(bare.group(1))
    return None


def _extract_marking_points(text: Optional[str]) -> list[str]:
    """Legacy list-of-strings API, kept for the standalone CLI path."""

    return [point["text"] for point in extract_structured_marking_points(text)["points"]]


def _select_items(items: list[Dict[str, Any]], header_seen: bool) -> list[Dict[str, Any]]:
    """Pick the one rubric style that carries the marks.

    Styles do not mix within a node. MP labels win over a numbered list only when
    they could plausibly be the rubric themselves — a stray cross-reference
    ("Note: MP6: both counts must have been declared") is one mp_label against a
    real seven-item numbered rubric and must not discard it. Numbered items and
    bullets without a header are trusted only in pairs, to skip stray numbered
    code lines.
    """
    mp_points = [item for item in items if item["style"] == "mp_label"]
    numbered_points = [item for item in items if item["style"] == "numbered_list"]
    bullet_points = [item for item in items if item["style"] in ("bullet", "one_mark_bullet")]

    if mp_points and len(mp_points) >= len(numbered_points):
        return mp_points
    if numbered_points and (header_seen or len(numbered_points) >= 2):
        return numbered_points
    if bullet_points and (header_seen or len(bullet_points) >= 2):
        return bullet_points
    return []


def extract_structured_marking_points(
    text: Optional[str],
) -> Dict[str, Any]:
    """Extract structured marking points from mark-scheme answer text.

    Returns {"points": [{id, text, marks, confidence, style}], "max_marks": int|None}.

    A single line scanner recognises the interchangeable Cambridge rubric styles
    — explicit ``MPn`` labels, numbered lists (dotted, parenthesised, or the
    9618 bare-digit form), and bullet lists — under flexible headers such as
    "Mark as follows", "For loop-based solutions, mark as follows:",
    "One mark for each of the following (max 8):", and "Mark points as circled,
    descriptions as below:". Example-solution code lines never become points,
    and the inline-``MPn`` convention (marks shown as gaps in the code) yields no
    spurious text points.

    Styles do not mix within one node: MP labels win over numbered lists, which
    win over bullets. Numbered/bullet items without any header are accepted only
    when there are at least two of them, to avoid stray numbered code lines.

    When a mark scheme lists several *alternative solutions* (each its own rubric
    block), every point carries an ``alt_group`` index for the block it came
    from. Points are deduplicated only *within* a group, so alternatives stay
    separate rather than being merged into one additive list; ``alt_group_count``
    reports how many alternative groups are present.
    """
    if not text:
        return {"points": [], "max_marks": None, "alt_group_count": 0}

    lines = text.splitlines()
    max_marks = _detect_max_marks(lines)
    items, header_seen, _ = _scan_rubric_items(lines)
    chosen = _select_items(items, header_seen)

    points: list[Dict[str, Any]] = []
    seen_per_group: Dict[int, set] = {}
    # Renumber alternative groups compactly (the chosen style may skip some).
    group_remap: Dict[int, int] = {}
    for item in chosen:
        text = _clean_item_text(item["text"])
        raw_group = item.get("group", 0)
        key = text.lower()
        if not text or key in seen_per_group.setdefault(raw_group, set()):
            continue
        seen_per_group[raw_group].add(key)
        alt_group = group_remap.setdefault(raw_group, len(group_remap))
        points.append(
            {
                "id": f"mp{len(points) + 1}",
                "text": text,
                "marks": 1,
                "confidence": item["confidence"],
                "style": item["style"],
                "alt_group": alt_group,
            }
        )

    return {
        "points": points,
        "max_marks": max_marks,
        "alt_group_count": len(group_remap),
    }


# Private-use glyphs the mark-scheme font uses for pseudocode operators.
_GLYPH_REPLACEMENTS = {"\uf0ac": "\u2190", "\uf0e0": "\u2192", "\uf0b3": "\u2265", "\uf0a3": "\u2264"}


def _clean_underline_text(text: str) -> str:
    for glyph, replacement in _GLYPH_REPLACEMENTS.items():
        text = text.replace(glyph, replacement)
    # A trailing "/" is half of the "//" that separates alternative answers; the
    # underline often runs one character into it.
    return _clean_item_text(text).rstrip("/").strip()


# The rubric line that *declares* the convention underlines its own key word
# ("One mark per <u>underlined</u> word / expression"), so that word arrives as a
# span alongside the real answer spans. A marking point is always answer content,
# never the name of the convention, so these are dropped outright.
# A label opening the same answer restated in a real programming language. The
# scheme marks whichever language the candidate used, so these are alternatives.
LANGUAGE_VARIANT_PATTERN = re.compile(
    r"^(VB|VB\.NET|Visual\s+Basic|Pascal|Delphi|Python|Java|C#|C\+\+)\s*:", re.IGNORECASE
)
# A scheme that declares its marks are carried by styling — underlined or bold
# part-statements, highlighted phrases — rather than by a written list.
STYLE_CONVENTION_PATTERN = re.compile(
    r"(?:one|1)\s+mark\s+(?:for\s+each|per)[^\n]{0,60}"
    r"(underlined?|bold|highlighted?|part-?statement)",
    re.IGNORECASE,
)


def declares_style_convention(answer_text: Optional[str]) -> bool:
    """Whether the scheme says its marks are the styled spans in the answer."""
    return bool(answer_text and STYLE_CONVENTION_PATTERN.search(answer_text))


CONVENTION_WORD_PATTERN = re.compile(
    r"^(underlined?|highlighted?|bold(?:ed|ened)?|emboldened|circled|italic(?:s|ised)?)$",
    re.IGNORECASE,
)


def _valid_span_bbox(bbox: Any) -> bool:
    return (
        isinstance(bbox, (list, tuple))
        and len(bbox) == 4
        and all(isinstance(v, (int, float)) for v in bbox)
    )


# Where a single underlined declaration divides into separate marks, in the order
# Cambridge splits them. A whole "one mark per underlined part" header or
# declaration arrives as one continuous underlined run — the PDF gives no
# sub-span structure, because the styling never changes across it — so the marks
# have to come from the declaration's own syntax: the return clause, then each
# parameter, then the element type of an array.
_DECLARATION_BOUNDARIES = (
    (0, re.compile(r"\s+(?=\bRETURNS\b)", re.IGNORECASE)),
    (1, re.compile(r",\s*")),
    (2, re.compile(r"\s+(?=\bOF\b)", re.IGNORECASE)),
)


def _split_declarations(runs: list[str], parts: int) -> list[str]:
    """Divide underlined declaration runs into ``parts`` pieces at syntax breaks.

    Splits the highest-priority boundary available, longest piece first, until
    the target is reached or no boundary is left — so runs that cannot be divided
    that far are returned as far as they got rather than chopped arbitrarily.
    A header split across two lines arrives as two runs, and the extra marks may
    live in either, so every run is a candidate.
    """
    pieces = list(runs)
    while len(pieces) < parts:
        best = None
        for index, piece in enumerate(pieces):
            for priority, pattern in _DECLARATION_BOUNDARIES:
                match = pattern.search(piece)
                if not match or not piece[match.end():].strip():
                    continue
                candidate = (priority, -len(piece), index, match.start(), match.end())
                if best is None or candidate < best:
                    best = candidate
                break
        if best is None:
            break
        _priority, _length, index, start, end = best
        piece = pieces[index]
        pieces[index : index + 1] = [piece[:start].strip(), piece[end:].strip()]
    return [piece for piece in pieces if piece]


def _comment_only_texts(answer_text: Optional[str]) -> set:
    """Underlined fragments that only ever appear inside a ``//`` comment line.

    Mark schemes underline commented-out variants ("// NextChar =
    UCASE(NextChar)") to show an accepted alternative phrasing. Those are not
    separate marks, so a fragment seen exclusively on comment lines is dropped —
    a fragment that also appears in live code is kept.
    """
    if not answer_text:
        return set()
    commented: set = set()
    live: list[str] = []
    for line in answer_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            commented.add(_clean_underline_text(stripped.lstrip("/").strip()))
        else:
            live.append(stripped)
    commented.discard("")
    return {text for text in commented if not any(text in line for line in live)}


def _alt_boundary_lines(answer_text: Optional[str]) -> set:
    """Answer-line indices at which a new alternative solution begins.

    Two conventions produce one: a line ending in "//" offers the *next* line as
    an alternative form ("DECLARE Item : ARRAY [1:2000] OF Component//"), and a
    language-variant label opens a whole restatement of the answer in another
    language ("VB: Dim Lookup(0 to 127) As CHAR"). Neither adds marks.
    """
    if not answer_text:
        return set()
    boundaries = set()
    for index, line in enumerate(answer_text.splitlines()):
        stripped = line.strip()
        if stripped.endswith("//") and not stripped.startswith("//"):
            boundaries.add(index + 1)
        if LANGUAGE_VARIANT_PATTERN.match(stripped):
            boundaries.add(index)
    return boundaries


def marking_points_from_underlined_spans(
    spans: Any,
    target_marks: Optional[int] = None,
    line_tolerance: float = 6.0,
    answer_text: Optional[str] = None,
) -> list[Dict[str, Any]]:
    """Turn a node's underlined spans into marking points.

    Cambridge "one mark per underlined word / expression" schemes leave no text
    rubric; the marks *are* the underlined runs in the model answer, recovered by
    ms_parser via ``TEXT_COLLECT_STYLES``. Underline boundaries alone are
    ambiguous — a single statement may be several style-split spans, while
    several words on one line may be several marks — so ``target_marks`` (the
    node's mark value) drives granularity: starting from one group per span, the
    smallest same-line gaps are merged until exactly ``target_marks`` groups
    remain. Without a target, spans are merged per line (one mark per line).
    """

    commented = _comment_only_texts(answer_text)
    valid = [
        s
        for s in spans or []
        if (s.get("text") or "").strip()
        and _valid_span_bbox(s.get("bbox"))
        and not CONVENTION_WORD_PATTERN.match((s.get("text") or "").strip())
        and _clean_underline_text(s.get("text") or "") not in commented
    ]
    if not valid:
        return []

    # Cluster spans into visual lines, then read each line left to right. A pure
    # (y, x) sort misorders spans whose baselines differ slightly (e.g. the "←"
    # operator glyph sits a touch higher than its neighbours).
    lines: list[list[Dict[str, Any]]] = []
    for span in sorted(valid, key=lambda s: (s["bbox"][1] + s["bbox"][3]) / 2.0):
        mid = (span["bbox"][1] + span["bbox"][3]) / 2.0
        if lines and abs(mid - lines[-1][0]) <= line_tolerance:
            lines[-1][1].append(span)  # type: ignore[index]
        else:
            lines.append([mid, [span]])  # type: ignore[list-item]
    ordered: list[Dict[str, Any]] = []
    line_of: list[int] = []
    for line_index, (_mid, line_spans) in enumerate(lines):
        for span in sorted(line_spans, key=lambda s: s["bbox"][0]):
            ordered.append(span)
            line_of.append(line_index)

    count = len(ordered)
    parent = list(range(count))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    # Candidate merges: consecutive spans on the same text line, cheapest gap first.
    edges = []
    for i in range(1, count):
        if line_of[i] != line_of[i - 1]:
            continue
        gap = ordered[i]["bbox"][0] - ordered[i - 1]["bbox"][2]
        edges.append((gap, i - 1, i))
    edges.sort(key=lambda e: e[0])

    target = target_marks if isinstance(target_marks, int) and target_marks > 0 else None
    groups = count
    for _gap, left, right in edges:
        if target is not None and groups <= target:
            break
        if find(left) != find(right):
            parent[find(right)] = find(left)
            groups -= 1

    grouped: Dict[int, list[str]] = {}
    order: list[int] = []
    for i in range(count):
        root = find(i)
        if root not in grouped:
            grouped[root] = []
            order.append(root)
        grouped[root].append(ordered[i]["text"])

    boundaries = _alt_boundary_lines(answer_text)
    answer_lines = (answer_text or "").splitlines()

    def alt_group_for(text: str) -> int:
        # Locate the point in the answer, then count the alternative boundaries
        # at or above it. Points that cannot be located stay in the first group.
        if not boundaries:
            return 0
        for index, line in enumerate(answer_lines):
            if text and text in _clean_underline_text(line):
                return sum(1 for start in boundaries if start <= index)
        return 0

    runs: list[tuple[int, str]] = []
    for root in order:
        text = _clean_underline_text(" ".join(grouped[root]))
        if text:
            runs.append((alt_group_for(text), text))

    # Merging can only ever reach the target from above. A run that still holds
    # several marks — a whole header underlined in one go — has to be divided at
    # its syntax breaks instead. The target counts marks per alternative, since
    # alternatives are mutually exclusive.
    if target is not None:
        by_group: Dict[int, list[str]] = {}
        for group, text in runs:
            by_group.setdefault(group, []).append(text)
        # Only when *no* group reaches the target is the answer genuinely
        # under-split. A group that already has its marks means the short ones
        # beside it are supplementary — the "VB:" / "Pascal:" restatements of a
        # solution, worth a mark or two, not the whole question again.
        if all(len(texts) < target for texts in by_group.values()):
            split: list[tuple[int, str]] = []
            for group, texts in by_group.items():
                split.extend((group, text) for text in _split_declarations(texts, target))
            runs = split

    return [
        {
            "id": f"mp{index}",
            "text": text,
            "marks": 1,
            "confidence": "high",
            "style": "underlined",
            "alt_group": group,
        }
        for index, (group, text) in enumerate(runs, start=1)
    ]


def _find_primary_node(ms_entry: Dict[str, Any], primary_marker: Any) -> Optional[Dict[str, Any]]:
    target = _normalize_marker(primary_marker)
    for part in ms_entry.get("primary_subparts", []):
        primary = part.get("primary") or {}
        if _normalize_marker(primary.get("text")) == target:
            return part
    return None


def _find_ms_node(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ms_entry = record.get("ms_entry")
    if not isinstance(ms_entry, dict):
        return None

    level = record.get("ms_level") or record.get("segment_kind")
    if level == "question":
        return ms_entry.get("question")
    if level == "primary":
        primary_part = _find_primary_node(ms_entry, record.get("primary_marker"))
        if primary_part:
            return primary_part.get("primary")
        return None
    if level == "secondary":
        primary_part = _find_primary_node(ms_entry, record.get("primary_marker"))
        if not primary_part:
            return None
        target = _normalize_marker(record.get("secondary_marker"))
        for subpart in primary_part.get("secondary_subparts", []):
            secondary = subpart.get("secondary") or {}
            if _normalize_marker(secondary.get("text")) == target:
                return secondary
        return None
    return None


def _apply_marking_points(records: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    with_points = 0
    total = 0
    for record in records:
        total += 1
        node = _find_ms_node(record)
        answer_text = node.get("answer_text") if isinstance(node, dict) else None
        marking_points = _extract_marking_points(answer_text)
        record["marking_points"] = marking_points
        if marking_points:
            with_points += 1
    return {"total": total, "with_points": with_points, "without_points": total - with_points}


def main() -> int:
    args = parse_args()
    payload = _read_json(args.input_json)
    records = payload.get("records", [])
    if isinstance(records, list):
        stats = _apply_marking_points(records)
        summary = payload.get("summary")
        if isinstance(summary, dict):
            summary["marking_points"] = {
                "records_total": stats["total"],
                "records_with_points": stats["with_points"],
                "records_without_points": stats["without_points"],
                "source_field": "ms_entry.answer_text",
            }
    _write_json(args.output_json, payload)
    print(f"Wrote marking points to {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
