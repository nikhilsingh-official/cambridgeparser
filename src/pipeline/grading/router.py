"""Provider routing for grading: Google AI Studio first, OpenRouter as backup.

Google AI Studio is the default because it is the cheapest path to the model we
actually want (gemini-2.5-flash-lite). OpenRouter stays configured as the
fallback for one specific failure: Google refusing the call on quota. Every
other failure is *our* problem (a bad prompt, a broken schema, an outage) and
retrying it through a second vendor would only spend money to fail twice.

The returned envelope is grading-result/v1 either way. When a fallback happened
the result carries ``fallback_from`` so the failure is visible in logs and in
the eval harness instead of being silently absorbed.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.pipeline.grading.google_ai_client import (
    GoogleAIConfig,
    grade_answer_google,
)
from src.pipeline.grading.openrouter_client import (
    DEFAULT_TIMEOUT_SECONDS,
    OpenRouterConfig,
    RESULT_SCHEMA_VERSION,
    Transport,
    dry_run_result,
    grade_answer,
)


def grade_answer_routed(
    record: Dict[str, Any],
    parsed_answer: Dict[str, Any],
    google_config: Optional[GoogleAIConfig] = None,
    openrouter_config: Optional[OpenRouterConfig] = None,
    dry_run: Optional[bool] = None,
    google_transport: Optional[Transport] = None,
    openrouter_transport: Optional[Transport] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """Grade one answer, preferring Google and falling back on rate limits.

    ``dry_run=None`` auto-selects: dry-run only when *neither* provider has a
    key, which keeps the CLI's offline behaviour intact.
    """
    google_config = google_config or GoogleAIConfig()
    openrouter_config = openrouter_config or OpenRouterConfig()

    if dry_run is None:
        dry_run = not google_config.has_api_key and not openrouter_config.has_api_key
    if dry_run:
        return dry_run_result(record, parsed_answer)

    if not google_config.has_api_key:
        # No Google key configured: OpenRouter is the only path, not a fallback.
        return grade_answer(
            record,
            parsed_answer,
            config=openrouter_config,
            dry_run=False,
            transport=openrouter_transport,
            timeout=timeout,
        )

    primary = grade_answer_google(
        record,
        parsed_answer,
        config=google_config,
        dry_run=False,
        transport=google_transport,
        timeout=timeout,
    )
    if primary.get("ok") or not primary.get("rate_limited"):
        return primary

    if not openrouter_config.has_api_key:
        primary["error"] = (
            f"{primary.get('error')} (no OPENROUTER_API_KEY configured to fall back to)"
        )
        return primary

    fallback = grade_answer(
        record,
        parsed_answer,
        config=openrouter_config,
        dry_run=False,
        transport=openrouter_transport,
        timeout=timeout,
    )
    fallback["fallback_from"] = {
        "provider": primary.get("provider"),
        "model": primary.get("model"),
        "error": primary.get("error"),
    }
    return fallback


__all__ = ["grade_answer_routed", "RESULT_SCHEMA_VERSION"]
