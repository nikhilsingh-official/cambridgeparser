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
MP_ITEM_PATTERN = re.compile(r"^\s*MP\s*(\d+)\b[.):\-\s]*(.*)$", re.IGNORECASE)
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
    r"^(note\b|n\.?b\.?\b|alternative\b|example\s+(?:solution|of)"
    r"|expected\s+output|guidance\b|or)\s*:?\s*$",
    re.IGNORECASE,
)
META_PREFIX_PATTERN = re.compile(
    r"^(note\s*:|alternative\b|example\s+(?:solution|of)|expected\s+output|guidance\s*:)",
    re.IGNORECASE,
)
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
# "(max 8)" inline in a header line, e.g. "One mark for each of the following (max 8):".
MAX_MARKS_INLINE_PATTERN = re.compile(r"\(\s*max(?:imum)?\.?\s*(\d+)", re.IGNORECASE)
CODE_LINE_PATTERN = re.compile(
    r"^\s*(?:DECLARE|CONSTANT|FUNCTION|ENDFUNCTION|PROCEDURE|ENDPROCEDURE|IF\b|ELSE\b|ENDIF|"
    r"WHILE\b|ENDWHILE|REPEAT\b|UNTIL\b|FOR\b|NEXT\b|CASE\b|ENDCASE|INPUT\b|OUTPUT\b|RETURNS?\b|"
    r"OPENFILE|READFILE|WRITEFILE|CLOSEFILE|CALL\b|TYPE\b|ENDTYPE)"
)
# Further hints that a line is example-solution code, not rubric prose: the
# pseudocode assignment arrow (real "<-" glyph or the mark-scheme font's
# private-use glyph) and end-of-block keywords.
CODE_HINT_PATTERN = re.compile("(?:\\u2190|\\uf0ac|:=|\\bENDFUNCTION\\b|\\bENDPROCEDURE\\b|\\bENDWHILE\\b|\\bENDFOR\\b)")


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
    return bool(CODE_LINE_PATTERN.match(stripped) or CODE_HINT_PATTERN.search(stripped))


def _mp_item(stripped: str) -> Optional[tuple[int, str]]:
    """Return the (number, description) of a real MP-label item, or None.

    A genuine ``MPn`` rubric line carries a natural-language description. The
    inline convention (``MP1 MP2`` on a gap, or ``NEXT HardQ MP5`` appended to a
    code line) is rejected: MPn must open the line and must not be immediately
    followed by another MPn token. Out-of-sequence numbers (a wrapped
    "``MP4`` to generate ..." cross-reference) are filtered by the caller.
    """

    match = MP_ITEM_PATTERN.match(stripped)
    if not match:
        return None
    remainder = match.group(2).strip()
    if re.match(r"^MP\s*\d", remainder, re.IGNORECASE):
        return None
    return int(match.group(1)), remainder


def _numbered_item(stripped: str) -> Optional[str]:
    match = NUM_ITEM_PATTERN.match(stripped)
    if not match:
        return None
    separator, text = match.group(2), match.group(3).strip()
    if not text or not re.search(r"[A-Za-z]", text):
        return None
    # A bare "2 OUTPUT ..." with no separator is a circled mark digit on a code
    # line, or a row of an expected-output table ("1 : OUTPUT \"1\""); leading
    # punctuation is stripped before the code check so both are rejected.
    if separator is None and _is_code_line(re.sub(r"^[^0-9A-Za-z]+", "", text)):
        return None
    return text


def _bullet_item(raw: str) -> Optional[str]:
    match = BULLET_LINE_PATTERN.match(raw)
    if not match:
        return None
    text = match.group(1).strip()
    if not text or _is_code_line(text):
        return None
    return text


def _scan_rubric_items(lines: list[str]) -> tuple[list[Dict[str, Any]], bool, bool]:
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
            last_mp_number = 0
            if ONE_MARK_HEADER_PATTERN.search(stripped):
                one_mark_header_seen = True
            continue

        if (
            STOP_LINE_PATTERN.match(stripped)
            or MAX_MARKS_PATTERN.match(stripped)
            or META_BOUNDARY_PATTERN.match(stripped)
            or META_PREFIX_PATTERN.match(stripped)
        ):
            flush()
            if ALT_MARKER_PATTERN.match(stripped):
                pending_alt = True
            last_mp_number = 0
            continue

        mp = _mp_item(stripped)
        if mp is not None and mp[0] > last_mp_number:
            flush()
            last_mp_number = mp[0]
            begin_item(mp[1], "mp_label", "high", number=mp[0])
            continue

        # A numbered-looking line that the code guard rejects (a circled mark
        # digit or an expected-output row) is a boundary, never a continuation.
        if mp is None and NUM_ITEM_PATTERN.match(stripped):
            text = _numbered_item(stripped)
            if text is not None:
                flush()
                number = int(NUM_ITEM_PATTERN.match(stripped).group(1))
                begin_item(
                    text, "numbered_list", "high" if header_seen else "medium", number=number
                )
            else:
                flush()
            continue

        bullet = _bullet_item(raw)
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
    return None


def _extract_marking_points(text: Optional[str]) -> list[str]:
    """Legacy list-of-strings API, kept for the standalone CLI path."""

    return [point["text"] for point in extract_structured_marking_points(text)["points"]]


def extract_structured_marking_points(text: Optional[str]) -> Dict[str, Any]:
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

    mp_points = [item for item in items if item["style"] == "mp_label"]
    numbered_points = [item for item in items if item["style"] == "numbered_list"]
    bullet_points = [item for item in items if item["style"] in ("bullet", "one_mark_bullet")]

    if mp_points:
        chosen = mp_points
    elif numbered_points and (header_seen or len(numbered_points) >= 2):
        chosen = numbered_points
    elif bullet_points and (header_seen or len(bullet_points) >= 2):
        chosen = bullet_points
    else:
        chosen = []

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
    return _clean_item_text(text)


def _valid_span_bbox(bbox: Any) -> bool:
    return (
        isinstance(bbox, (list, tuple))
        and len(bbox) == 4
        and all(isinstance(v, (int, float)) for v in bbox)
    )


def marking_points_from_underlined_spans(
    spans: Any, target_marks: Optional[int] = None, line_tolerance: float = 6.0
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

    valid = [
        s for s in spans or [] if (s.get("text") or "").strip() and _valid_span_bbox(s.get("bbox"))
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

    points: list[Dict[str, Any]] = []
    for root in order:
        text = _clean_underline_text(" ".join(grouped[root]))
        if text:
            points.append(
                {
                    "id": f"mp{len(points) + 1}",
                    "text": text,
                    "marks": 1,
                    "confidence": "high",
                    "style": "underlined",
                    "alt_group": 0,
                }
            )
    return points


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
