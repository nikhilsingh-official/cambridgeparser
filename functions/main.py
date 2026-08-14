"""HTTPS Cloud Function backing the website's grading API.

Firebase Hosting rewrites ``/api/**`` to this function (see ``firebase.json``).
The only server-side secret -- the OpenRouter API key -- is read here from
Secret Manager and never leaves the function; it is never bundled into the
client. The grading logic itself is the repository's real pipeline
(``src/pipeline/grading``), vendored into ``functions/grading`` at deploy time
by ``sync_pipeline.py`` so the uploaded function is self-contained and needs no
Rust toolchain (the browser sends its own wasm parse result along with the
request).

This mirrors the dev-server contract in ``src/website/grade_one.py``: request
``{record_id, source, parse}`` in, a ``grading-result/v1`` JSON out.
"""

from __future__ import annotations

import json
import hashlib
import os
import time
from pathlib import Path

import firebase_admin
from firebase_admin import auth, db
from firebase_functions import https_fn, options
from firebase_functions.params import SecretParam

try:  # Firebase deploy imports main.py as a top-level module.
    from .rate_limit import RateLimitExceeded, consume_quota
except ImportError:  # pragma: no cover - exercised by the Functions runtime
    from rate_limit import RateLimitExceeded, consume_quota

# Declared secret. Firebase injects its value as an environment variable at
# runtime for any function that lists it in ``secrets=[...]``. Set the value
# once (you do this yourself after deploy):
#     firebase functions:secrets:set OPENROUTER_API_KEY
OPENROUTER_API_KEY = SecretParam("OPENROUTER_API_KEY")

GRADING_RESULT_SCHEMA = "grading-result/v1"
MAX_REQUEST_BYTES = 256_000
MAX_SOURCE_CHARS = 20_000
DATABASE_URL = os.environ.get(
    "FIREBASE_DATABASE_URL",
    "https://pseudocode-parser-default-rtdb.asia-southeast1.firebasedatabase.app",
)
RATE_LIMIT_POLICIES = {
    "burst": {
        "limit": int(os.environ.get("GRADE_BURST_LIMIT", "8")),
        "window_seconds": int(os.environ.get("GRADE_BURST_WINDOW_SECONDS", "600")),
    },
    "daily": {
        "limit": int(os.environ.get("GRADE_DAILY_LIMIT", "50")),
        "window_seconds": int(os.environ.get("GRADE_DAILY_WINDOW_SECONDS", "86400")),
    },
}

_records_by_id: dict[str, dict] | None = None


