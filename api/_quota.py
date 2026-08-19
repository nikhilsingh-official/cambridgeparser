"""Persistent per-user grading quotas for the Vercel Function.

The window arithmetic used to live here, in a compare-and-set loop against the
Firebase Realtime Database: read with an ETag, compute the next state, write it
back with ``If-Match``, retry on 412.  That design existed to avoid giving
Vercel an admin credential -- the counter was protected by security rules the
client could not satisfy dishonestly.

The Supabase version keeps that property and drops the loop.  ``grading_quotas``
has RLS with a select-only policy and *no* insert or update policy, so the table
is unwritable through the API.  The only thing that writes it is
``consume_grading_quota()``, a ``security definer`` function that takes the row
lock, rolls expired windows and increments -- atomically, in one statement, in
the database.  This module is now just the caller.

Vercel therefore still holds no secret: the public anon key plus the caller's
own access token is the whole credential set.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get(
    "SUPABASE_ANON_KEY",
    "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH",
)
CONSUME_QUOTA_URL = f"{SUPABASE_URL}/rest/v1/rpc/consume_grading_quota"

# Mirrors the limits in supabase/migrations/00000000000001_ide_schema.sql. The
# database is the enforcer; these exist only so an exhausted response can name
# the limit it hit without a second query. Change them there first.
QUOTA_POLICIES = {
    "burst": {"limit": 8, "window_ms": 10 * 60 * 1000},
    "daily": {"limit": 50, "window_ms": 24 * 60 * 60 * 1000},
}


@dataclass
class RateLimitExceeded(Exception):
    retry_after: int
    limit: int


class QuotaUnavailable(Exception):
    """Raised when the quota store cannot safely accept a grading request."""


def interpret_quota_response(payload: Any) -> int:
    """Turn the RPC's JSON into a remaining count, or raise.

    Split out from the HTTP call so the decision logic is testable without a
    database or a network.
    """

    if not isinstance(payload, dict):
        raise QuotaUnavailable(f"unexpected quota response: {payload!r}")

    if payload.get("allowed") is True:
        remaining = payload.get("remaining")
        if not isinstance(remaining, int):
            raise QuotaUnavailable("quota response was allowed but had no remaining count")
        return remaining

    if payload.get("allowed") is False:
        retry_after = payload.get("retry_after_seconds")
        limit = payload.get("limit")
        raise RateLimitExceeded(
            retry_after=retry_after if isinstance(retry_after, int) and retry_after > 0 else 60,
            limit=limit if isinstance(limit, int) else 0,
        )

    raise QuotaUnavailable(f"quota response had no verdict: {payload!r}")


def consume_quota(token: str) -> int:
    """Atomically consume one request and return the smallest remaining quota.

    ``token`` is the caller's Supabase access token; the database reads the user
    id from it, so no uid is passed and none can be spoofed.
    """

    request = urllib.request.Request(
        CONSUME_QUOTA_URL,
        data=b"{}",
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        # 401/403 here means the token stopped being valid between verification
        # and this call. Treat it as unavailable rather than as a quota verdict:
        # failing closed is right when we cannot tell whether spend is allowed.
        raise QuotaUnavailable(f"quota RPC returned {error.code}") from error
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise QuotaUnavailable(str(error)) from error

    return interpret_quota_response(payload)
