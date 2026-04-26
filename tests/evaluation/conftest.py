"""Pytest configuration for evaluation tests."""

import pytest
import asyncio
from typing import AsyncGenerator

from compass.agent.agent import ReasoningAgent
from compass.services.session import SessionManager
from compass.services.audit import AuditLogger
from compass.indexer.search import BM25Index
from compass.indexer.index_tree import IndexTreeManager


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def session_manager(tmp_path):
    """Create temporary session manager."""
    return SessionManager(str(tmp_path / "sessions"))


@pytest.fixture
def audit_logger(tmp_path):
    """Create temporary audit logger."""
    return AuditLogger(str(tmp_path / "audit"))


@pytest.fixture
def search_index(tmp_path):
    """Create temporary BM25 search index."""
    return BM25Index(str(tmp_path / "search_index"))


@pytest.fixture
def index_tree_manager(tmp_path):
    """Create temporary index tree manager."""
    return IndexTreeManager(str(tmp_path / "index.json"))