def _json(
    payload: dict,
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> https_fn.Response:
    response_headers = {"Cache-Control": "no-store"}
    response_headers.update(headers or {})
    return https_fn.Response(
        json.dumps(payload),
        status=status,
        mimetype="application/json",
        headers=response_headers,
    )


def _error(
    message: str,
    status: int = 400,
    headers: dict[str, str] | None = None,
) -> https_fn.Response:
    return _json(
        {
            "schema_version": GRADING_RESULT_SCHEMA,
            "ok": False,
            "result": None,
            "error": message,
        },
        status=status,
        headers=headers,
    )


def _ensure_firebase_app() -> None:
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()


def _authenticated_uid(req: https_fn.Request) -> str:
    header = req.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ValueError("Sign in is required to use AI grading.")
    _ensure_firebase_app()
    decoded = auth.verify_id_token(token)
    uid = decoded.get("uid") or decoded.get("sub")
    if not isinstance(uid, str) or not uid:
        raise ValueError("The sign-in token does not contain an account id.")
    return uid


def _consume_account_quota(uid: str) -> int:
    account_key = hashlib.sha256(uid.encode("utf-8")).hexdigest()
    quota_ref = db.reference(
        f"serverOnly/rateLimits/grading/{account_key}",
        url=DATABASE_URL,
    )
    decision: dict[str, int] = {}
    now = int(time.time())

    def update(current: object) -> dict:
        next_state, remaining = consume_quota(
            current,
            now=now,
            policies=RATE_LIMIT_POLICIES,
        )
        decision["remaining"] = remaining
        return next_state

    quota_ref.transaction(update)
    return decision.get("remaining", 0)


def _load_record(record_id: object) -> dict | None:
    global _records_by_id
    if _records_by_id is None:
        path = Path(__file__).with_name("question_records.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        _records_by_id = {
            str(record.get("id")): record
            for record in payload.get("records", [])
            if isinstance(record, dict) and record.get("id") is not None
        }
    return _records_by_id.get(str(record_id))


@https_fn.on_request(
    secrets=[OPENROUTER_API_KEY],
    # Co-located with the Singapore RTDB instance (asia-southeast1). Must match
    # the region in the Hosting rewrite in firebase.json.
    region="asia-southeast1",
    memory=options.MemoryOption.MB_256,
    timeout_sec=120,
)
def api(req: https_fn.Request) -> https_fn.Response:
    """Grade one submission. Hosting only forwards ``/api/**`` here, and grading
    is the sole endpoint, so any POST is treated as a grade request (avoids a
    self-inflicted 404 if the forwarded path isn't exactly ``/api/grade``)."""
    if req.method != "POST":
        return _error("POST required (this endpoint grades one submission)", status=405)

    if req.content_length is not None and req.content_length > MAX_REQUEST_BYTES:
        return _error("request is too large", status=413)

    try:
        uid = _authenticated_uid(req)
    except Exception:  # noqa: BLE001 - never expose token verification details
        return _error("Sign in is required to use AI grading.", status=401)

    try:
        request = req.get_json(force=True, silent=False)
    except Exception as error:  # noqa: BLE001 - surface malformed JSON to the client
        return _error(f"invalid request JSON: {error}", status=400)
    if not isinstance(request, dict):
        return _error("request JSON must be an object")

    record = _load_record(request.get("record_id"))
    if record is None:
        return _error("request.record_id does not identify a known question")

    source = request.get("source") or ""
    parse = request.get("parse") or {}
    answer_kind = request.get("answer_kind") or "pseudocode"
    if not isinstance(source, str):
        return _error("request.source must be a string")
    if len(source) > MAX_SOURCE_CHARS:
        return _error(f"request.source exceeds {MAX_SOURCE_CHARS} characters")
    if not isinstance(parse, dict):
        return _error("request.parse must be an object")
    if answer_kind not in {"pseudocode", "fill_blank_sheet"}:
        return _error("request.answer_kind is not supported")

    # Spend quota only after every cheap rejection. From here onward the request
    # is eligible to invoke the paid AI service.
    try:
        remaining = _consume_account_quota(uid)
    except RateLimitExceeded as error:
        return _error(
            "AI grading limit reached. Try again later.",
            status=429,
            headers={
                "Retry-After": str(error.retry_after),
                "X-RateLimit-Limit": str(error.limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    # Imported lazily so a missing vendored package produces a clear runtime
    # error rather than a module-load crash.
    from grading.ast_adapter import AST_VERSION, SCHEMA_VERSION
    from grading.openrouter_client import OpenRouterConfig, grade_answer

    # Shape the browser's wasm result into the parsed-answer/v1 the grader wants.
    parsed_answer = {
        "schema_version": SCHEMA_VERSION,
        "source_text": source,
        "answer_kind": answer_kind,
        "parse": {
            "ok": bool(parse.get("ok")),
            "ast_version": parse.get("ast_version") or AST_VERSION,
            "ast": {"statements": parse.get("statements") or []},
            "diagnostics": parse.get("diagnostics") or [],
        },
    }

    # OpenRouterConfig also reads OPENROUTER_API_KEY from the environment, but we
    # pass the secret value explicitly to keep the dependency obvious. A missing
    # key makes the grader fall back to a deterministic dry-run result.
    config = OpenRouterConfig(api_key=OPENROUTER_API_KEY.value or None)
    result = grade_answer(record, parsed_answer, config=config)
    result["mark_scheme"] = record.get("mark_scheme") or {}
    return _json(
        result,
        headers={
            "RateLimit-Policy": ", ".join(
                f'{policy["limit"]};w={policy["window_seconds"]}'
                for policy in RATE_LIMIT_POLICIES.values()
            ),
            "X-RateLimit-Remaining": str(remaining),
        },
    )
