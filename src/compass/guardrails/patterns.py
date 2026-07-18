"""Compiled detection patterns for the guardrails.

Precision matters more than recall here: a false positive blocks a legitimate
documentation question. Patterns therefore match specific multi-word phrases
and structural markers, never single ambiguous words (a query like "how do I
ignore case in a filter" must pass, while "ignore your previous instructions"
must not).
"""

import re

# ---- prompt injection / jailbreak (any one strong match => injection) --------

_INJECTION_SOURCES = [
    # instruction override
    r"ignore\s+(?:all\s+|the\s+|your\s+|any\s+)?(?:previous|prior|above|earlier|preceding)\s+(?:instructions?|prompts?|rules?|directions?|messages?)",
    r"disregard\s+(?:all\s+|the\s+|your\s+|any\s+)?(?:previous|prior|above|earlier)?\s*(?:instructions?|prompts?|rules?|context)",
    r"forget\s+(?:all\s+|everything\s+|your\s+)?(?:previous|prior|above)?\s*(?:instructions?|rules?|what\s+you)",
    r"override\s+(?:your\s+|the\s+|all\s+)?(?:instructions?|system\s+prompt|rules?|guardrails?|safety)",
    # role reassignment / jailbreak personas
    r"you\s+are\s+now\s+(?:a|an|no\s+longer|going\s+to)",
    r"pretend\s+(?:you\s+are|to\s+be|that\s+you)",
    r"act\s+as\s+(?:if\s+you\s+are\s+)?(?:a\s+|an\s+)?(?:dan|jailbroken|unrestricted|uncensored|evil|developer)",
    r"\bdeveloper\s+mode\b",
    r"\bjailbreak\b",
    r"\bDAN\b",
    # system-prompt / config extraction
    r"(?:reveal|show|print|repeat|output|display|tell\s+me|give\s+me|what\s+(?:is|are))\s+(?:me\s+)?(?:your\s+|the\s+)?(?:system\s+)?(?:prompt|instructions?|configuration|rules?|guidelines?)\b",
    r"\bsystem\s+prompt\b",
    r"repeat\s+(?:the\s+|everything\s+)?(?:above|text\s+above|words\s+above)",
    # restriction bypass
    r"bypass\s+(?:your\s+|the\s+|all\s+)?(?:restrictions?|rules?|guardrails?|filters?|safety|limitations?)",
    r"without\s+(?:any\s+)?(?:restrictions?|filters?|rules?|limitations?|censorship)",
    r"no\s+longer\s+(?:bound|restricted|limited)\s+by",
    # structural / template injection
    r"</?\s*(?:system|instructions?|prompt|assistant|user)\s*>",
    r"\[/?INST\]",
    r"<\|(?:im_start|im_end|system|endoftext)\|>",
    r"###\s*(?:system|instruction)",
    # data-exfil framing
    r"(?:print|output|list|reveal)\s+(?:your\s+)?(?:api\s*keys?|secrets?|credentials?|env(?:ironment)?\s+variables?|tokens?)",
]

INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_SOURCES]


# ---- disallowed / harmful use (narrow & high-precision for a doc assistant) --

_HARMFUL_SOURCES = [
    r"(?:how\s+to\s+|help\s+me\s+|write\s+|create\s+|generate\s+|build\s+)(?:a\s+|some\s+)?(?:malware|ransomware|spyware|keylogger|computer\s+virus|trojan)",
    r"(?:how\s+to\s+)?(?:make|build|construct)\s+(?:a\s+)?(?:bomb|explosive|weapon|firearm)",
    r"(?:instructions?\s+(?:for|to)\s+|how\s+to\s+)(?:synthesize|manufacture|produce)\s+(?:drugs?|methamphetamine|explosives?)",
    r"(?:how\s+to\s+)?(?:hack|breach|attack)\s+(?:into\s+)?(?:someone'?s?|a|the)\s+(?:account|bank|network|system|computer)",
]

HARMFUL_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _HARMFUL_SOURCES]


# ---- obvious off-topic LLM misuse (only very clear cases -> soft flag) --------

_OFF_TOPIC_SOURCES = [
    r"\bwrite\s+(?:me\s+)?(?:a\s+)?(?:poem|song|story|essay|rap|haiku|joke|screenplay)\b",
    r"\btell\s+me\s+a\s+joke\b",
    r"\bwrite\s+(?:me\s+)?(?:some\s+)?(?:python|java(?:script)?|c\+\+|sql|bash)\s+(?:code|script|program)\s+(?:to|that|for)\b",
    r"\b(?:who|what)\s+(?:is|are|was|were)\s+(?:the\s+)?(?:president|capital\s+of|weather|stock\s+price)\b",
    r"\btranslate\s+(?:this\s+|the\s+following\s+)?(?:into|to)\s+(?:french|spanish|german|chinese|japanese)\b",
]

OFF_TOPIC_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _OFF_TOPIC_SOURCES]


# ---- PII / secrets (redact before the query reaches the LLM and logs) --------
# (name, pattern, replacement-label)

_PII_SOURCES = [
    ("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[redacted-email]"),
    ("ssn", r"\b\d{3}-\d{2}-\d{4}\b", "[redacted-ssn]"),
    ("credit_card", r"\b(?:\d[ -]?){13,16}\b", "[redacted-cc]"),
    ("aws_key", r"\bAKIA[0-9A-Z]{16}\b", "[redacted-key]"),
    ("openai_key", r"\bsk-[A-Za-z0-9]{20,}\b", "[redacted-key]"),
    ("bearer", r"\bBearer\s+[A-Za-z0-9\-_\.]{20,}\b", "[redacted-token]"),
    (
        "secret_assignment",
        r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|private[_-]?key)\b\s*[:=]\s*\S+",
        "[redacted-secret]",
    ),
]

PII_PATTERNS = [(name, re.compile(p), label) for name, p, label in _PII_SOURCES]


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Redact PII/secrets from text.

    Returns:
        (redacted_text, list of PII type names that matched)
    """
    found: list[str] = []
    out = text
    for name, pattern, label in PII_PATTERNS:
        if pattern.search(out):
            found.append(name)
            out = pattern.sub(label, out)
    return out, found


def matches_any(patterns, text: str) -> bool:
    """True if any compiled pattern matches text."""
    return any(p.search(text) for p in patterns)


def first_match(patterns, text: str):
    """Return the first matching pattern's match object (or None)."""
    for p in patterns:
        m = p.search(text)
        if m:
            return m
    return None
