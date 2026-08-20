"""Invoke the Rust pseudocode parser and return structured ParsedAnswer data.

The adapter shields the rest of the pipeline from process details: it locates
the ``pseudocode-parser`` binary, feeds it student source, enforces a timeout,
and always returns a ``parsed-answer/v1`` payload — subprocess failures become
diagnostics, never exceptions.
"""

# import paths rewritten from src.pipeline.grading to api.grading when
# this package moved into the serverless function. Logic unchanged.

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

SCHEMA_VERSION = "parsed-answer/v1"
AST_VERSION = "cambridge-pseudocode-ast/v1"
DEFAULT_TIMEOUT_SECONDS = 10.0

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BINARY_CANDIDATES = (
    _REPO_ROOT / "pseudocode-parser" / "target" / "release" / "pseudocode-parser",
    _REPO_ROOT / "pseudocode-parser" / "target" / "debug" / "pseudocode-parser",
)


def find_parser_binary() -> Optional[Path]:
    """Locate the parser binary: $PSEUDOCODE_PARSER_BIN, then release, then debug."""
    override = os.environ.get("PSEUDOCODE_PARSER_BIN")
    if override:
        path = Path(override)
        return path if path.is_file() else None
    for candidate in _BINARY_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _failure_parse(message: str, hint: Optional[str] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "ast_version": AST_VERSION,
        "ast": {"statements": []},
        "diagnostics": [
            {
                "severity": "error",
                "message": message,
                "hint": hint,
                "line": None,
                "column": None,
            }
        ],
    }


def parse_answer(
    source_text: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    binary: Optional[Path] = None,
) -> Dict[str, Any]:
    """Parse student pseudocode into a ParsedAnswer payload.

    Never raises for parser-side problems; the ``parse`` block carries either
    the AST or diagnostics, and ``runner`` records how the subprocess behaved.
    """
    resolved_binary = Path(binary) if binary else find_parser_binary()
    runner: Dict[str, Any] = {
        "binary": str(resolved_binary) if resolved_binary else None,
        "exit_code": None,
        "duration_ms": None,
        "stdout": "",
        "stderr": "",
        "error": None,
    }

    if resolved_binary is None or not Path(resolved_binary).is_file():
        runner["error"] = "binary_missing"
        return {
            "schema_version": SCHEMA_VERSION,
            "source_text": source_text,
            "parse": _failure_parse(
                "Pseudocode parser binary not found",
                "Build it with: cargo build --release (in pseudocode-parser/), "
                "or set PSEUDOCODE_PARSER_BIN.",
            ),
            "runner": runner,
        }

    started = time.monotonic()
    try:
        completed = subprocess.run(
            [str(resolved_binary), "--format", "json"],
            input=source_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        runner["error"] = "timeout"
        runner["duration_ms"] = round((time.monotonic() - started) * 1000.0, 3)
        return {
            "schema_version": SCHEMA_VERSION,
            "source_text": source_text,
            "parse": _failure_parse(
                f"Parser timed out after {timeout} seconds",
                "The submission may contain pathological input.",
            ),
            "runner": runner,
        }

    runner["duration_ms"] = round((time.monotonic() - started) * 1000.0, 3)
    runner["exit_code"] = completed.returncode
    runner["stdout"] = completed.stdout or ""
    runner["stderr"] = (completed.stderr or "")[-2000:]

    if completed.returncode != 0:
        runner["error"] = "nonzero_exit"
        return {
            "schema_version": SCHEMA_VERSION,
            "source_text": source_text,
            "parse": _failure_parse(
                f"Parser exited with code {completed.returncode}",
                runner["stderr"] or None,
            ),
            "runner": runner,
        }

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        runner["error"] = "invalid_json"
        return {
            "schema_version": SCHEMA_VERSION,
            "source_text": source_text,
            "parse": _failure_parse(
                f"Parser emitted invalid JSON: {error}",
                (completed.stdout or "")[:500] or None,
            ),
            "runner": runner,
        }

    parse_block = {
        "ok": bool(payload.get("ok")),
        "ast_version": payload.get("ast_version") or AST_VERSION,
        "ast": {"statements": payload.get("statements") or []},
        "diagnostics": payload.get("diagnostics") or [],
        "compiler_output": {
            "stdout": payload.get("stdout") or "",
            "stderr": payload.get("stderr") or "",
            "raw": payload,
        },
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "source_text": source_text,
        "parse": parse_block,
        "runner": runner,
    }
