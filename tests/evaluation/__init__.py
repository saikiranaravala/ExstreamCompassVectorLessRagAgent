"""Evaluation framework for Compass RAG."""

from tests.evaluation.harness import EvaluationHarness
from tests.evaluation.metrics import MetricsCollector, EvaluationResults, QueryMetrics
from tests.evaluation.reporter import EvaluationReporter
from tests.evaluation.test_queries import (
    EvaluationQuery,
    EVALUATION_QUERIES,
    get_evaluation_queries_by_variant,
    get_evaluation_queries_by_category,
    get_evaluation_queries_by_difficulty,
)

__all__ = [
    "EvaluationHarness",
    "MetricsCollector",
    "EvaluationResults",
    "QueryMetrics",
    "EvaluationReporter",
    "EvaluationQuery",
    "EVALUATION_QUERIES",
    "get_evaluation_queries_by_variant",
    "get_evaluation_queries_by_category",
    "get_evaluation_queries_by_difficulty",
]
