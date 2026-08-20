"""Provider routing for grading: Google AI Studio first, OpenRouter as backup.

Google AI Studio is the default because calling Google directly avoids the
reseller margin. OpenRouter stays configured as the fallback for the two
failures that are Google's problem rather than ours: a quota refusal, and a
model that has become unavailable to our key (see ``classify_failure``). Every
other failure is *our* problem (a bad prompt, a broken schema) and retrying it
through a second vendor would only spend money to fail twice.

The returned envelope is grading-result/v1 either way. When a fallback happened
the result carries ``fallback_from`` so the failure is visible in logs and in
the eval harness instead of being silently absorbed.
"""

# import paths rewritten from src.pipeline.grading to api.grading when
# this package moved into the serverless function. Logic unchanged.

from __future__ import annotations

from typing import Any, Dict, List, Optional

from api.grading.google_ai_client import (
    GoogleAIConfig,
    grade_answer_google,
)
from api.grading.openrouter_client import (
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

    # Walk the free Google models in order, exhausting each free tier before the
    # next. Only a rate_limit/model_unavailable verdict advances the chain.
    attempts: List[Dict[str, Any]] = []
    primary: Dict[str, Any] = {}
    fallback_reason: Optional[str] = None
    for model in google_config.rotation_for(record.get("id")):
        primary = grade_answer_google(
            record,
            parsed_answer,
            config=google_config.for_model(model),
            dry_run=False,
            transport=google_transport,
            timeout=timeout,
        )
        fallback_reason = primary.get("fallback_reason")
        if primary.get("ok") or not fallback_reason:
            if attempts:
                primary["fallback_from"] = attempts[-1]
            return primary
        attempts.append(
            {
                "provider": primary.get("provider"),
                "model": model,
                "reason": fallback_reason,
                "error": primary.get("error"),
            }
        )

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
    fallback["fallback_from"] = attempts[-1]
    fallback["fallback_chain"] = attempts
    return fallback


__all__ = ["grade_answer_routed", "RESULT_SCHEMA_VERSION"]
