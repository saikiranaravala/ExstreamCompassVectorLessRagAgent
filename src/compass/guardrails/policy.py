"""Guardrail policy: categories, decisions, results, and the persona matrix.

Personas the app must serve safely (all subject to the same policy):

    Legitimate roles          Typical intent            Handling
    -----------------------   -----------------------   -------------------------
    Support Engineer          resolve a ticket          ALLOW (grounded answer)
    Solution Consultant       compare variants          ALLOW
    New Hire                  learn the product         ALLOW
    Product Manager           verify behavior           ALLOW
    Customer (self-serve)     how-to questions          ALLOW
    IT Admin                  install / configure       ALLOW

    Adversarial actors        Typical intent            Handling
    -----------------------   -----------------------   -------------------------
    Prompt injector           override instructions     REFUSE (injection)
    Data exfiltrator          leak system prompt/keys    REFUSE + output leak guard
    Scope abuser              off-topic LLM use         REFUSE (out-of-scope/harmful)
    Careless user             pastes secrets/PII        SANITIZE (redact) + proceed
    Flooder / scraper         hammer the endpoint       RATE_LIMIT

Legitimate roles are never singled out — they pass because their queries are
in-scope and grounded, not because of who they are. The boundary is behavioral.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from compass.config import settings


class Category(str, Enum):
    """Classification of a request or response."""

    IN_SCOPE = "in_scope"  # legitimate documentation question
    OUT_OF_SCOPE = "out_of_scope"  # unrelated to the documentation corpus
    PROMPT_INJECTION = "prompt_injection"  # attempts to override instructions
    HARMFUL = "harmful"  # disallowed / abusive use of the model
    PII = "pii"  # query carries personal data or secrets
    MALFORMED = "malformed"  # empty / too long / non-text
    RATE_LIMITED = "rate_limited"  # too many requests
    LOW_CONFIDENCE = "low_confidence"  # retrieval too weak to answer reliably
    UNGROUNDED = "ungrounded"  # answer not supported by sources
    LEAKED = "leaked"  # answer leaks system prompt / secrets


class Decision(str, Enum):
    """What the pipeline decides to do with a request/response."""

    ALLOW = "allow"  # proceed unchanged
    SANITIZE = "sanitize"  # proceed with a modified (redacted/clamped) value
    REFUSE = "refuse"  # do not process; return a safe message
    RATE_LIMIT = "rate_limit"  # reject: too many requests


class Severity(str, Enum):
    """Severity for audit/telemetry."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Decisions that stop the normal flow and return a safe message to the user.
BLOCKING_DECISIONS = frozenset({Decision.REFUSE, Decision.RATE_LIMIT})


@dataclass
class GuardrailResult:
    """Outcome of a guardrail check.

    ``sanitized_text`` carries a cleaned query (when ``decision == SANITIZE``)
    or a safe replacement answer (output guard). ``message`` is the user-facing
    text to show when a request is refused/rate-limited.
    """

    decision: Decision = Decision.ALLOW
    category: Category = Category.IN_SCOPE
    severity: Severity = Severity.INFO
    reason: str = ""  # internal explanation (audit/logs)
    message: Optional[str] = None  # user-facing text for blocking decisions
    sanitized_text: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return self.decision in BLOCKING_DECISIONS

    @property
    def allowed(self) -> bool:
        return not self.blocked

    def to_audit(self) -> dict:
        """Compact dict for audit logging (never includes raw user text)."""
        return {
            "decision": self.decision.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "reason": self.reason,
            **({"metadata": self.metadata} if self.metadata else {}),
        }


@dataclass
class GuardrailConfig:
    """Tunable thresholds. Defaults come from ``settings`` but can be overridden
    (e.g. in tests) by constructing with explicit values."""

    enabled: bool = field(default_factory=lambda: settings.guardrails_enabled)
    max_query_chars: int = field(default_factory=lambda: settings.max_query_chars)
    min_query_chars: int = field(default_factory=lambda: settings.min_query_chars)
    min_retrieval_score: float = field(default_factory=lambda: settings.min_retrieval_score)
    rate_per_minute: int = field(default_factory=lambda: settings.guardrail_rate_per_minute)
    rate_per_hour: int = field(default_factory=lambda: settings.guardrail_rate_per_hour)
    # Redact PII/secrets from the query before it reaches the LLM and logs.
    redact_pii: bool = True


# ---- user-facing messages (calm, specific, no internal detail leaked) --------

MESSAGES = {
    Category.MALFORMED: (
        "I couldn't read that request. Please enter a documentation question "
        "between {min} and {max} characters."
    ),
    Category.PROMPT_INJECTION: (
        "I can only answer questions about the OpenText Exstream documentation, "
        "and I can't change how I operate or reveal my internal configuration. "
        "Ask me about the product and I'll help."
    ),
    Category.HARMFUL: (
        "I can't help with that request. I'm a documentation assistant for "
        "OpenText Exstream — ask me about the product and I'll do my best."
    ),
    Category.OUT_OF_SCOPE: (
        "That looks outside the OpenText Exstream documentation I cover. "
        "Try asking about deployment, Communications Designer, Content Author, "
        "Empower, output/production, or configuration."
    ),
    Category.RATE_LIMITED: (
        "You're sending requests faster than I can safely handle. "
        "Please wait a moment and try again."
    ),
    Category.LOW_CONFIDENCE: (
        "I couldn't find a confident match for that in the {variant} "
        "documentation. Here is the closest information I found — please verify "
        "against the source files, and consider rephrasing with product terms."
    ),
}


def message_for(category: Category, cfg: GuardrailConfig, **fmt) -> str:
    """Render the user-facing message for a category."""
    template = MESSAGES.get(category, MESSAGES[Category.OUT_OF_SCOPE])
    return template.format(
        min=cfg.min_query_chars, max=cfg.max_query_chars, **fmt
    )
