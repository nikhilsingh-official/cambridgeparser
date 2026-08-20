"""OpenRouter grading client for pseudocode question records.

Environment configuration (no secrets in code):

    OPENROUTER_API_KEY   user-provided key; absent -> dry-run only
    OPENROUTER_MODEL          default: google/gemini-2.5-flash (needs structured outputs)
    OPENROUTER_PROVIDER_ONLY  optional comma-separated provider tags/names
    OPENROUTER_PROVIDER_SORT  optional OpenRouter provider sort, e.g. price
    OPENROUTER_BASE_URL       default: https://openrouter.ai/api/v1

The client always returns a ``grading-result/v1`` dict. Dry-run mode
fabricates a deterministic result so the web UI works without network access;
invalid model output is preserved for debugging instead of being hidden.
"""

# import paths rewritten from src.pipeline.grading to api.grading when
# this package moved into the serverless function. Logic unchanged.

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

RESULT_SCHEMA_VERSION = "grading-result/v1"
# Grading needs *guaranteed* JSON, so the default must support strict
# structured-output (json_schema), not a code model with weak schema adherence.
# gemini-2.5-flash is Google's reasoning/coding model ($0.30/$2.50 per 1M,
# ~$0.003 per grade) and grades more accurately than the ultra-cheap tier.
# Cheaper alternates with the same JSON guarantee: google/gemini-2.5-flash-lite,
# openai/gpt-4.1-nano, openai/gpt-4o-mini. Override with OPENROUTER_MODEL (use
# only models that support structured outputs, or the strict schema is rejected).
DEFAULT_MODEL = "google/gemini-2.5-flash"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT_SECONDS = 120
MAX_ATTEMPTS = 2

VALID_CONFIDENCE = {"high", "medium", "low"}

# Strict JSON schema for the grading result. OpenRouter enforces this on models
# that support structured outputs, so the model cannot return prose or a
# malformed object. It mirrors validate_grading_payload() exactly.
GRADING_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "grading_result",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "total_awarded": {"type": "integer"},
                "max_marks": {"type": "integer"},
                "points": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "marking_point_id": {"type": "string"},
                            "awarded": {"type": "boolean"},
                            "marks_awarded": {"type": "integer"},
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                            },
                            "evidence": {"type": "string"},
                            "concerns": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": [
                            "marking_point_id",
                            "awarded",
                            "marks_awarded",
                            "confidence",
                            "evidence",
                            "concerns",
                        ],
                    },
                },
                "overall_explanation": {"type": "string"},
            },
            "required": ["total_awarded", "max_marks", "points", "overall_explanation"],
        },
    },
}

Transport = Callable[[str, Dict[str, str], bytes, int], str]


class OpenRouterConfig:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider_only: Optional[List[str]] = None,
        provider_sort: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
        self.model = model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL
        self.provider_only = provider_only if provider_only is not None else _env_list(
            "OPENROUTER_PROVIDER_ONLY"
        )
        self.provider_sort = (
            provider_sort
            if provider_sort is not None
            else os.environ.get("OPENROUTER_PROVIDER_SORT")
        )
        self.base_url = (
            base_url or os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)


def _env_list(name: str) -> Optional[List[str]]:
    value = os.environ.get(name)
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def _default_transport(url: str, headers: Dict[str, str], body: bytes, timeout: int) -> str:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def group_marking_points(
    marking_points: List[Dict[str, Any]]
) -> List[List[Dict[str, Any]]]:
    """Split marking points into their alternative-solution groups, in order.

    Cambridge mark schemes often print several *alternative* rubrics for the same
    question. The extractor tags each point with ``alt_group``; the groups stay
    separate here (and in the prompt) so alternatives are never merged into one
    additive list. Points without a tag all fall into a single group.
    """
    groups: Dict[int, List[Dict[str, Any]]] = {}
    for point in marking_points:
        key = point.get("alt_group")
        groups.setdefault(key if isinstance(key, int) else 0, []).append(point)
    return [groups[key] for key in sorted(groups)]


def _group_marks(group: List[Dict[str, Any]]) -> int:
    total = 0
    for point in group:
        marks = point.get("marks", 1)
        total += marks if isinstance(marks, int) else 1
    return total


