#!/usr/bin/env python
"""Run full evaluation harness for Compass RAG."""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compass.agent.agent import ReasoningAgent
from compass.services.session import SessionManager
from compass.services.audit import AuditLogger
from compass.indexer.index_tree import IndexTreeManager
from tests.evaluation import (
    EvaluationHarness,
    EvaluationReporter,
    EVALUATION_QUERIES,
    get_evaluation_queries_by_variant,
    get_evaluation_queries_by_difficulty,
    get_evaluation_queries_by_category,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run evaluation harness."""
    parser = argparse.ArgumentParser(
        description="Run Compass RAG evaluation harness"
    )
    parser.add_argument(
        "--variant",
        help="Filter by variant (CloudNative, ServerBased)",
        default=None,
    )
    parser.add_argument(
        "--difficulty",
        help="Filter by difficulty (easy, medium, hard)",
        default=None,
    )
    parser.add_argument(
        "--category",
        help="Filter by category (Installation, Configuration, etc.)",
        default=None,
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of queries",
        default=None,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Batch size for concurrent execution",
        default=10,
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for report output",
        default="evaluation_reports",
    )
    parser.add_argument(
        "--skip-reports",
        action="store_true",
        help="Skip report generation",
    )

    args = parser.parse_args()

    # Get queries based on filters
    queries = EVALUATION_QUERIES

    if args.variant:
        queries = get_evaluation_queries_by_variant(args.variant)
        logger.info(f"Filtered to {len(queries)} queries for variant: {args.variant}")

    if args.difficulty:
        queries = [q for q in queries if q.difficulty == args.difficulty]
        logger.info(
            f"Filtered to {len(queries)} queries for difficulty: {args.difficulty}"
        )

    if args.category:
        queries = [q for q in queries if q.category == args.category]
        logger.info(
            f"Filtered to {len(queries)} queries for category: {args.category}"
        )

    if args.limit:
        queries = queries[: args.limit]
        logger.info(f"Limited to {len(queries)} queries")

    if not queries:
        logger.error("No queries to run")
        return 1

    logger.info(f"Running {len(queries)} evaluation queries")

    # Initialize components
    logger.info("Initializing Compass RAG agent...")
    session_dir = Path(".compass_sessions")
    audit_dir = Path(".compass_audit")

    session_manager = SessionManager(str(session_dir))
    audit_logger = AuditLogger(str(audit_dir))
    index_tree_manager = IndexTreeManager()

    try:
        agent = ReasoningAgent(
            index_tree_manager=index_tree_manager,
            session_manager=session_manager,
            audit_logger=audit_logger,
        )
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        logger.warning(
            "Note: Agent initialization may fail if index tree not built. "
            "This is expected in test environments."
        )
        # Continue anyway for testing
        agent = None

    # Create and run harness
    if agent:
        harness = EvaluationHarness(agent)

        logger.info(f"Starting evaluation with batch size {args.batch_size}")
        start_time = asyncio.get_event_loop().time()

        try:
            await harness.run_batch(queries, batch_size=args.batch_size)
        except KeyboardInterrupt:
            logger.info("Evaluation interrupted by user")
            return 130
        except Exception as e:
            logger.error(f"Evaluation failed: {e}", exc_info=True)
            return 1

        elapsed_time = asyncio.get_event_loop().time() - start_time

        # Print summary
        harness.print_summary()
        logger.info(f"Evaluation completed in {elapsed_time:.1f} seconds")

        # Generate reports
        if not args.skip_reports:
            logger.info(f"Generating reports to {args.output_dir}")
            results = harness.get_results()
            reporter = EvaluationReporter(results, Path(args.output_dir))

            try:
                report_files = reporter.save_all_reports()
                for report_type, file_path in report_files.items():
                    logger.info(f"Saved {report_type.upper()} report: {file_path}")
            except Exception as e:
                logger.error(f"Failed to generate reports: {e}", exc_info=True)
                return 1

        return 0
    else:
        logger.error("Cannot run evaluation without agent")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
