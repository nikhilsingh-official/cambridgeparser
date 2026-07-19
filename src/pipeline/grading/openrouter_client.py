"""OpenRouter grading client for pseudocode question records.

Environment configuration (no secrets in code):

    OPENROUTER_API_KEY   user-provided key; absent -> dry-run only
    OPENROUTER_MODEL     default: qwen/qwen2.5-coder-7b-instruct
    OPENROUTER_BASE_URL  default: https://openrouter.ai/api/v1

The client always returns a ``grading-result/v1`` dict. Dry-run mode
fabricates a deterministic result so the web UI works without network access;
invalid model output is preserved for debugging instead of being hidden.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

RESULT_SCHEMA_VERSION = "grading-result/v1"
DEFAULT_MODEL = "qwen/qwen2.5-coder-7b-instruct"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT_SECONDS = 120
MAX_ATTEMPTS = 2

VALID_CONFIDENCE = {"high", "medium", "low"}

Transport = Callable[[str, Dict[str, str], bytes, int], str]


class OpenRouterConfig:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
        self.model = model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL
        self.base_url = (
            base_url or os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)


def _default_transport(url: str, headers: Dict[str, str], body: bytes, timeout: int) -> str:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def build_grading_messages(
    record: Dict[str, Any], parsed_answer: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Build chat messages for point-by-point grading of one student answer."""
    mark_scheme = record.get("mark_scheme") or {}
    marking_points = mark_scheme.get("marking_points") or []
    max_marks = mark_scheme.get("max_marks")
    parse = parsed_answer.get("parse") or {}

    if marking_points:
        points_lines = "\n".join(
            f"- {point.get('id')}: {point.get('text')} ({point.get('marks', 1)} mark)"
            for point in marking_points
        )
        points_instruction = (
            "Judge each marking point independently by its id. Award marks only "
            "when the student's code clearly satisfies the point."
        )
    else:
        points_lines = "(no structured marking points were extracted; derive up to "
        points_lines += f"{max_marks or 6} points from the mark-scheme answer and use ids auto1, auto2, ...)"
        points_instruction = (
            "Derive marking points from the mark-scheme answer text, then judge each "
            "independently."
        )

    payload = {
        "question_text": record.get("question_text") or "",
        "question_context_text": record.get("question_context_text") or "",
        "mark_scheme_answer_text": mark_scheme.get("answer_text") or "",
        "max_marks": max_marks,
        "marking_points": marking_points,
        "student_source_text": parsed_answer.get("source_text") or "",
        "student_ast": parse.get("ast") or {},
        "parser_ok": parse.get("ok"),
        "parser_diagnostics": parse.get("diagnostics") or [],
    }

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
    user = (
        "GRADING PACKET (JSON):\n"
        + json.dumps(payload, indent=2)
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
    points = []
    total = 0
    for index, point in enumerate(marking_points):
        awarded = parse_ok and index % 2 == 0
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
    max_marks = mark_scheme.get("max_marks")
    if not isinstance(max_marks, int):
        max_marks = sum(int(point.get("marks", 1)) for point in marking_points)
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "ok": True,
        "dry_run": True,
        "model": "dry-run",
        "provider": "none",
        "result": {
            "total_awarded": total,
            "max_marks": max_marks,
            "points": points,
            "overall_explanation": (
                "DRY RUN: deterministic placeholder grading. Set OPENROUTER_API_KEY "
                "to grade with the real model."
            ),
        },
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
    body = json.dumps(
        {
            "model": config.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
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
            "result": payload,
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
