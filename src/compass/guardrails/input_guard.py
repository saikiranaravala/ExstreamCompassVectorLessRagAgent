"""Input guardrails: validate and classify a query before it is answered.

Order of checks (fail-fast on the highest-severity issue):
    1. Structural validity   — non-empty, printable, within length bounds
    2. Prompt injection      — REFUSE
    3. Harmful/disallowed use — REFUSE
    4. Obvious off-topic use  — REFUSE (soft-flag borderline cases to grounding)
    5. PII / secrets          — SANITIZE (redact) and proceed
"""

import logging
import unicodedata

from compass.guardrails import patterns
from compass.guardrails.policy import (
    Category,
    Decision,
    GuardrailConfig,
    GuardrailResult,
    Severity,
    message_for,
)

logger = logging.getLogger(__name__)

# Control characters (except tab/newline/carriage-return) that should never
# appear in a legitimate text query — a signal of binary/garbage input.
_DISALLOWED_CTRL = {c for c in range(0x00, 0x20)} - {0x09, 0x0A, 0x0D}


class InputGuard:
    """Runs pre-answer checks on a query."""

    def __init__(self, config: GuardrailConfig):
        self.cfg = config

    def check(self, query: str) -> GuardrailResult:
        """Classify a query and decide how to handle it."""
        if not self.cfg.enabled:
            return GuardrailResult(sanitized_text=query)

        raw = query if isinstance(query, str) else ""
        text = unicodedata.normalize("NFKC", raw).strip()

        # 1. structural validity -------------------------------------------------
        if not text or len(text) < self.cfg.min_query_chars:
            return self._refuse(Category.MALFORMED, "empty or too short")
        if len(text) > self.cfg.max_query_chars:
            return self._refuse(
                Category.MALFORMED, f"exceeds max length ({len(text)} chars)"
            )
        if any(ord(ch) in _DISALLOWED_CTRL for ch in text):
            return self._refuse(Category.MALFORMED, "contains control characters")
        # a query with no letters at all (pure symbols/digits) is not a question
        if not any(ch.isalpha() for ch in text):
            return self._refuse(Category.MALFORMED, "no alphabetic content")

        # 2. prompt injection ----------------------------------------------------
        inj = patterns.first_match(patterns.INJECTION_PATTERNS, text)
        if inj:
            return self._refuse(
                Category.PROMPT_INJECTION,
                f"injection pattern matched: {inj.re.pattern[:60]}",
                severity=Severity.WARNING,
            )

        # 3. harmful / disallowed use -------------------------------------------
        harm = patterns.first_match(patterns.HARMFUL_PATTERNS, text)
        if harm:
            return self._refuse(
                Category.HARMFUL,
                f"harmful pattern matched: {harm.re.pattern[:60]}",
                severity=Severity.WARNING,
            )

        # 4. obvious off-topic misuse -------------------------------------------
        if patterns.matches_any(patterns.OFF_TOPIC_PATTERNS, text):
            return self._refuse(
                Category.OUT_OF_SCOPE, "off-topic pattern matched"
            )

        # 5. PII / secrets -> redact and proceed --------------------------------
        if self.cfg.redact_pii:
            redacted, found = patterns.redact_pii(text)
            if found:
                logger.info("Guardrail redacted PII/secrets from query: %s", found)
                return GuardrailResult(
                    decision=Decision.SANITIZE,
                    category=Category.PII,
                    severity=Severity.WARNING,
                    reason=f"redacted {', '.join(found)}",
                    sanitized_text=redacted,
                    metadata={"pii_types": found},
                )

        return GuardrailResult(sanitized_text=text)

    # -- helpers ---------------------------------------------------------------

    def _refuse(
        self, category: Category, reason: str, severity: Severity = Severity.INFO
    ) -> GuardrailResult:
        return GuardrailResult(
            decision=Decision.REFUSE,
            category=category,
            severity=severity,
            reason=reason,
            message=message_for(category, self.cfg),
        )
