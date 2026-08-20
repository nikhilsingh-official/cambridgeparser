"""Vercel Function for authenticated AI grading.

# the auth and quota halves of this module were rewritten for Supabase;
# the grading pipeline call below is unchanged.

The Vue client sends a Supabase access token and a compact answer payload to
this same-origin endpoint.  The function validates the token with Supabase Auth,
loads the trusted question by id, and calls the shared grading pipeline.

Grading runs on Google AI Studio (``GOOGLE_AI_STUDIO_API_KEY``) and falls back
to OpenRouter (``OPENROUTER_API_KEY``) when Google rate-limits us.  Both keys
are read from Vercel's server-side environment and never reach the browser.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from typing import Any, Mapping

from api._quota import QuotaUnavailable, RateLimitExceeded, consume_quota
from api.grade_one import grade_request, load_record


GRADING_RESULT_SCHEMA = "grading-result/v1"
MAX_REQUEST_BYTES = 256_000
OPENROUTER_TIMEOUT_SECONDS = 50
# Both are public project identifiers, not secrets: the anon key grants only
# what Row Level Security allows.  Kept as environment variables so a preview
# deployment can point at a different project without a code change.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get(
    "SUPABASE_ANON_KEY",
    "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH",
)


def _error(message: str) -> dict[str, Any]:
    return {
        "schema_version": GRADING_RESULT_SCHEMA,
        "ok": False,
        "result": None,
        "error": message,
    }


def _trusted_mark_scheme(record_id: Any) -> dict[str, Any] | None:
    try:
        record = load_record(record_id)
    except Exception:  # noqa: BLE001 - public responses must remain JSON-shaped
        return None
    return (record.get("mark_scheme") or {}) if record else None


def _error_for_record(message: str, request_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build an error that can still reveal the submitted record's mark scheme."""

    payload = _error(message)
    mark_scheme = _trusted_mark_scheme(request_payload.get("record_id"))
    if mark_scheme is not None:
        payload["mark_scheme"] = mark_scheme
    return payload


def _bearer_token(headers: Mapping[str, str]) -> str:
    scheme, _, token = (headers.get("Authorization") or "").partition(" ")
    if scheme.casefold() != "bearer" or not token:
        raise ValueError("missing bearer token")
    return token


def _verify_supabase_token(token: str) -> str:
    """Return the Supabase user id for a valid access token.

    Asking Supabase to resolve the token, rather than verifying the JWT
    signature here, keeps this function free of any secret: it needs only the
    public anon key and the caller's own token.  That is the same property the
    Firebase version had, and it means a leak of this function's environment
    exposes no ability to mint or impersonate a session.  The cost is one
    network round trip per grading request, which is negligible beside the
    model call that follows.

    It also means a revoked or signed-out session is rejected immediately,
    which local signature verification would not catch until expiry.
    """

    request = urllib.request.Request(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": SUPABASE_ANON_KEY,
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    uid = payload.get("id") if isinstance(payload, dict) else None
    if not isinstance(uid, str) or not uid:
        raise ValueError("token did not resolve to a Supabase user")
    return uid


def handle_grade(
    method: str,
    headers: Mapping[str, str],
    body: bytes,
) -> tuple[int, dict[str, Any]]:
    """Handle one HTTP request and return ``(status, JSON payload)``."""

    if method != "POST":
        return 405, _error("POST required (this endpoint grades one submission)")
    if len(body) > MAX_REQUEST_BYTES:
        return 413, _error("request is too large")

    try:
        token = _bearer_token(headers)
        # The uid is not needed here any more - consume_grading_quota() derives
        # it from the token inside the database - but verifying up front still
        # earns its round trip: it turns an unauthenticated call into a clean
        # 401 before the record load and the model call.
        _verify_supabase_token(token)
    except (ValueError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return 401, _error("Sign in is required to use AI grading.")

    try:
        request_payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return 400, _error(f"invalid request JSON: {error}")
    if not isinstance(request_payload, dict):
        return 400, _error("request JSON must be an object")

    # Google AI Studio is the primary provider; OpenRouter is the rate-limit
    # fallback. Either key alone is enough to grade.
    has_google_key = bool(os.environ.get("GOOGLE_AI_STUDIO_API_KEY"))
    has_openrouter_key = bool(os.environ.get("OPENROUTER_API_KEY"))
    if not has_google_key and not has_openrouter_key:
        return 503, _error_for_record(
            "AI grading is not configured: set GOOGLE_AI_STUDIO_API_KEY "
            "(or OPENROUTER_API_KEY).",
            request_payload,
        )

    try:
        remaining = consume_quota(token)
    except RateLimitExceeded as error:
        payload = _error_for_record(
            "AI grading limit reached. Try again later.",
            request_payload,
        )
        payload["retry_after_seconds"] = error.retry_after
        return 429, payload
    except QuotaUnavailable:
        return 503, _error_for_record(
            "AI grading is temporarily unavailable. Please try again.",
            request_payload,
        )

    try:
        result = grade_request(request_payload, timeout=OPENROUTER_TIMEOUT_SECONDS)
    except Exception:  # noqa: BLE001 - keep the public API JSON-shaped
        return 500, _error_for_record(
            "AI grading failed unexpectedly. Please try again.",
            request_payload,
        )
    if "mark_scheme" not in result:
        mark_scheme = _trusted_mark_scheme(request_payload.get("record_id"))
        if mark_scheme is not None:
            result["mark_scheme"] = mark_scheme
    result["rate_limit_remaining"] = remaining
    if result.get("ok"):
        return 200, result
    # A model/provider failure is a valid grading-result response. Keep it as a
    # 200 so the results panel can render the provider's actionable error.
    if result.get("provider") in {"openrouter", "google-ai-studio"}:
        return 200, result
    return 400, result


class handler(BaseHTTPRequestHandler):  # noqa: N801 - Vercel entrypoint name
    """Entrypoint detected by Vercel's Python runtime.

    Vercel's static analysis only recognises a class or function *defined*
    under a lowercase ``handler`` (or ``app``) name; an alias assigned from
    another name is invisible to it and the deployment fails with
    ``The pattern "api/grade.py" defined in `functions` doesn't match any
    Serverless Functions inside the `api` directory.``
    """

    def _respond(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        retry_after = payload.get("retry_after_seconds")
        if status == 429 and isinstance(retry_after, int):
            self.send_header("Retry-After", str(retry_after))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            content_length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            self._respond(400, _error("Content-Length must be an integer"))
            return
        if content_length > MAX_REQUEST_BYTES:
            self._respond(413, _error("request is too large"))
            return
        try:
            status, payload = handle_grade(
                "POST",
                self.headers,
                self.rfile.read(content_length),
            )
        except Exception:  # noqa: BLE001 - final serverless HTTP boundary
            status, payload = 500, _error(
                "AI grading failed unexpectedly. Please try again."
            )
        self._respond(status, payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        status, payload = handle_grade("GET", self.headers, b"")
        self._respond(status, payload)
