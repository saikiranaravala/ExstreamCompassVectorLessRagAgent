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


@app.on_event("startup")
def _warm_indexes() -> None:
    """Build search indexes in the background so the first query is fast."""
    threading.Thread(target=query_service.warmup, daemon=True).start()


# NOTE: endpoints below are sync (`def`) on purpose — FastAPI runs them in a
# threadpool, so index builds and LLM calls do not block the event loop.


@app.post("/api/v1/query")
def query(request: Request, query: str, variant: str = "CloudNative", session_id: str = None) -> dict:
    """Query endpoint — full-corpus BM25 retrieval + structured LLM answer."""
    try:
        gateway.get_current_user(request)
    except HTTPException:
        pass  # demo mode allows unauthenticated access

    session_id = session_id or str(uuid.uuid4())
    if variant not in ("CloudNative", "ServerBased"):
        raise HTTPException(status_code=400, detail=f"Invalid variant: {variant}")

    result = query_service.query(query, variant)

    return {
        "session_id": session_id,
        "answer": result["answer"],
        "citations": result["citations"],
        "tool_calls": result["tool_calls"],
        "processing_time": result["processing_time"],
        "variant": variant,
        "model": result["model"],
        "trace": result["trace"],
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
