"""Persistent per-user grading quotas for the Vercel Function.

The function uses the caller's already-verified Firebase ID token to update a
rules-protected Realtime Database counter.  This preserves spend protection
without requiring a Firebase Admin service-account secret in Vercel.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


DATABASE_URL = os.environ.get(
    "FIREBASE_DATABASE_URL",
    "https://pseudocode-parser-default-rtdb.asia-southeast1.firebasedatabase.app",
).rstrip("/")
QUOTA_POLICIES = {
    "burst": {"limit": 8, "window_ms": 10 * 60 * 1000},
    "daily": {"limit": 50, "window_ms": 24 * 60 * 60 * 1000},
}
MAX_TRANSACTION_ATTEMPTS = 5


@dataclass
class RateLimitExceeded(Exception):
    retry_after: int
    limit: int


class QuotaUnavailable(Exception):
    """Raised when the quota store cannot safely accept a grading request."""


def next_quota_state(
    current: Any,
    *,
    now_ms: int,
    policies: Mapping[str, Mapping[str, int]] = QUOTA_POLICIES,
) -> tuple[dict[str, dict[str, int]], int]:
    """Return the next fixed-window state or raise when a window is full."""

    existing = current if isinstance(current, dict) else {}
    next_state: dict[str, dict[str, int]] = {}
    remaining_values: list[int] = []

    for name, policy in policies.items():
        limit = int(policy["limit"])
        window_ms = int(policy["window_ms"])
        prior = existing.get(name) if isinstance(existing.get(name), dict) else {}
        started_at = prior.get("startedAt")
        count = prior.get("count")
        if (
            not isinstance(started_at, int)
            or not isinstance(count, int)
            or now_ms < started_at
            or now_ms >= started_at + window_ms
        ):
            started_at, count = now_ms, 0
        if count >= limit:
            retry_after = max(1, (started_at + window_ms - now_ms + 999) // 1000)
            raise RateLimitExceeded(retry_after=retry_after, limit=limit)
        count += 1
        next_state[name] = {"startedAt": started_at, "count": count}
        remaining_values.append(limit - count)

    return next_state, min(remaining_values, default=0)


def _quota_url(uid: str, token: str) -> str:
    safe_uid = urllib.parse.quote(uid, safe="")
    query = urllib.parse.urlencode({"auth": token})
    return f"{DATABASE_URL}/gradingQuotas/{safe_uid}.json?{query}"


def consume_quota(uid: str, token: str) -> int:
    """Atomically consume one request and return the smallest remaining quota."""

    url = _quota_url(uid, token)
    for _attempt in range(MAX_TRANSACTION_ATTEMPTS):
        get_request = urllib.request.Request(
            url,
            headers={"X-Firebase-ETag": "true"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(get_request, timeout=10) as response:
                current = json.loads(response.read().decode("utf-8"))
                etag = response.headers.get("ETag")
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise QuotaUnavailable(str(error)) from error
        if not etag:
            raise QuotaUnavailable("Realtime Database did not return an ETag")

        next_state, remaining = next_quota_state(
            current,
            now_ms=int(time.time() * 1000),
        )
        put_request = urllib.request.Request(
            url,
            data=json.dumps(next_state, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json", "If-Match": etag},
            method="PUT",
        )
        try:
            with urllib.request.urlopen(put_request, timeout=10):
                return remaining
        except urllib.error.HTTPError as error:
            if error.code == 412:
                continue
            raise QuotaUnavailable(str(error)) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise QuotaUnavailable(str(error)) from error

    raise QuotaUnavailable("grading quota was updated concurrently; try again")