def _compact_exam_text(text: str) -> str:
    """Remove PDF answer-line noise while preserving examiner-relevant wording."""
    if not text:
        return ""

    compacted: List[str] = []
    previous_answer_space = False
    for raw_line in text.splitlines():
        line = re.sub(r"\.{10,}", "[answer space]", raw_line).strip()
        line = re.sub(r"\s+", " ", line)
        if not line or re.fullmatch(r"[, ]+", line):
            previous_answer_space = False
            continue
        if line == "[answer space]":
            if previous_answer_space:
                continue
            previous_answer_space = True
        else:
            previous_answer_space = False
        compacted.append(line)
    return "\n".join(compacted).strip()


def _compact_marking_point(point: Dict[str, Any]) -> Dict[str, Any]:
    compact = {
        "id": str(point.get("id") or ""),
        "text": str(point.get("text") or ""),
        "marks": point.get("marks", 1) if isinstance(point.get("marks", 1), int) else 1,
    }
    alt_group = point.get("alt_group")
    if isinstance(alt_group, int):
        compact["alt_group"] = alt_group
    return compact


def resolve_max_marks(record: Dict[str, Any]) -> Optional[int]:
    """The mark cap for a record: the mark scheme's value, else the best group.

    Never the sum over *all* points — with alternative rubrics that would be
    several times the real total.
    """
    mark_scheme = record.get("mark_scheme") or {}
    for key in ("max_marks", "marks_value"):
        value = mark_scheme.get(key)
        if isinstance(value, int):
            return value
    groups = group_marking_points(mark_scheme.get("marking_points") or [])
    return max((_group_marks(g) for g in groups), default=None)


def apply_max_marks_cap(result: Dict[str, Any], cap: Optional[int]) -> Dict[str, Any]:
    """Clamp ``total_awarded`` to the question's mark cap, in place.

    A safety net for records whose extracted marking points over-expand (several
    alternative rubrics, or a rubric with a "max N" note): even if the model
    awards every point, the record cannot score above the question's marks.
    """
    if not isinstance(cap, int) or cap < 0:
        return result
    total = result.get("total_awarded")
    if not isinstance(total, int):
        total = sum(
            point.get("marks_awarded", 0)
            for point in result.get("points") or []
            if isinstance(point.get("marks_awarded"), int)
        )
    result["max_marks"] = cap
    if total > cap:
        result["total_awarded"] = cap
        result["cap_applied"] = {"reported_total": total, "max_marks": cap}
        explanation = result.get("overall_explanation")
        note = (
            f"Total capped at the question maximum of {cap} "
            f"(marking points supported {total})."
        )
        result["overall_explanation"] = f"{explanation} {note}".strip() if explanation else note
    else:
        result["total_awarded"] = total
    return result


