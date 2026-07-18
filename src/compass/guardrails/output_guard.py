"""Output guardrails: validate a generated answer before it reaches the user.

Checks:
    * retrieval confidence — if the best hit scored below threshold, the answer
      is likely ungrounded; downgrade to a low-confidence disclaimer.
    * leakage — the answer must not echo the system prompt or expose secrets;
      redact/replace if it does.
    * emptiness — never return a blank answer.
    * citation presence — a substantive answer over real sources should cite;
      absence is flagged (informational), not blocked.

The output guard prefers to *repair* (annotate/replace) over hard-refusing, so
a legitimate question still gets the best safe answer available.
"""

import logging
import re

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

# Phrases that would indicate the model leaked its own instructions.
_LEAK_MARKERS = [
    re.compile(r"you are compass, an expert assistant", re.IGNORECASE),
    re.compile(r"system\s+prompt\s*:", re.IGNORECASE),
    re.compile(r"my (?:system\s+)?instructions? (?:are|state|say)", re.IGNORECASE),
    re.compile(r"cite sources inline with bracketed numbers", re.IGNORECASE),
]

_CITATION_RE = re.compile(r"\[\d{1,2}\]")


class OutputGuard:
    """Runs post-answer checks on a generated answer."""

    def __init__(self, config: GuardrailConfig):
        self.cfg = config

    def check(
        self,
        answer: str,
        hits: list[dict],
        variant: str,
        top_score: float,
    ) -> GuardrailResult:
        """Validate/repair an answer.

        Args:
            answer: Generated answer text
            hits: Retrieval hits used as sources
            variant: Documentation variant (for messaging)
            top_score: BM25 score of the best hit (0.0 if none)
        """
        if not self.cfg.enabled:
            return GuardrailResult(sanitized_text=answer)

        text = (answer or "").strip()

        # 1. empty answer -> low confidence disclaimer --------------------------
        if not text:
            return GuardrailResult(
                decision=Decision.SANITIZE,
                category=Category.UNGROUNDED,
                severity=Severity.WARNING,
                reason="empty answer from generator",
                sanitized_text=message_for(
                    Category.LOW_CONFIDENCE, self.cfg, variant=variant
                ),
            )

        # 2. system-prompt / instruction leakage --------------------------------
        if any(m.search(text) for m in _LEAK_MARKERS):
            logger.warning("Guardrail caught system-prompt leakage in answer")
            return GuardrailResult(
                decision=Decision.SANITIZE,
                category=Category.LEAKED,
                severity=Severity.ERROR,
                reason="answer echoed system prompt / instructions",
                sanitized_text=message_for(
                    Category.LOW_CONFIDENCE, self.cfg, variant=variant
                ),
            )

        # 3. secret leakage in the answer -> redact -----------------------------
        redacted, found = patterns.redact_pii(text)
        if found:
            logger.warning("Guardrail redacted secrets from answer: %s", found)
            return GuardrailResult(
                decision=Decision.SANITIZE,
                category=Category.LEAKED,
                severity=Severity.ERROR,
                reason=f"redacted {', '.join(found)} from answer",
                sanitized_text=redacted,
                metadata={"pii_types": found},
            )

        # 4. grounding / confidence --------------------------------------------
        if not hits or top_score < self.cfg.min_retrieval_score:
            # Keep the answer but flag low confidence so the caller can surface
            # a disclaimer; do not discard a genuine (if weak) answer.
            return GuardrailResult(
                decision=Decision.ALLOW,
                category=Category.LOW_CONFIDENCE,
                severity=Severity.WARNING,
                reason=f"top retrieval score {top_score:.2f} < {self.cfg.min_retrieval_score}",
                sanitized_text=text,
                metadata={"top_score": round(top_score, 3), "hits": len(hits)},
            )

        # 5. citation presence (informational) ----------------------------------
        if hits and not _CITATION_RE.search(text):
            return GuardrailResult(
                decision=Decision.ALLOW,
                category=Category.IN_SCOPE,
                severity=Severity.INFO,
                reason="answer over real sources contains no [n] citations",
                sanitized_text=text,
                metadata={"missing_citations": True},
            )

        return GuardrailResult(sanitized_text=text)
