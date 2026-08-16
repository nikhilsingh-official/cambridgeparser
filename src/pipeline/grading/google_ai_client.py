"""Google AI Studio (Gemini API) grading client.

This is the *primary* grading path. It calls the Generative Language API
directly with the same prompt, the same strict JSON contract, and the same
``grading-result/v1`` envelope as the OpenRouter client, so the two are
interchangeable from the caller's point of view.

    GOOGLE_AI_STUDIO_API_KEY  required; set in Vercel's project environment
    GOOGLE_AI_MODEL           default: gemini-2.5-flash-lite
    GOOGLE_AI_BASE_URL        default: https://generativelanguage.googleapis.com/v1beta
    GOOGLE_AI_THINKING_BUDGET optional; sends generationConfig.thinkingConfig

Going direct rather than through OpenRouter removes the reseller margin, and
Flash-Lite's output tokens are ~6x cheaper than gemini-2.5-flash's. When Google
rate-limits us the caller falls back to OpenRouter -- see
``grading.router.grade_answer_with_fallback``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from src.pipeline.grading.openrouter_client import (
    RESULT_SCHEMA_VERSION,
    Transport,
    _extract_json_object,
    apply_max_marks_cap,
    build_grading_messages,
    dry_run_result,
    resolve_max_marks,
    validate_grading_payload,
)

DEFAULT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_TIMEOUT_SECONDS = 120
MAX_ATTEMPTS = 2
PROVIDER = "google-ai-studio"

# Gemini validates responses against an OpenAPI 3.0 *subset*: type, enum, items,
# properties, required and propertyOrdering are honoured, but JSON Schema's
# `additionalProperties` is not accepted. This mirrors GRADING_RESPONSE_FORMAT's
# schema in openrouter_client, minus that key, and both mirror
# validate_grading_payload() -- the real contract, enforced on every response
# regardless of provider.
GRADING_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "total_awarded": {"type": "integer"},
        "max_marks": {"type": "integer"},
        "points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "marking_point_id": {"type": "string"},
                    "awarded": {"type": "boolean"},
                    "marks_awarded": {"type": "integer"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
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
                "propertyOrdering": [
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
    "propertyOrdering": ["total_awarded", "max_marks", "points", "overall_explanation"],
}


class RateLimited(Exception):
    """Google refused the call for quota reasons; the caller should fall back."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class GoogleAIConfig:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        thinking_budget: Optional[int] = None,
    ) -> None:
        self.api_key = (
            api_key
            if api_key is not None
            else os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
        )
        self.model = model or os.environ.get("GOOGLE_AI_MODEL") or DEFAULT_MODEL
        self.base_url = (
            base_url or os.environ.get("GOOGLE_AI_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        # Flash-Lite does not think by default, so this stays unset unless asked
        # for. Sending an unsupported generationConfig key fails the whole call,
        # and a silent grading outage costs more than a few thinking tokens.
        self.thinking_budget = (
            thinking_budget
            if thinking_budget is not None
            else _env_int("GOOGLE_AI_THINKING_BUDGET")
        )

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)


def _env_int(name: str) -> Optional[int]:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _default_transport(url: str, headers: Dict[str, str], body: bytes, timeout: int) -> str:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def to_gemini_request(
    messages: List[Dict[str, str]],
    *,
    schema: Optional[Dict[str, Any]] = None,
    thinking_budget: Optional[int] = None,
) -> Dict[str, Any]:
    """Convert OpenAI-style chat messages into a generateContent payload.

    ``system`` messages become ``systemInstruction``; everything else becomes a
    ``contents`` turn, with ``assistant`` renamed to Gemini's ``model`` role.
    """
    system_parts: List[Dict[str, str]] = []
    contents: List[Dict[str, Any]] = []
    for message in messages:
        text = message.get("content") or ""
        role = message.get("role")
        if role == "system":
            system_parts.append({"text": text})
            continue
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}],
            }
        )

    generation_config: Dict[str, Any] = {
        "temperature": 0,
        "responseMimeType": "application/json",
        "responseSchema": schema if schema is not None else GRADING_RESPONSE_SCHEMA,
    }
    if thinking_budget is not None:
        generation_config["thinkingConfig"] = {"thinkingBudget": thinking_budget}

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": generation_config,
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": system_parts}
    return payload


def extract_text(envelope: Dict[str, Any]) -> str:
    """Pull the model's text out of a generateContent response."""
    candidate = (envelope.get("candidates") or [])[0]
    parts = ((candidate.get("content") or {}).get("parts")) or []
    text = "".join(part.get("text") or "" for part in parts)
    if not text:
        reason = candidate.get("finishReason") or "no text in response"
        raise ValueError(f"empty completion ({reason})")
    return text


def is_rate_limit(code: int, detail: str) -> bool:
    """True when Google is refusing on quota rather than on the request itself."""
    if code == 429:
        return True
    return "RESOURCE_EXHAUSTED" in detail


def _failure(
    config: GoogleAIConfig,
    error: str,
    raw_response: Optional[str],
    *,
    rate_limited: bool = False,
) -> Dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "ok": False,
        "dry_run": False,
        "model": config.model,
        "provider": PROVIDER,
        "result": None,
        "error": error,
        "raw_response": raw_response,
        "rate_limited": rate_limited,
    }


def grade_answer_google(
    record: Dict[str, Any],
    parsed_answer: Dict[str, Any],
    config: Optional[GoogleAIConfig] = None,
    dry_run: Optional[bool] = None,
    transport: Optional[Transport] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Grade one answer via Gemini. Returns grading-result/v1, never raises."""
    config = config or GoogleAIConfig()
    if dry_run is None:
        dry_run = not config.has_api_key
    if dry_run:
        return dry_run_result(record, parsed_answer)
    if not config.has_api_key:
        return _failure(config, "GOOGLE_AI_STUDIO_API_KEY is not set", None)

    messages = build_grading_messages(record, parsed_answer)
    body = json.dumps(
        to_gemini_request(messages, thinking_budget=config.thinking_budget)
    ).encode("utf-8")
    headers = {
        # The key travels as a header, not a query parameter, so it cannot leak
        # into request logs or error strings that quote the URL.
        "x-goog-api-key": config.api_key or "",
        "Content-Type": "application/json",
    }
    url = f"{config.base_url}/models/{config.model}:generateContent"
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
            if is_rate_limit(error.code, detail):
                # Do not burn the retry here: OpenRouter is the better next hop.
                return _failure(config, last_error, raw_response, rate_limited=True)
            if error.code in (500, 502, 503) and attempt < MAX_ATTEMPTS:
                continue
            break
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = f"network error: {error}"
            if attempt < MAX_ATTEMPTS:
                continue
            break

        try:
            content = extract_text(json.loads(raw_response))
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as error:
            last_error = f"unexpected Google AI response shape: {error}"
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
            "provider": PROVIDER,
            "result": apply_max_marks_cap(payload, resolve_max_marks(record)),
            "error": None,
            "raw_response": content,
        }

    return _failure(config, last_error or "unknown error", raw_response)
