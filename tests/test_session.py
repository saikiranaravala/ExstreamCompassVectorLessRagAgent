"""Tests for session management."""

import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from compass.services.session import Session, SessionBudget, QueryRecord, SessionManager


class TestSessionBudget:
    """Test SessionBudget class."""

    def test_create_budget(self):
        """Test creating session budget."""
        budget = SessionBudget(max_tool_calls=20, max_file_reads=8)

        assert budget.max_tool_calls == 20
        assert budget.max_file_reads == 8
        assert budget.tool_calls_used == 0
        assert budget.file_reads_used == 0

    def test_has_tool_calls_remaining(self):
        """Test checking tool call budget."""
        budget = SessionBudget(max_tool_calls=5)

        assert budget.has_tool_calls_remaining() is True
        budget.tool_calls_used = 5
        assert budget.has_tool_calls_remaining() is False

    def test_has_file_reads_remaining(self):
        """Test checking file read budget."""
        budget = SessionBudget(max_file_reads=3)

        assert budget.has_file_reads_remaining() is True
        budget.file_reads_used = 3
        assert budget.has_file_reads_remaining() is False

    def test_increment_tool_calls_success(self):
        """Test incrementing tool calls within budget."""
        budget = SessionBudget(max_tool_calls=10)

        result = budget.increment_tool_calls(3)

        assert result is True
        assert budget.tool_calls_used == 3

    def test_increment_tool_calls_exceeds_budget(self):
        """Test incrementing tool calls exceeds budget."""
        budget = SessionBudget(max_tool_calls=5)
        budget.tool_calls_used = 4

        result = budget.increment_tool_calls(2)

        assert result is False
        assert budget.tool_calls_used == 4  # Unchanged

    def test_increment_file_reads_success(self):
        """Test incrementing file reads within budget."""
        budget = SessionBudget(max_file_reads=8)

        result = budget.increment_file_reads(2)

        assert result is True
        assert budget.file_reads_used == 2

    def test_increment_file_reads_exceeds_budget(self):
        """Test incrementing file reads exceeds budget."""
        budget = SessionBudget(max_file_reads=5)
        budget.file_reads_used = 4

        result = budget.increment_file_reads(2)

        assert result is False
        assert budget.file_reads_used == 4  # Unchanged

    def test_get_remaining_tool_calls(self):
        """Test getting remaining tool calls."""
        budget = SessionBudget(max_tool_calls=10)
        budget.tool_calls_used = 3

        remaining = budget.get_remaining_tool_calls()

        assert remaining == 7

    def test_get_remaining_file_reads(self):
        """Test getting remaining file reads."""
        budget = SessionBudget(max_file_reads=8)
        budget.file_reads_used = 5

        remaining = budget.get_remaining_file_reads()

        assert remaining == 3


class TestQueryRecord:
    """Test QueryRecord dataclass."""

    def test_create_query_record(self):
        """Test creating query record."""
        record = QueryRecord(
            query="What is Python?",
            variant="CloudNative",
            timestamp="2026-04-26T10:00:00",
        )

        assert record.query == "What is Python?"
        assert record.variant == "CloudNative"
        assert record.status == "pending"

    def test_query_record_completion(self):
        """Test completing query record."""
        record = QueryRecord(
            query="What is Python?",
            variant="CloudNative",
            timestamp="2026-04-26T10:00:00",
        )

        record.answer = "Python is a language"
        record.status = "completed"
        record.tool_calls_count = 2

        assert record.answer is not None
        assert record.status == "completed"


class TestSession:
    """Test Session dataclass."""

    def test_create_session(self):
        """Test creating session."""
        session = Session(
            session_id="session123",
            user_id="user456",
            created_at="2026-04-26T10:00:00",
            last_activity="2026-04-26T10:00:00",
        )

        assert session.session_id == "session123"
        assert session.user_id == "user456"
        assert session.variant == "CloudNative"

    def test_session_to_dict(self):
        """Test converting session to dict."""
        session = Session(
            session_id="session123",
            user_id="user456",
            created_at="2026-04-26T10:00:00",
            last_activity="2026-04-26T10:00:00",
        )

        data = session.to_dict()

        assert data["session_id"] == "session123"
        assert data["user_id"] == "user456"
        assert isinstance(data["queries"], list)
        assert isinstance(data["budget"], dict)

    def test_session_from_dict(self):
        """Test creating session from dict."""
        data = {
            "session_id": "session123",
            "user_id": "user456",
            "created_at": "2026-04-26T10:00:00",
            "last_activity": "2026-04-26T10:00:00",
            "variant": "ServerBased",
            "queries": [],
            "budget": {"max_tool_calls": 20, "max_file_reads": 8, "tool_calls_used": 0, "file_reads_used": 0},
            "metadata": {},
        }

        session = Session.from_dict(data)

        assert session.session_id == "session123"
        assert session.variant == "ServerBased"


