"""Main FastAPI application."""

import logging
import os
import threading
import uuid

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from compass import __version__
from compass.api.gateway import APIGateway
from compass.config import settings
from compass.retrieval.service import QueryService
from compass.services.audit import AuditLogger, AuditEventType

logger = logging.getLogger(__name__)


def _bootstrap_langsmith() -> None:
    """Push LangSmith env vars into os.environ before LangGraph initializes its tracer.

    LangGraph reads LANGCHAIN_TRACING_V2 when the graph is compiled, so this must
    run at module load time — before any ReasoningAgent is instantiated.
    """
    if not settings.langchain_tracing_v2:
        return
    if not settings.langchain_api_key:
        logger.warning(
            "LANGCHAIN_TRACING_V2=true but LANGCHAIN_API_KEY is not set — "
            "LangSmith tracing will be disabled."
        )
        return
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    logger.info(f"LangSmith tracing enabled (project: {settings.langchain_project})")


_bootstrap_langsmith()

app = FastAPI(
    title="Compass RAG",
    description="Vectorless Retrieval-Augmented Generation agent for OpenText Exstream documentation",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API gateway with authentication
gateway = APIGateway(app)
gateway.register_routes()

# Shared retrieval/answering service (also used by agent tools)
query_service = QueryService()

# Audit logger for guardrail decisions on the active query flow
audit_logger = AuditLogger()


def _audit_guardrail(session_id: str, identity: str, result: dict) -> None:
    """Record guardrail decisions to the audit log (no raw query text)."""
    guardrail = result.get("guardrail") or {}
    inp = guardrail.get("input", {})
    out = guardrail.get("output", {})
    decision = inp.get("decision")
    try:
        if decision in ("refuse", "rate_limit"):
            event = (
                AuditEventType.RATE_LIMITED
                if decision == "rate_limit"
                else AuditEventType.GUARDRAIL_BLOCKED
            )
            audit_logger.log_event(event, session_id, identity, inp, severity="WARNING")
        elif decision == "sanitize":
            audit_logger.log_event(
                AuditEventType.GUARDRAIL_SANITIZED, session_id, identity, inp
            )
        if out.get("category") in ("low_confidence", "leaked", "ungrounded"):
            audit_logger.log_event(
                AuditEventType.GUARDRAIL_FLAGGED, session_id, identity, out,
                severity=out.get("severity", "INFO"),
            )
    except Exception as e:  # audit must never break the request
        logger.debug(f"Audit logging failed: {e}")


@app.on_event("startup")
def _warm_indexes() -> None:
    """Build search indexes in the background so the first query is fast."""
    threading.Thread(target=query_service.warmup, daemon=True).start()


# NOTE: endpoints below are sync (`def`) on purpose — FastAPI runs them in a
# threadpool, so index builds and LLM calls do not block the event loop.


def _caller_identity(request: Request) -> str:
    """Identity for rate limiting: authenticated user id, else client IP."""
    user = getattr(request.state, "user", None)
    if user is not None and getattr(user, "user_id", None):
        return f"user:{user.user_id}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


@app.post("/api/v1/query")
def query(request: Request, query: str, variant: str = "CloudNative", session_id: str = None) -> dict:
    """Query endpoint — guardrails + full-corpus BM25 retrieval + LLM answer."""
    try:
        gateway.get_current_user(request)
    except HTTPException:
        pass  # demo mode allows unauthenticated access

    session_id = session_id or str(uuid.uuid4())
    if variant not in ("CloudNative", "ServerBased"):
        raise HTTPException(status_code=400, detail=f"Invalid variant: {variant}")

    identity = _caller_identity(request)
    result = query_service.query(query, variant, identity=identity)
    _audit_guardrail(session_id, identity, result)

    guardrail = result.get("guardrail", {})
    # A rate-limit refusal maps to HTTP 429 so clients can back off correctly.
    if guardrail.get("input", {}).get("decision") == "rate_limit":
        raise HTTPException(status_code=429, detail=result["answer"])

    return {
        "session_id": session_id,
        "answer": result["answer"],
        "citations": result["citations"],
        "tool_calls": result["tool_calls"],
        "processing_time": result["processing_time"],
        "variant": variant,
        "model": result["model"],
        "trace": result["trace"],
        "guardrail": guardrail,
    }


@app.get("/api/v1/session/{session_id}")
def get_session(session_id: str, request: Request) -> dict:
    """Get session information."""
    try:
        gateway.get_current_user(request)
    except HTTPException:
        pass

    return {
        "session_id": session_id,
        "created_at": "2026-04-27T00:00:00Z",
        "last_activity": "2026-04-27T00:00:00Z",
        "variant": "CloudNative",
        "statistics": {
            "total_queries": 1,
            "total_tool_calls": 0,
            "total_file_reads": 0,
            "average_response_time": 0.1,
        },
    }


@app.delete("/api/v1/session/{session_id}")
def close_session(session_id: str, request: Request) -> dict:
    """Close a session."""
    try:
        gateway.get_current_user(request)
    except HTTPException:
        pass

    return {"message": "Session closed", "session_id": session_id}


@app.get("/api/v1/session/{session_id}/queries")
def get_session_queries(session_id: str, request: Request) -> dict:
    """Get all queries in a session."""
    try:
        gateway.get_current_user(request)
    except HTTPException:
        pass

    return {
        "session_id": session_id,
        "queries": [],
    }


@app.get("/health")
def health_check():
    """Health check endpoint (includes index status)."""
    return {
        "status": "healthy",
        "service": "compass-rag",
        "version": __version__,
        "retrieval": query_service.status(),
    }


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Compass RAG API",
        "version": __version__,
        "docs": "/docs",
    }
