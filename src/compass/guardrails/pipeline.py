"""GuardrailPipeline: the single entry point wiring the guards together.

    check_request(query, identity)  -> GuardrailResult   (before answering)
    check_response(answer, hits, ...) -> GuardrailResult  (after answering)

``QueryService.query`` calls both; a REFUSE/RATE_LIMIT from ``check_request``
short-circuits answer generation entirely (no LLM call, no retrieval waste).
"""

import logging
from typing import Optional

from compass.guardrails.input_guard import InputGuard
from compass.guardrails.output_guard import OutputGuard
from compass.guardrails.policy import (
    Category,
    Decision,
    GuardrailConfig,
    GuardrailResult,
    Severity,
    message_for,
)
from compass.guardrails.rate_limit import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)


class GuardrailPipeline:
    """Coordinates rate limiting, input guard, and output guard."""

    def __init__(self, config: Optional[GuardrailConfig] = None):
        self.cfg = config or GuardrailConfig()
        self.input_guard = InputGuard(self.cfg)
        self.output_guard = OutputGuard(self.cfg)
        self.rate_limiter = SlidingWindowRateLimiter(
            self.cfg.rate_per_minute, self.cfg.rate_per_hour
        )

    # -- request side ----------------------------------------------------------

    def check_request(self, query: str, identity: str = "anonymous") -> GuardrailResult:
        """Rate-limit then validate/classify the query.

        Returns a GuardrailResult; when ``blocked`` is True the caller must not
        generate an answer and should return ``result.message`` instead. When
        allowed, ``result.sanitized_text`` is the query to actually use.
        """
        if not self.cfg.enabled:
            return GuardrailResult(sanitized_text=query)

        if not self.rate_limiter.allow(identity):
            logger.warning("Guardrail rate limit hit for identity=%s", identity)
            return GuardrailResult(
                decision=Decision.RATE_LIMIT,
                category=Category.RATE_LIMITED,
                severity=Severity.WARNING,
                reason="per-identity rate limit exceeded",
                message=message_for(Category.RATE_LIMITED, self.cfg),
            )

        return self.input_guard.check(query)

    # -- response side ---------------------------------------------------------

    def check_response(
        self, answer: str, hits: list[dict], variant: str, top_score: float
    ) -> GuardrailResult:
        """Validate/repair the generated answer."""
        return self.output_guard.check(answer, hits, variant, top_score)

    # -- convenience -----------------------------------------------------------

    def refusal_response(self, result: GuardrailResult, variant: str) -> dict:
        """Build the standard query-response dict for a blocked request.

        The ``guardrail`` block mirrors the allowed-path shape ({input, output})
        so callers can inspect ``guardrail["input"]["decision"]`` uniformly.
        """
        return {
            "answer": result.message or message_for(result.category, self.cfg),
            "citations": [],
            "tool_calls": 0,
            "variant": variant,
            "model": None,
            "trace": [f"Guardrail: {result.category.value} -> {result.decision.value}"],
            "processing_time": 0.0,
            "guardrail": {"input": result.to_audit(), "output": {}},
        }
