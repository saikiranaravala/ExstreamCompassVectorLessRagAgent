"""Integration tests running the evaluation harness."""

import pytest
from pathlib import Path

from tests.evaluation.test_queries import EVALUATION_QUERIES
from tests.evaluation.harness import EvaluationHarness
from tests.evaluation.reporter import EvaluationReporter


@pytest.mark.asyncio
class TestEvaluationHarness:
    """Test evaluation harness functionality."""

    async def test_run_single_query(self, session_manager, audit_logger):
        """Test running a single evaluation query."""
        from compass.agent.agent import ReasoningAgent
        from compass.indexer.index_tree import IndexTreeManager

        # Initialize agent
        agent = ReasoningAgent(
            index_tree_manager=IndexTreeManager(),
            session_manager=session_manager,
            audit_logger=audit_logger,
        )

        harness = EvaluationHarness(agent)

        # Run first query
        query = EVALUATION_QUERIES[0]
        metrics = await harness.run_query(query)

        assert metrics.query_id == query.id
        assert metrics.variant == query.variant
        assert metrics.success is True or metrics.error is not None

    async def test_run_query_batch(self, session_manager, audit_logger):
        """Test running a batch of queries."""
        from compass.agent.agent import ReasoningAgent
        from compass.indexer.index_tree import IndexTreeManager

        agent = ReasoningAgent(
            index_tree_manager=IndexTreeManager(),
            session_manager=session_manager,
            audit_logger=audit_logger,
        )

        harness = EvaluationHarness(agent)

        # Run first 5 queries as batch
        await harness.run_batch(EVALUATION_QUERIES[:5], batch_size=2)

        results = harness.get_results()
        assert results.total_queries == 5
        assert results.total_queries > 0

    def test_evaluation_query_structure(self):
        """Test evaluation queries are properly structured."""
        assert len(EVALUATION_QUERIES) > 0

        for query in EVALUATION_QUERIES:
            assert query.id
            assert query.query
            assert query.variant in ["CloudNative", "ServerBased"]
            assert query.expected_keywords
            assert query.min_citations > 0
            assert query.category
            assert query.difficulty in ["easy", "medium", "hard"]

    def test_metrics_aggregation(self, session_manager, audit_logger):
        """Test metrics collector aggregation."""
        from tests.evaluation.metrics import QueryMetrics

        harness = EvaluationHarness(None)

        # Create test metrics
        for i in range(3):
            metrics = QueryMetrics(
                query_id=f"test-{i}",
                query_text="test query",
                variant="CloudNative",
                category="Test",
                difficulty="easy",
                success=i < 2,  # 2 successful, 1 failed
                latency_ms=100.0 + (i * 10),
                tool_calls=3,
                citations_count=2,
                keywords_found=3,
                keywords_total=3,
                answer_length=500,
            )
            harness.collector.record_query(metrics)

        results = harness.collector.finalize()

        assert results.total_queries == 3
        assert results.successful_queries == 2
        assert results.failed_queries == 1
        assert results.avg_latency_ms == pytest.approx(110.0)

    def test_report_generation(self, session_manager, audit_logger, tmp_path):
        """Test evaluation report generation."""
        from tests.evaluation.metrics import QueryMetrics

        harness = EvaluationHarness(None)

        # Create test metrics
        for i in range(3):
            metrics = QueryMetrics(
                query_id=f"test-{i}",
                query_text="test query",
                variant="CloudNative",
                category="Test",
                difficulty="easy",
                success=True,
                latency_ms=100.0,
                tool_calls=3,
                citations_count=2,
                keywords_found=3,
                keywords_total=3,
                answer_length=500,
            )
            harness.collector.record_query(metrics)

        results = harness.collector.finalize()
        reporter = EvaluationReporter(results, tmp_path)

        # Test report generation
        json_report = reporter.generate_json_report()
        assert "total_queries" in json_report
        assert "3" in json_report

        csv_report = reporter.generate_csv_report()
        assert "test-0" in csv_report
        assert "CloudNative" in csv_report

        html_report = reporter.generate_html_report()
        assert "Compass RAG Evaluation Report" in html_report

    def test_query_filtering(self):
        """Test query filtering functionality."""
        from tests.evaluation.test_queries import (
            get_evaluation_queries_by_variant,
            get_evaluation_queries_by_category,
            get_evaluation_queries_by_difficulty,
        )

        # Test variant filtering
        cloud_native_queries = get_evaluation_queries_by_variant("CloudNative")
        assert all(q.variant == "CloudNative" for q in cloud_native_queries)

        server_based_queries = get_evaluation_queries_by_variant("ServerBased")
        assert all(q.variant == "ServerBased" for q in server_based_queries)

        # Test category filtering
        installation_queries = get_evaluation_queries_by_category("Installation")
        assert all(q.category == "Installation" for q in installation_queries)

        # Test difficulty filtering
        easy_queries = get_evaluation_queries_by_difficulty("easy")
        assert all(q.difficulty == "easy" for q in easy_queries)
