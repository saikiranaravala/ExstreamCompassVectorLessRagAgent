"""OpenTelemetry instrumentation for Compass RAG."""

import os
import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)


# Custom metrics
query_counter = Counter(
    "compass_queries_total",
    "Total queries processed",
    ["variant", "category", "status"],
)

query_latency = Histogram(
    "compass_query_latency_seconds",
    "Query processing latency",
    ["variant"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

tool_calls_counter = Counter(
    "compass_tool_calls_total",
    "Total tool calls executed",
    ["tool_name", "status"],
)

citations_counter = Counter(
    "compass_citations_total",
    "Total citations generated",
    ["variant"],
)

active_sessions_gauge = Gauge(
    "compass_active_sessions",
    "Number of active sessions",
)

index_size_gauge = Gauge(
    "compass_index_size_bytes",
    "Size of search index in bytes",
)

budget_utilization = Histogram(
    "compass_budget_utilization",
    "Budget utilization per query",
    ["budget_type"],  # tool_calls, file_reads
)


def initialize_telemetry(app_name: str = "compass-rag") -> None:
    """Initialize OpenTelemetry instrumentation.

    Args:
        app_name: Name of the application
    """
    # Get configuration from environment
    jaeger_enabled = os.getenv("JAEGER_ENABLED", "true").lower() == "true"
    prometheus_enabled = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"

    jaeger_host = os.getenv("JAEGER_HOST", "localhost")
    jaeger_port = int(os.getenv("JAEGER_PORT", "6831"))
    jaeger_agent_port = int(os.getenv("JAEGER_AGENT_PORT", "6831"))

    # Create resource
    resource = Resource.create(
        {
            "service.name": app_name,
            "service.version": os.getenv("SERVICE_VERSION", "0.0.1"),
            "environment": os.getenv("ENVIRONMENT", "development"),
        }
    )

    # Initialize tracing
    if jaeger_enabled:
        logger.info(
            f"Initializing Jaeger tracer ({jaeger_host}:{jaeger_agent_port})"
        )

        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_agent_port,
        )

        trace_provider = TracerProvider(resource=resource)
        trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        trace.set_tracer_provider(trace_provider)

    # Initialize metrics
    metric_readers = []

    if prometheus_enabled:
        logger.info("Initializing Prometheus metrics")
        metric_readers.append(PrometheusMetricReader())

    # Also add OTLP exporter for metrics
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        logger.info(f"Initializing OTLP metrics exporter ({otlp_endpoint})")
        metric_readers.append(
            PeriodicExportingMetricReader(OTLPMetricExporter(otlp_endpoint))
        )

    if metric_readers:
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=metric_readers,
        )
        metrics.set_meter_provider(meter_provider)

    # Instrument libraries
    logger.info("Instrumenting libraries")
    FastAPIInstrumentor.instrument_app(None)  # Will be called with app later
    RequestsInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    LoggingInstrumentor().instrument()

    logger.info("OpenTelemetry initialization complete")


def instrument_fastapi_app(app) -> None:
    """Instrument FastAPI application.

    Args:
        app: FastAPI application instance
    """
    FastAPIInstrumentor.instrument_app(app)


def record_query(variant: str, category: str, status: str, latency: float) -> None:
    """Record query execution metrics.

    Args:
        variant: Documentation variant
        category: Query category
        status: Query status (success/failure)
        latency: Query processing time in seconds
    """
    query_counter.labels(variant=variant, category=category, status=status).inc()
    query_latency.labels(variant=variant).observe(latency)


def record_tool_call(tool_name: str, status: str = "success") -> None:
    """Record tool execution.

    Args:
        tool_name: Name of tool executed
        status: Execution status
    """
    tool_calls_counter.labels(tool_name=tool_name, status=status).inc()


def record_citations(variant: str, count: int) -> None:
    """Record citations generated.

    Args:
        variant: Documentation variant
        count: Number of citations
    """
    citations_counter.labels(variant=variant).inc(count)


def set_active_sessions(count: int) -> None:
    """Update active session count.

    Args:
        count: Current active sessions
    """
    active_sessions_gauge.set(count)


def set_index_size(size_bytes: int) -> None:
    """Update index size metric.

    Args:
        size_bytes: Size in bytes
    """
    index_size_gauge.set(size_bytes)


def record_budget_utilization(budget_type: str, utilization: float) -> None:
    """Record budget utilization.

    Args:
        budget_type: Type of budget (tool_calls, file_reads)
        utilization: Utilization percentage (0-100)
    """
    budget_utilization.labels(budget_type=budget_type).observe(utilization / 100.0)


def get_tracer(name: str = "compass") -> trace.Tracer:
    """Get tracer instance.

    Args:
        name: Tracer name

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def get_meter(name: str = "compass") -> metrics.Meter:
    """Get meter instance.

    Args:
        name: Meter name

    Returns:
        Meter instance
    """
    return metrics.get_meter(name)
