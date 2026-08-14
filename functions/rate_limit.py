"""Pure fixed-window quota logic used by the grading Cloud Function."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class RateLimitExceeded(Exception):
    retry_after: int
    limit: int
    window_seconds: int

    def __str__(self) -> str:
        return f"rate limit exceeded; retry in {self.retry_after} seconds"


def consume_quota(
    current: Any,
    *,
    now: int,
    policies: Mapping[str, Mapping[str, int]],
) -> tuple[dict[str, dict[str, int]], int]:
    """Return the next quota state or raise without mutating ``current``.

    The caller stores the returned state in one database transaction, making
    all configured windows (burst and daily) advance together.
    """
    existing = current if isinstance(current, dict) else {}
    next_state: dict[str, dict[str, int]] = {}
    remaining_values: list[int] = []

    for name, policy in policies.items():
        limit = int(policy["limit"])
        window_seconds = int(policy["window_seconds"])
        if limit < 1 or window_seconds < 1:
            raise ValueError(f"invalid rate-limit policy: {name}")

        prior = existing.get(name) if isinstance(existing.get(name), dict) else {}
        started_at = prior.get("started_at")
        count = prior.get("count")
        if not isinstance(started_at, int) or not isinstance(count, int):
            started_at, count = now, 0
        elif now < started_at or now >= started_at + window_seconds:
            started_at, count = now, 0

        if count >= limit:
            retry_after = max(1, math.ceil(started_at + window_seconds - now))
            raise RateLimitExceeded(retry_after, limit, window_seconds)

        next_count = count + 1
        next_state[name] = {"started_at": started_at, "count": next_count}
        remaining_values.append(limit - next_count)

    return next_state, min(remaining_values, default=0)
