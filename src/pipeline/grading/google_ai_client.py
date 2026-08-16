"""Google AI Studio (Gemini API) grading client.

This is the *primary* grading path. It calls the Generative Language API
directly with the same prompt, the same strict JSON contract, and the same
``grading-result/v1`` envelope as the OpenRouter client, so the two are
interchangeable from the caller's point of view.

    GOOGLE_AI_STUDIO_API_KEY  required; set in Vercel's project environment
    GOOGLE_AI_MODELS          comma-separated rotation; default DEFAULT_ROTATION
    GOOGLE_AI_MODEL           pins one model, disabling the rotation
    GOOGLE_AI_BASE_URL        default: https://generativelanguage.googleapis.com/v1beta
    GOOGLE_AI_THINKING_BUDGET optional; sends generationConfig.thinkingConfig

AI Studio meters each model separately, so spreading requests across models
multiplies the free allowance. Rotating *keys* would not: Google applies rate
limits per project, not per key. When every free model is exhausted the caller
falls back to OpenRouter -- see ``grading.router.grade_answer_routed``.
"""

from __future__ import annotations

import hashlib
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

# Free-tier *capacity* picks the default here, not per-token price. Measured at
# ~1.6K tokens per grade, AI Studio's free limits work out to:
#
#   gemma-4-31b-it        16K TPM -> ~10 grades/min, 14,400/day
#   gemini-3.1-flash-lite 15 RPM  -> ~15 grades/min,     500/day
#
# Flash-Lite's 500/day is ten users at the 50/day account quota, so Gemma leads
# and Flash-Lite is the next hop; both are free before OpenRouter costs money.
# The eval harness put them level on marks (exact 32/45 each, MAE 0.38 vs 0.33).
DEFAULT_MODEL = "gemma-4-31b-it"

# AI Studio meters each model separately, so rotating models multiplies free
# capacity in a way rotating *keys* cannot (limits are per project, not per
# key). Every entry was verified against the real grading payload -- HTTP 200
# and a reply passing validate_grading_payload() -- with its measured latency:
#
#   gemini-3.5-flash-lite  2.0s      gemma-4-31b-it        10.3s
#   gemini-3.6-flash       3.5s      gemini-3.1-flash-lite 13.7s
#
# Verified but excluded: gemini-3.5-flash works and is correct, but averaged
# 35.3s -- one slow model in the rotation would make one question in N crawl.
# Rejected outright: gemini-3.7-flash (503), gemini-3-flash / gemini-2.5-flash
# / gemini-2.5-flash-lite (404, closed to new keys), gemma-4-26b-a4b-it (timed
# out past 120s). Re-run scratchpad/probe_models.py before adding any model.
DEFAULT_ROTATION: List[str] = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemma-4-31b-it",
    "gemini-3.1-flash-lite",
]
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
        models: Optional[List[str]] = None,
    ) -> None:
        self.api_key = (
            api_key
            if api_key is not None
            else os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
        )
        # A single pinned model always wins over the rotation. The eval harness
        # depends on this: comparing models is meaningless if the rotation can
        # answer with a different one mid-run.
        pinned = model or os.environ.get("GOOGLE_AI_MODEL")
        if models is not None:
            self.models = list(models)
        elif pinned:
            self.models = [pinned]
        else:
            self.models = _env_list("GOOGLE_AI_MODELS") or list(DEFAULT_ROTATION)
        self.models = self.models or [DEFAULT_MODEL]
        self.model = self.models[0]
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

    def rotation_for(self, key: Any = None) -> List[str]:
        """The rotation, ordered so ``key`` deterministically picks the head.

        Keying on the question id spreads load across models while keeping one
        question on one model, so two students answering the same question are
        marked by the same grader. Models differ in generosity -- the eval put
        gemma-4-31b-it at 11 over-awards to 2 under, against 8/5 for
        gemini-3.1-flash-lite -- so an unkeyed rotation would decide marks by
        coin flip. Without a key, order is preserved.
        """
        models = list(self.models)
        if key is None or len(models) < 2:
            return models
        digest = hashlib.sha256(str(key).encode("utf-8")).digest()
        offset = int.from_bytes(digest[:4], "big") % len(models)
        return models[offset:] + models[:offset]

    def for_model(self, model: str) -> "GoogleAIConfig":
        """A copy pinned to one model, so the rotation never mutates shared state."""
        return GoogleAIConfig(
            api_key=self.api_key,
            base_url=self.base_url,
            thinking_budget=self.thinking_budget,
            models=[model],
        )


def _env_list(name: str) -> Optional[List[str]]:
    value = os.environ.get(name)
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


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


def classify_failure(code: int, detail: str) -> Optional[str]:
    """Name the failures worth retrying on the other provider, else None.

    Two cases are Google's problem rather than ours, and OpenRouter may well
    serve the same request:

    ``rate_limit``        quota refusal (429, or RESOURCE_EXHAUSTED in the body,
                          which Google sometimes returns as 403).
    ``model_unavailable`` the model is gone for this key (404 / NOT_FOUND) --
                          how gemini-2.5-flash-lite broke: retired for new users
                          while OpenRouter still served it.

    Everything else (a 400, a bad schema) is our bug; retrying it elsewhere
    would only spend money to fail twice.
    """
    if code == 429 or "RESOURCE_EXHAUSTED" in detail:
        return "rate_limit"
    if code == 404 or "NOT_FOUND" in detail:
        return "model_unavailable"
    return None


def _failure(
    config: GoogleAIConfig,
    error: str,
    raw_response: Optional[str],
    *,
    fallback_reason: Optional[str] = None,
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
        "fallback_reason": fallback_reason,
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
            fallback_reason = classify_failure(error.code, detail)
            if fallback_reason is not None:
                # Do not burn the retry here: OpenRouter is the better next hop.
                return _failure(
                    config, last_error, raw_response, fallback_reason=fallback_reason
                )
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
