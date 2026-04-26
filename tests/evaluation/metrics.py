"""Evaluation metrics collection and analysis."""

import time
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class QueryMetrics:
    """Metrics for a single query evaluation."""

    query_id: str
    query_text: str
    variant: str
    category: str
    difficulty: str
    success: bool
    latency_ms: float
    tool_calls: int
    citations_count: int
    keywords_found: int
    keywords_total: int
    answer_length: int
    error: Optional[str] = None


@dataclass
class EvaluationResults:
    """Aggregated evaluation results."""

    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0

    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0

    total_tool_calls: int = 0
    avg_tool_calls: float = 0.0

    total_citations: int = 0
    avg_citations: float = 0.0
    citations_meeting_minimum: int = 0

    keyword_accuracy: float = 0.0  # % of expected keywords found
    answer_length_stats: dict = field(default_factory=dict)

    results_by_variant: dict = field(default_factory=dict)
    results_by_category: dict = field(default_factory=dict)
    results_by_difficulty: dict = field(default_factory=dict)

    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    queries: list[QueryMetrics] = field(default_factory=list)


class MetricsCollector:
    """Collect and aggregate evaluation metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.results = EvaluationResults()
        self.query_times = {}

    def start_query(self, query_id: str) -> None:
        """Mark query start time."""
        self.query_times[query_id] = time.time()

    def record_query(self, metrics: QueryMetrics) -> None:
        """Record query metrics."""
        self.results.queries.append(metrics)
        self.results.total_queries += 1

        if metrics.success:
            self.results.successful_queries += 1
        else:
            self.results.failed_queries += 1

        # Latency stats
        self.results.total_latency_ms += metrics.latency_ms
        self.results.min_latency_ms = min(
            self.results.min_latency_ms, metrics.latency_ms
        )
        self.results.max_latency_ms = max(
            self.results.max_latency_ms, metrics.latency_ms
        )

        # Tool calls
        self.results.total_tool_calls += metrics.tool_calls

        # Citations
        self.results.total_citations += metrics.citations_count
        if metrics.citations_count > 0:
            self.results.citations_meeting_minimum += 1

        # Variant breakdown
        if metrics.variant not in self.results.results_by_variant:
            self.results.results_by_variant[metrics.variant] = {
                "total": 0,
                "successful": 0,
                "avg_latency": 0.0,
            }
        variant_stats = self.results.results_by_variant[metrics.variant]
        variant_stats["total"] += 1
        if metrics.success:
            variant_stats["successful"] += 1

        # Category breakdown
        if metrics.category not in self.results.results_by_category:
            self.results.results_by_category[metrics.category] = {
                "total": 0,
                "successful": 0,
            }
        cat_stats = self.results.results_by_category[metrics.category]
        cat_stats["total"] += 1
        if metrics.success:
            cat_stats["successful"] += 1

        # Difficulty breakdown
        if metrics.difficulty not in self.results.results_by_difficulty:
            self.results.results_by_difficulty[metrics.difficulty] = {
                "total": 0,
                "successful": 0,
            }
        diff_stats = self.results.results_by_difficulty[metrics.difficulty]
        diff_stats["total"] += 1
        if metrics.success:
            diff_stats["successful"] += 1

    def finalize(self) -> EvaluationResults:
        """Calculate final statistics."""
        if self.results.total_queries > 0:
            self.results.avg_latency_ms = (
                self.results.total_latency_ms / self.results.total_queries
            )
            self.results.avg_tool_calls = (
                self.results.total_tool_calls / self.results.total_queries
            )
            self.results.avg_citations = (
                self.results.total_citations / self.results.total_queries
            )

            # Calculate keyword accuracy
            total_keywords = sum(q.keywords_total for q in self.results.queries)
            found_keywords = sum(q.keywords_found for q in self.results.queries)
            if total_keywords > 0:
                self.results.keyword_accuracy = (
                    found_keywords / total_keywords * 100
                )

            # Calculate citation success rate
            queries_with_citations = sum(
                1 for q in self.results.queries if q.citations_count > 0
            )
            if self.results.total_queries > 0:
                citation_rate = queries_with_citations / self.results.total_queries * 100

            # Answer length stats
            if self.results.queries:
                lengths = [q.answer_length for q in self.results.queries]
                self.results.answer_length_stats = {
                    "min": min(lengths),
                    "max": max(lengths),
                    "avg": sum(lengths) / len(lengths),
                }

            # Update variant latency
            for variant, stats in self.results.results_by_variant.items():
                variant_queries = [
                    q for q in self.results.queries if q.variant == variant
                ]
                if variant_queries:
                    latencies = [q.latency_ms for q in variant_queries]
                    stats["avg_latency"] = sum(latencies) / len(latencies)

        return self.results

    def get_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.results.total_queries == 0:
            return 0.0
        return (
            self.results.successful_queries / self.results.total_queries * 100
        )

    def get_variant_success_rates(self) -> dict[str, float]:
        """Get success rates by variant."""
        rates = {}
        for variant, stats in self.results.results_by_variant.items():
            if stats["total"] > 0:
                rates[variant] = stats["successful"] / stats["total"] * 100
        return rates

    def get_category_success_rates(self) -> dict[str, float]:
        """Get success rates by category."""
        rates = {}
        for category, stats in self.results.results_by_category.items():
            if stats["total"] > 0:
                rates[category] = stats["successful"] / stats["total"] * 100
        return rates

    def get_difficulty_success_rates(self) -> dict[str, float]:
        """Get success rates by difficulty."""
        rates = {}
        for difficulty, stats in self.results.results_by_difficulty.items():
            if stats["total"] > 0:
                rates[difficulty] = stats["successful"] / stats["total"] * 100
        return rates
