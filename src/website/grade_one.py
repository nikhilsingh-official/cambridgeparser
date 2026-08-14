"""Grade a single submitted answer for the website's Submit button.

Reads a JSON request on stdin and writes a ``grading-result/v1`` JSON on stdout:

    {"record_id": <known question id>,
     "source": "<student pseudocode>",
     "parse":  {"ok": bool, "statements": [...], "diagnostics": [...]}}

The ``parse`` block is the browser's wasm-compiler output, so this entrypoint
never needs the native Rust binary. The same request builder is used by the
Vercel Function in ``api/grade.py``. Grading reuses the real pipeline in
:mod:`src.pipeline.grading.openrouter_client`: dry-run without
``OPENROUTER_API_KEY`` and a real model call when the key is set.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path
from typing import Any, Dict

from src.pipeline.grading.ast_adapter import AST_VERSION, SCHEMA_VERSION
from src.pipeline.grading.openrouter_client import (
    DEFAULT_TIMEOUT_SECONDS,
    OpenRouterConfig,
    grade_answer,
)


RECORDS_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "website"
    / "server_resources"
    / "grading_question_records.json.gz"
)
_records_by_id: Dict[str, Dict[str, Any]] | None = None
MAX_SOURCE_CHARS = 20_000


def load_record(record_id: Any) -> Dict[str, Any] | None:
    global _records_by_id
    if _records_by_id is None:
        with gzip.open(RECORDS_PATH, "rt", encoding="utf-8") as records_file:
            payload = json.load(records_file)
        _records_by_id = {
            str(record.get("id")): record
            for record in payload.get("records", [])
            if isinstance(record, dict) and record.get("id") is not None
        }
    return _records_by_id.get(str(record_id))


def build_parsed_answer(
    source: str, parse: Dict[str, Any], answer_kind: str = "pseudocode"
) -> Dict[str, Any]:
    """Shape the browser's wasm result into the ``parsed-answer/v1`` the grader expects."""
    return {
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


def grade_request(
    request: Dict[str, Any],
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    if not isinstance(request, dict):
        return {
            "schema_version": "grading-result/v1",
            "ok": False,
            "result": None,
            "error": "request JSON must be an object",
        }
    # Direct records remain supported for the CLI's unit-level dry run. The web
    # client sends only an id; production resolves the same trusted corpus.
    record = request.get("record") or load_record(request.get("record_id"))
    if not isinstance(record, dict):
        return {
            "schema_version": "grading-result/v1",
            "ok": False,
            "dry_run": False,
            "model": None,
            "provider": None,
            "result": None,
            "error": "request.record must be a pseudocode-question-record object",
            "raw_response": None,
        }
    source = request.get("source") or ""
    parse = request.get("parse") or {}
    answer_kind = request.get("answer_kind") or "pseudocode"
    if not isinstance(source, str):
        return {
            "schema_version": "grading-result/v1",
            "ok": False,
            "result": None,
            "error": "request.source must be a string",
        }
    if len(source) > MAX_SOURCE_CHARS:
        return {
            "schema_version": "grading-result/v1",
            "ok": False,
            "result": None,
            "error": f"request.source exceeds {MAX_SOURCE_CHARS} characters",
        }
    if not isinstance(parse, dict):
        return {
            "schema_version": "grading-result/v1",
            "ok": False,
            "result": None,
            "error": "request.parse must be an object",
        }
    if answer_kind not in {"pseudocode", "fill_blank_sheet"}:
        return {
            "schema_version": "grading-result/v1",
            "ok": False,
            "result": None,
            "error": "request.answer_kind is not supported",
        }
    parsed_answer = build_parsed_answer(source, parse, answer_kind)
    result = grade_answer(
        record,
        parsed_answer,
        config=OpenRouterConfig(),
        timeout=timeout,
    )
    result["mark_scheme"] = record.get("mark_scheme") or {}
    return result


def main() -> int:
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        json.dump(
            {
                "schema_version": "grading-result/v1",
                "ok": False,
                "error": f"invalid request JSON: {error}",
                "result": None,
            },
            sys.stdout,
        )
        return 0
    json.dump(grade_request(request), sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