class TestSessionManager:
    """Test SessionManager class."""

    @pytest.fixture
    def manager(self):
        """Create session manager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionManager(Path(tmpdir))

    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.sessions_dir.exists()
        assert len(manager.active_sessions) == 0

    def test_create_session(self, manager):
        """Test creating a session."""
        session = manager.create_session("user123", "CloudNative")

        assert session.user_id == "user123"
        assert session.variant == "CloudNative"
        assert session.session_id in manager.active_sessions

    def test_get_session(self, manager):
        """Test retrieving a session."""
        created = manager.create_session("user123")
        retrieved = manager.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id

    def test_get_nonexistent_session(self, manager):
        """Test retrieving non-existent session."""
        session = manager.get_session("nonexistent")

        assert session is None

    def test_add_query_to_session(self, manager):
        """Test adding query to session."""
        session = manager.create_session("user123")

        record = manager.add_query(
            session.session_id,
            "What is Python?",
            "CloudNative",
        )

        assert record is not None
        assert len(session.queries) == 1

    def test_add_query_to_nonexistent_session(self, manager):
        """Test adding query to non-existent session."""
        record = manager.add_query(
            "nonexistent",
            "What is Python?",
            "CloudNative",
        )

        assert record is None

    def test_update_query(self, manager):
        """Test updating query with answer."""
        session = manager.create_session("user123")
        manager.add_query(session.session_id, "What is Python?", "CloudNative")

        result = manager.update_query(
            session.session_id,
            0,
            "Python is a language",
            tool_calls_count=2,
            file_reads_count=1,
            status="completed",
        )

        assert result is True
        assert session.queries[0].answer == "Python is a language"

    def test_save_and_load_session(self, manager):
        """Test saving and loading session."""
        # Create and save
        session = manager.create_session("user123", "ServerBased")
        manager.add_query(session.session_id, "Test query", "ServerBased")
        save_result = manager.save_session(session.session_id)

        assert save_result is True

        # Load
        del manager.active_sessions[session.session_id]
        loaded = manager.load_session(session.session_id)

        assert loaded is not None
        assert loaded.user_id == "user123"
        assert len(loaded.queries) == 1

    def test_delete_session(self, manager):
        """Test deleting a session."""
        session = manager.create_session("user123")
        session_id = session.session_id

        result = manager.delete_session(session_id)

        assert result is True
        assert manager.get_session(session_id) is None

    def test_list_sessions(self, manager):
        """Test listing sessions."""
        manager.create_session("user123")
        manager.create_session("user456")
        manager.create_session("user123")

        all_sessions = manager.list_sessions()
        user123_sessions = manager.list_sessions("user123")

        assert len(all_sessions) == 3
        assert len(user123_sessions) == 2

    def test_cleanup_expired_sessions(self, manager):
        """Test cleaning up expired sessions."""
        session = manager.create_session("user123")

        # Manually set last_activity to old time
        old_time = (datetime.utcnow() - timedelta(hours=25)).isoformat()
        session.last_activity = old_time

        deleted_count = manager.cleanup_expired_sessions(max_age_hours=24)

        assert deleted_count == 1
        assert manager.get_session(session.session_id) is None

    def test_get_session_stats(self, manager):
        """Test getting session statistics."""
        session = manager.create_session("user123")
        manager.add_query(session.session_id, "Query 1", "CloudNative")
        manager.update_query(
            session.session_id,
            0,
            "Answer 1",
            tool_calls_count=3,
            file_reads_count=2,
            status="completed",
        )

        stats = manager.get_session_stats(session.session_id)

        assert stats is not None
        assert stats["total_queries"] == 1
        assert stats["completed_queries"] == 1
        assert stats["total_tool_calls"] == 3
        assert stats["total_file_reads"] == 2

    def test_get_session_stats_nonexistent(self, manager):
        """Test getting stats for non-existent session."""
        stats = manager.get_session_stats("nonexistent")

        assert stats is None

    def test_update_session_activity(self, manager):
        """Test updating session activity timestamp."""
        session = manager.create_session("user123")
        original_activity = session.last_activity

        time.sleep(0.1)  # Small delay

        manager.update_session(session)

        assert session.last_activity > original_activity