def build_grading_messages(
    record: Dict[str, Any], parsed_answer: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Build chat messages for point-by-point grading of one student answer."""
    mark_scheme = record.get("mark_scheme") or {}
    marking_points = mark_scheme.get("marking_points") or []
    max_marks = resolve_max_marks(record)
    parse = parsed_answer.get("parse") or {}
    groups = group_marking_points(marking_points)

    if len(groups) > 1:
        blocks = []
        for index, group in enumerate(groups):
            lines = "\n".join(
                f"- {point.get('id')}: {point.get('text')} ({point.get('marks', 1)} mark)"
                for point in group
            )
            blocks.append(
                f"ALTERNATIVE SOLUTION {index + 1} "
                f"({_group_marks(group)} mark(s) available):\n{lines}"
            )
        points_lines = "\n\n".join(blocks)
        points_instruction = (
            f"The mark scheme lists {len(groups)} ALTERNATIVE solutions. They are "
            "mutually exclusive: choose the single alternative that best matches "
            "the student's approach, judge each of that alternative's marking "
            "points independently by its id, and award nothing from the other "
            "alternatives. Award marks only when the student's code clearly "
            "satisfies the point. "
            f"total_awarded must never exceed max_marks ({max_marks})."
        )
    elif marking_points:
        points_lines = "\n".join(
            f"- {point.get('id')}: {point.get('text')} ({point.get('marks', 1)} mark)"
            for point in marking_points
        )
        points_instruction = (
            "Judge each marking point independently by its id. Award marks only "
            "when the student's code clearly satisfies the point. "
            f"total_awarded must never exceed max_marks ({max_marks})."
        )
    else:
        points_lines = "(no structured marking points were extracted; derive up to "
        points_lines += f"{max_marks or 6} points from the mark-scheme answer and use ids auto1, auto2, ...)"
        points_instruction = (
            "Derive marking points from the mark-scheme answer text, then judge each "
            "independently."
        )

    payload = {
        "answer_kind": parsed_answer.get("answer_kind") or "pseudocode",
        "question_text": _compact_exam_text(record.get("question_text") or ""),
        "question_context_text": _compact_exam_text(record.get("question_context_text") or ""),
        "mark_scheme_answer_text": _compact_exam_text(mark_scheme.get("answer_text") or ""),
        "max_marks": max_marks,
        "student_source_text": parsed_answer.get("source_text") or "",
        "student_ast": parse.get("ast") or {},
        "parser_ok": parse.get("ok"),
    }
    diagnostics = parse.get("diagnostics") or []
    if diagnostics:
        payload["parser_diagnostics"] = diagnostics
    if marking_points:
        payload["marking_point_ids"] = [
            _compact_marking_point(point) for point in marking_points
        ]

    system = (
        "You are an experienced Cambridge International Computer Science examiner "
        "grading a student's pseudocode answer against mark-scheme marking points. "
        + points_instruction
        + " If the parser reported diagnostics, grade from the source text but "
        "mention the parse problem in your concerns. Respond with STRICT JSON only, "
        "no markdown fences, matching exactly this shape: "
        '{"total_awarded": <int>, "max_marks": <int>, "points": [{"marking_point_id": '
        '"mp1", "awarded": <bool>, "marks_awarded": <int>, "confidence": "high|medium|low", '
        '"evidence": "<quote or description from the student answer>", "concerns": '
        '["<optional strings>"]}], "overall_explanation": "<short paragraph>"}'
    )
    if payload["answer_kind"] == "fill_blank_sheet":
        system += (
            " The student answer is an ordered fill-in-the-blank answer sheet, "
            "not a complete program; match each Blank N answer to its surrounding "
            "line context and do not penalize it for lacking a parseable AST."
        )
    user = (
        "GRADING PACKET (JSON):\n"
        + json.dumps(payload, separators=(",", ":"))
        + "\n\nMARKING POINTS:\n"
        + points_lines
        + "\n\nReturn the strict JSON grading result now."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Parse a JSON object from model output, tolerating code fences."""
    candidate = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(candidate[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def validate_grading_payload(payload: Any) -> Optional[str]:
    """Return an error message when the model payload violates the contract."""
    if not isinstance(payload, dict):
        return "response is not a JSON object"
    if not isinstance(payload.get("total_awarded"), int):
        return "total_awarded must be an integer"
    if not isinstance(payload.get("max_marks"), int):
        return "max_marks must be an integer"
    points = payload.get("points")
    if not isinstance(points, list):
        return "points must be a list"
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            return f"points[{index}] is not an object"
        if not isinstance(point.get("marking_point_id"), str):
            return f"points[{index}].marking_point_id must be a string"
        if not isinstance(point.get("awarded"), bool):
            return f"points[{index}].awarded must be a boolean"
        if not isinstance(point.get("marks_awarded"), int):
            return f"points[{index}].marks_awarded must be an integer"
        confidence = point.get("confidence")
        if confidence is not None and confidence not in VALID_CONFIDENCE:
            return f"points[{index}].confidence must be one of {sorted(VALID_CONFIDENCE)}"
        if not isinstance(point.get("evidence"), str):
            return f"points[{index}].evidence must be a string"
        concerns = point.get("concerns", [])
        if concerns is not None and not isinstance(concerns, list):
            return f"points[{index}].concerns must be a list"
    if not isinstance(payload.get("overall_explanation"), str):
        return "overall_explanation must be a string"
    return None


def dry_run_result(record: Dict[str, Any], parsed_answer: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic fake result for offline testing of the UI and pipeline."""
    mark_scheme = record.get("mark_scheme") or {}
    marking_points = mark_scheme.get("marking_points") or []
    parse_ok = bool(((parsed_answer.get("parse") or {}).get("ok")))
    gradable_answer = parse_ok or parsed_answer.get("answer_kind") == "fill_blank_sheet"
    points = []
    total = 0
    for index, point in enumerate(marking_points):
        awarded = gradable_answer and index % 2 == 0
        marks = int(point.get("marks", 1)) if awarded else 0
        total += marks
        points.append(
            {
                "marking_point_id": str(point.get("id") or f"mp{index + 1}"),
                "awarded": awarded,
                "marks_awarded": marks,
                "confidence": "low",
                "evidence": "DRY RUN: no model was called; this is a fabricated decision.",
                "concerns": ["dry-run mode"],
            }
        )
    max_marks = resolve_max_marks(record)
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "ok": True,
        "dry_run": True,
        "model": "dry-run",
        "provider": "none",
        "result": apply_max_marks_cap(
            {
                "total_awarded": total,
                "max_marks": max_marks if isinstance(max_marks, int) else total,
                "points": points,
                "overall_explanation": (
                    "DRY RUN: deterministic placeholder grading. Set "
                    "GOOGLE_AI_STUDIO_API_KEY (or OPENROUTER_API_KEY) to grade "
                    "with the real model."
                ),
            },
            max_marks,
        ),
        "error": None,
        "raw_response": None,
    }


def grade_answer(
    record: Dict[str, Any],
    parsed_answer: Dict[str, Any],
    config: Optional[OpenRouterConfig] = None,
    dry_run: Optional[bool] = None,
    transport: Optional[Transport] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Grade one answer. Returns a grading-result/v1 dict, never raises.

    ``dry_run=None`` auto-selects: dry-run when no API key is configured.
    """
    config = config or OpenRouterConfig()
    if dry_run is None:
        dry_run = not config.has_api_key
    if dry_run:
        return dry_run_result(record, parsed_answer)
    if not config.has_api_key:
        return {
            "schema_version": RESULT_SCHEMA_VERSION,
            "ok": False,
            "dry_run": False,
            "model": config.model,
            "provider": "openrouter",
            "result": None,
            "error": "OPENROUTER_API_KEY is not set",
            "raw_response": None,
        }

    messages = build_grading_messages(record, parsed_answer)
    request_payload: Dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "temperature": 0,
        "response_format": GRADING_RESPONSE_FORMAT,
        "provider": {"require_parameters": True},
    }
    if config.provider_only:
        request_payload["provider"]["only"] = config.provider_only
    if config.provider_sort:
        request_payload["provider"]["sort"] = config.provider_sort
    body = json.dumps(request_payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "pseudocode-grading",
    }
    url = f"{config.base_url}/chat/completions"
    send = transport or _default_transport

    last_error: Optional[str] = None
    raw_response: Optional[str] = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw_response = send(url, headers, body, timeout)
        except urllib.error.HTTPError as error:
            detail = ""
            try:
                detail = error.read().decode("utf-8", "replace")[:500]
            except Exception:  # noqa: BLE001 - best-effort detail capture
                pass
            last_error = f"HTTP {error.code}: {detail or error.reason}"
            if error.code in (429, 500, 502, 503) and attempt < MAX_ATTEMPTS:
                continue
            break
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = f"network error: {error}"
            if attempt < MAX_ATTEMPTS:
                continue
            break

        try:
            envelope = json.loads(raw_response)
            content = envelope["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            last_error = f"unexpected OpenRouter response shape: {error}"
            break

        payload = _extract_json_object(content)
        validation_error = validate_grading_payload(payload)
        if validation_error is not None:
            last_error = f"model returned invalid grading JSON: {validation_error}"
            raw_response = content
            break

        return {
            "schema_version": RESULT_SCHEMA_VERSION,
            "ok": True,
            "dry_run": False,
            "model": config.model,
            "provider": "openrouter",
            "result": apply_max_marks_cap(payload, resolve_max_marks(record)),
            "error": None,
            "raw_response": content,
        }

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "ok": False,
        "dry_run": False,
        "model": config.model,
        "provider": "openrouter",
        "result": None,
        "error": last_error or "unknown error",
        "raw_response": raw_response,
    }
