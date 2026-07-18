"""Guardrails: a layered safety and quality boundary around every request.

The pipeline runs on both sides of answer generation:

* **Input guard** — validates and classifies the incoming query (length,
  encoding, prompt injection, disallowed use, PII/secrets, retrieval scope).
* **Output guard** — validates the generated answer (grounding/confidence,
  citation presence, system-prompt/PII leakage, empty answers).

Every request — from any persona, legitimate or adversarial — is subject to
the same policy. See ``policy.py`` for the persona × category matrix and the
decisions (ALLOW / SANITIZE / REFUSE / RATE_LIMIT) each category maps to.
"""

from compass.guardrails.pipeline import GuardrailPipeline
from compass.guardrails.policy import (
    Category,
    Decision,
    GuardrailResult,
    GuardrailConfig,
    Severity,
)

__all__ = [
    "GuardrailPipeline",
    "GuardrailResult",
    "GuardrailConfig",
    "Category",
    "Decision",
    "Severity",
]
