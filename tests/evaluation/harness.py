"""Evaluation harness for running 300-query benchmark."""

import time
import logging
from typing import Optional

from compass.agent.agent import ReasoningAgent
from tests.evaluation.test_queries import EvaluationQuery
from tests.evaluation.metrics import QueryMetrics, MetricsCollector

logger = logging.getLogger(__name__)


class EvaluationHarness:
    """Run evaluation queries and collect metrics."""

    def __init__(self, agent: ReasoningAgent):
        """Initialize evaluation harness.

        Args:
            agent: ReasoningAgent instance
        """
        self.agent = agent
        self.collector = MetricsCollector()

    async def run_query(self, query: EvaluationQuery) -> QueryMetrics:
        """Execute a single evaluation query.

        Args:
            query: EvaluationQuery to run

        Returns:
            QueryMetrics with results
        """
        self.collector.start_query(query.id)
        start_time = time.time()

        try:
            # Execute query
            result = self.agent.query(query.query, query.variant)

            latency_ms = (time.time() - start_time) * 1000
            answer = result.get("answer", "")
            tool_calls = result.get("tool_calls", 0)
            citations = result.get("citations", [])

            # Count keywords found
            keywords_found = 0
            for keyword in query.expected_keywords:
                if keyword.lower() in answer.lower():
                    keywords_found += 1

            metrics = QueryMetrics(
                query_id=query.id,
                query_text=query.query,
                variant=query.variant,
                category=query.category,
                difficulty=query.difficulty,
                success=True,
                latency_ms=latency_ms,
                tool_calls=tool_calls,
                citations_count=len(citations),
                keywords_found=keywords_found,
                keywords_total=len(query.expected_keywords),
                answer_length=len(answer),
            )

            # Check if minimum citations met
            if len(citations) < query.min_citations:
                metrics.success = False
                metrics.error = (
                    f"Expected {query.min_citations} citations, got {len(citations)}"
                )

            logger.info(
                f"Query {query.id}: {latency_ms:.1f}ms, "
                f"{tool_calls} tools, {len(citations)} citations"
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            metrics = QueryMetrics(
                query_id=query.id,
                query_text=query.query,
                variant=query.variant,
                category=query.category,
                difficulty=query.difficulty,
                success=False,
                latency_ms=latency_ms,
                tool_calls=0,
                citations_count=0,
                keywords_found=0,
                keywords_total=len(query.expected_keywords),
                answer_length=0,
                error=str(e),
            )

            logger.error(f"Query {query.id} failed: {e}")

        self.collector.record_query(metrics)
        return metrics

    async def run_batch(
        self, queries: list[EvaluationQuery], batch_size: int = 10
    ) -> None:
        """Run a batch of queries.

        Args:
            queries: List of queries to run
            batch_size: Number of concurrent queries
        """
        logger.info(
            f"Starting evaluation harness with {len(queries)} queries, "
            f"batch size {batch_size}"
        )

        for i in range(0, len(queries), batch_size):
            batch = queries[i : i + batch_size]
            logger.info(
                f"Running batch {i // batch_size + 1}/{(len(queries) + batch_size - 1) // batch_size}"
            )

            for query in batch:
                await self.run_query(query)

        logger.info("Evaluation harness completed")

    def get_results(self):
        """Get evaluation results.

        Returns:
            EvaluationResults with all metrics
        """
        return self.collector.finalize()

    def print_summary(self) -> None:
        """Print evaluation summary to console."""
        results = self.get_results()

        print("\n" + "=" * 70)
        print("EVALUATION RESULTS SUMMARY")
        print("=" * 70)

        print(f"\nTotal Queries: {results.total_queries}")
        print(f"Successful: {results.successful_queries}")
        print(f"Failed: {results.failed_queries}")
        print(f"Success Rate: {self.collector.get_success_rate():.1f}%")

        print(f"\nLatency:")
        print(f"  Average: {results.avg_latency_ms:.1f}ms")
        print(f"  Min: {results.min_latency_ms:.1f}ms")
        print(f"  Max: {results.max_latency_ms:.1f}ms")

        print(f"\nTool Calls:")
        print(f"  Total: {results.total_tool_calls}")
        print(f"  Average per query: {results.avg_tool_calls:.1f}")

        print(f"\nCitations:")
        print(f"  Total: {results.total_citations}")
        print(f"  Average per query: {results.avg_citations:.1f}")
        print(
            f"  Queries meeting minimum: {results.citations_meeting_minimum}/{results.total_queries}"
        )

        print(f"\nKeyword Accuracy: {results.keyword_accuracy:.1f}%")

        print(f"\nAnswer Length:")
        if results.answer_length_stats:
            print(f"  Average: {results.answer_length_stats['avg']:.0f} chars")
            print(f"  Min: {results.answer_length_stats['min']}")
            print(f"  Max: {results.answer_length_stats['max']}")

        print(f"\nBy Variant:")
        for variant, rates in self.collector.get_variant_success_rates().items():
            print(f"  {variant}: {rates:.1f}%")

        print(f"\nBy Category:")
        for category, rates in self.collector.get_category_success_rates().items():
            print(f"  {category}: {rates:.1f}%")

        print(f"\nBy Difficulty:")
        for difficulty, rates in (
            self.collector.get_difficulty_success_rates().items()
        ):
            print(f"  {difficulty}: {rates:.1f}%")

        print("\n" + "=" * 70)
