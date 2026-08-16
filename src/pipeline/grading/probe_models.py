"""Probe every candidate model with the REAL grading payload.

A model earns a place in the rotation only if it returns 200 *and* its reply
passes validate_grading_payload() -- the same check production applies. Prints
latency, tokens and how many evidence fields came back non-empty, since a
schema-valid reply with blank prose is a wrong answer that happens to typecheck.
"""

import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, "/home/nikhils/Programming/Pseudocode Solving")

from src.pipeline.grading.google_ai_client import to_gemini_request  # noqa: E402
from src.pipeline.grading.openrouter_client import (  # noqa: E402
    build_grading_messages,
    validate_grading_payload,
    _extract_json_object,
)

CANDIDATES = [
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]
RECORDS = (
    "/home/nikhils/Programming/Pseudocode Solving/src/website/server_resources/"
    "grading_question_records.json.gz"
)
KEY = os.environ["GOOGLE_AI_STUDIO_API_KEY"]


def first_record():
    with gzip.open(RECORDS, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    records = payload.get("records") if isinstance(payload, dict) else payload
    for record in records:
        if len(((record.get("mark_scheme") or {}).get("marking_points")) or []) >= 2:
            return record
    raise SystemExit("no usable record")


record = first_record()
answer = "DECLARE Count : INTEGER\nFOR Count = 1 TO 10\n   OUTPUT Count\nNEXT Count"
parsed = {"source": answer, "parse": {"ok": True}, "answer_kind": "pseudocode"}
body = json.dumps(to_gemini_request(build_grading_messages(record, parsed))).encode()

print(f"{'model':24} {'http':>5} {'secs':>6} {'in':>6} {'out':>5} {'contract':10} evidence")
print("-" * 78)

usable = []
for model in CANDIDATES:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    request = urllib.request.Request(
        url, data=body,
        headers={"x-goog-api-key": KEY, "Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode()
            code = response.status
    except urllib.error.HTTPError as error:
        detail = error.read().decode()[:150].replace("\n", " ")
        try:
            detail = json.loads(detail + "}" * 3).get("error", {}).get("status", detail)
        except Exception:
            pass
        print(f"{model:24} {error.code:>5} {'':>6} {'':>6} {'':>5} {'-':10} {detail[:28]}")
        continue
    except Exception as error:  # noqa: BLE001
        print(f"{model:24} {'ERR':>5} {'':>6} {'':>6} {'':>5} {'-':10} {str(error)[:28]}")
        continue

    elapsed = time.time() - started
    envelope = json.loads(raw)
    usage = envelope.get("usageMetadata") or {}
    text = "".join(
        part.get("text") or ""
        for part in ((envelope["candidates"][0].get("content") or {}).get("parts") or [])
    )
    payload = _extract_json_object(text)
    error = validate_grading_payload(payload)
    points = (payload or {}).get("points") or []
    filled = sum(1 for p in points if (p.get("evidence") or "").strip())
    verdict = "VALID" if error is None else "INVALID"
    print(f"{model:24} {code:>5} {elapsed:>6.1f} {usage.get('promptTokenCount', 0):>6} "
          f"{usage.get('candidatesTokenCount', 0):>5} {verdict:10} {filled}/{len(points)}")
    if error is None:
        usable.append(model)

print("\nusable rotation:")
print(json.dumps(usable, indent=2))
