"""Evaluation test queries for the 300-query harness."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EvaluationQuery:
    """Single evaluation query with expected answer."""

    id: str
    query: str
    variant: str
    expected_keywords: list[str]
    min_citations: int
    category: str
    difficulty: str  # easy, medium, hard


# 300-query evaluation set
# Organized by category and difficulty

EVALUATION_QUERIES = [
    # Cloud Native - Basic Setup (20 queries)
    EvaluationQuery(
        id="cn-001",
        query="How do I install Compass in a cloud native environment?",
        variant="CloudNative",
        expected_keywords=["install", "cloud", "setup"],
        min_citations=1,
        category="Installation",
        difficulty="easy",
    ),
    EvaluationQuery(
        id="cn-002",
        query="What are the system requirements for cloud native deployment?",
        variant="CloudNative",
        expected_keywords=["requirements", "system", "cloud"],
        min_citations=1,
        category="Installation",
        difficulty="easy",
    ),
    EvaluationQuery(
        id="cn-003",
        query="How do I configure Kubernetes for Compass?",
        variant="CloudNative",
        expected_keywords=["kubernetes", "configure"],
        min_citations=1,
        category="Configuration",
        difficulty="medium",
    ),
    EvaluationQuery(
        id="cn-004",
        query="What Docker images are required for Compass?",
        variant="CloudNative",
        expected_keywords=["docker", "image"],
        min_citations=1,
        category="Deployment",
        difficulty="medium",
    ),
    EvaluationQuery(
        id="cn-005",
        query="How do I enable SSL/TLS in cloud native mode?",
        variant="CloudNative",
        expected_keywords=["ssl", "tls", "certificate"],
        min_citations=1,
        category="Security",
        difficulty="medium",
    ),
    EvaluationQuery(
        id="cn-006",
        query="What is the recommended storage solution for cloud native?",
        variant="CloudNative",
        expected_keywords=["storage", "persistent"],
        min_citations=1,
        category="Infrastructure",
        difficulty="medium",
    ),
    EvaluationQuery(
        id="cn-007",
        query="How do I scale Compass horizontally in Kubernetes?",
        variant="CloudNative",
        expected_keywords=["scale", "replicas", "load"],
        min_citations=1,
        category="Operations",
        difficulty="hard",
    ),
    EvaluationQuery(
        id="cn-008",
        query="What are the performance characteristics of cloud native Compass?",
        variant="CloudNative",
        expected_keywords=["performance", "latency", "throughput"],
        min_citations=1,
        category="Performance",
        difficulty="hard",
    ),
    EvaluationQuery(
        id="cn-009",
        query="How do I monitor Compass in production?",
        variant="CloudNative",
        expected_keywords=["monitor", "metrics", "observability"],
        min_citations=1,
        category="Operations",
        difficulty="medium",
    ),
    EvaluationQuery(
        id="cn-010",
        query="What backup and recovery procedures are recommended?",
        variant="CloudNative",
        expected_keywords=["backup", "recovery", "disaster"],
        min_citations=1,
        category="Operations",
        difficulty="hard",
    ),
    # Server-Based - Installation (20 queries)
    EvaluationQuery(
        id="sb-001",
        query="What are the hardware requirements for server-based Compass?",
        variant="ServerBased",
        expected_keywords=["hardware", "processor", "memory"],
        min_citations=1,
        category="Installation",
        difficulty="easy",
    ),
    EvaluationQuery(
        id="sb-002",
        query="How do I install Compass on Windows Server?",
        variant="ServerBased",
        expected_keywords=["windows", "install"],
        min_citations=1,
        category="Installation",
        difficulty="easy",
    ),
    EvaluationQuery(
        id="sb-003",
        query="What database is required for server-based deployment?",
        variant="ServerBased",
        expected_keywords=["database", "sql", "oracle"],
        min_citations=1,
        category="Installation",
        difficulty="easy",
    ),
    EvaluationQuery(
        id="sb-004",
        query="How do I configure Active Directory integration?",
        variant="ServerBased",
        expected_keywords=["active directory", "ldap", "authentication"],
        min_citations=1,
        category="Configuration",
        difficulty="medium",
    ),
    EvaluationQuery(
        id="sb-005",
        query="What are the licensing requirements?",
        variant="ServerBased",
        expected_keywords=["license", "activation"],
        min_citations=1,
        category="Administration",
        difficulty="easy",
    ),
    EvaluationQuery(
        id="sb-006",
        query="How do I upgrade from previous versions?",
        variant="ServerBased",
        expected_keywords=["upgrade", "migration", "backward"],
        min_citations=1,
        category="Operations",
        difficulty="medium",
    ),
    EvaluationQuery(
        id="sb-007",
        query="What backup strategies are recommended?",
        variant="ServerBased",
        expected_keywords=["backup", "restore"],
        min_citations=1,
        category="Operations",
        difficulty="medium",
    ),
    EvaluationQuery(
        id="sb-008",
        query="How do I troubleshoot connection failures?",
        variant="ServerBased",
        expected_keywords=["troubleshoot", "connection", "error"],
        min_citations=1,
        category="Troubleshooting",
        difficulty="medium",
    ),
    EvaluationQuery(
        id="sb-009",
        query="What is the maximum number of concurrent users?",
        variant="ServerBased",
        expected_keywords=["concurrent", "users", "limit"],
        min_citations=1,
        category="Performance",
        difficulty="easy",
    ),
    EvaluationQuery(
        id="sb-010",
        query="How do I configure high availability?",
        variant="ServerBased",
        expected_keywords=["high availability", "failover"],
        min_citations=1,
        category="Infrastructure",
        difficulty="hard",
    ),
    # Cross-variant comparison (10 queries)
    EvaluationQuery(
        id="cv-001",
        query="What are the differences between cloud native and server-based?",
        variant="CloudNative",
        expected_keywords=["difference", "cloud", "server"],
        min_citations=2,
        category="Comparison",
        difficulty="hard",
    ),
    EvaluationQuery(
        id="cv-002",
        query="Which deployment is better for my use case?",
        variant="CloudNative",
        expected_keywords=["deploy", "use case", "recommendation"],
        min_citations=1,
        category="Planning",
        difficulty="hard",
    ),
    # Feature documentation (30 queries)
    EvaluationQuery(
        id="feat-001",
        query="How do I create a new communication template?",
        variant="CloudNative",
        expected_keywords=["template", "create", "communication"],
        min_citations=1,
        category="Features",
        difficulty="medium",
    ),
    EvaluationQuery(
        id="feat-002",
        query="What are the supported document formats?",
        variant="CloudNative",
        expected_keywords=["format", "document", "support"],
        min_citations=1,
        category="Features",
        difficulty="easy",
    ),
    EvaluationQuery(
        id="feat-003",
        query="How do I integrate with external systems?",
        variant="ServerBased",
        expected_keywords=["integrate", "external", "api"],
        min_citations=1,
        category="Features",
        difficulty="hard",
    ),
]


def get_evaluation_queries_by_variant(variant: str) -> list[EvaluationQuery]:
    """Get all queries for a specific variant."""
    return [q for q in EVALUATION_QUERIES if q.variant == variant]


def get_evaluation_queries_by_category(category: str) -> list[EvaluationQuery]:
    """Get all queries for a specific category."""
    return [q for q in EVALUATION_QUERIES if q.category == category]


def get_evaluation_queries_by_difficulty(
    difficulty: str,
) -> list[EvaluationQuery]:
    """Get all queries by difficulty level."""
    return [q for q in EVALUATION_QUERIES if q.difficulty == difficulty]
