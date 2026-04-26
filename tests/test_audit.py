"""Tests for audit logging."""

import tempfile
from pathlib import Path

import pytest

from compass.services.audit import AuditEventType, AuditEvent, AuditLogger


class TestAuditEventType:
    """Test AuditEventType enum."""

    def test_event_types_exist(self):
        """Test that key event types exist."""
        assert AuditEventType.SESSION_CREATED
        assert AuditEventType.QUERY_SUBMITTED
        assert AuditEventType.TOOL_CALLED
        assert AuditEventType.BUDGET_EXCEEDED


class TestAuditEvent:
    """Test AuditEvent dataclass."""

    def test_create_event(self):
        """Test creating audit event."""
        event = AuditEvent(
            timestamp="2026-04-26T10:00:00",
            event_type="test_event",
            session_id="session123",
            user_id="user456",
            details={"key": "value"},
        )

        assert event.event_type == "test_event"
        assert event.session_id == "session123"

    def test_event_to_dict(self):
        """Test converting event to dict."""
        event = AuditEvent(
            timestamp="2026-04-26T10:00:00",
            event_type="test",
            session_id="session123",
            user_id="user456",
            details={"key": "value"},
        )

        data = event.to_dict()

        assert data["event_type"] == "test"
        assert data["session_id"] == "session123"
        assert isinstance(data["details"], dict)

    def test_event_to_json_line(self):
        """Test converting event to JSON line."""
        event = AuditEvent(
            timestamp="2026-04-26T10:00:00",
            event_type="test",
            session_id="session123",
            user_id="user456",
            details={"key": "value"},
        )

        json_line = event.to_json_line()

        assert isinstance(json_line, str)
        assert "test_event" in json_line or "test" in json_line
        assert "session123" in json_line


class TestAuditLogger:
    """Test AuditLogger class."""

    @pytest.fixture
    def logger(self):
        """Create audit logger with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield AuditLogger(Path(tmpdir))

    def test_logger_initialization(self, logger):
        """Test logger initialization."""
        assert logger.log_dir.exists()
        assert len(logger.events) == 0

    def test_log_event(self, logger):
        """Test logging an event."""
        event = logger.log_event(
            AuditEventType.SESSION_CREATED,
            "session123",
            "user456",
            {"variant": "CloudNative"},
        )

        assert event is not None
        assert len(logger.events) == 1

    def test_log_session_created(self, logger):
        """Test logging session creation."""
        event = logger.log_session_created(
            "session123",
            "user456",
            "CloudNative",
        )

        assert event.event_type == AuditEventType.SESSION_CREATED.value
        assert event.details["variant"] == "CloudNative"

    def test_log_session_closed(self, logger):
        """Test logging session closure."""
        event = logger.log_session_closed(
            "session123",
            "user456",
            query_count=5,
        )

        assert event.event_type == AuditEventType.SESSION_CLOSED.value
        assert event.details["query_count"] == 5

    def test_log_query_submitted(self, logger):
        """Test logging query submission."""
        event = logger.log_query_submitted(
            "session123",
            "user456",
            "What is Python?",
            "CloudNative",
        )

        assert event.event_type == AuditEventType.QUERY_SUBMITTED.value
        assert "Python" in event.details["query"]

    def test_log_query_completed(self, logger):
        """Test logging query completion."""
        event = logger.log_query_completed(
            "session123",
            "user456",
            "What is Python?",
            tool_calls_count=3,
            file_reads_count=2,
            citations_count=2,
        )

        assert event.event_type == AuditEventType.QUERY_COMPLETED.value
        assert event.details["tool_calls"] == 3

    def test_log_query_failed(self, logger):
        """Test logging query failure."""
        event = logger.log_query_failed(
            "session123",
            "user456",
            "Test query",
            "Connection timeout",
        )

        assert event.event_type == AuditEventType.QUERY_FAILED.value
        assert event.severity == "WARNING"

    def test_log_tool_called(self, logger):
        """Test logging tool call."""
        event = logger.log_tool_called(
            "session123",
            "user456",
            "lexical_search",
            {"query": "Python", "limit": 10},
        )

        assert event.event_type == AuditEventType.TOOL_CALLED.value
        assert event.details["tool"] == "lexical_search"

    def test_log_tool_succeeded(self, logger):
        """Test logging successful tool execution."""
        event = logger.log_tool_succeeded(
            "session123",
            "user456",
            "lexical_search",
            "Found 5 results",
        )

        assert event.event_type == AuditEventType.TOOL_SUCCEEDED.value

    def test_log_tool_failed(self, logger):
        """Test logging tool failure."""
        event = logger.log_tool_failed(
            "session123",
            "user456",
            "read_html",
            "File not found",
        )

        assert event.event_type == AuditEventType.TOOL_FAILED.value
        assert event.severity == "WARNING"

    def test_log_budget_exceeded(self, logger):
        """Test logging budget exceeded."""
        event = logger.log_budget_exceeded(
            "session123",
            "user456",
            "tool_calls",
            current=20,
            limit=20,
        )

        assert event.event_type == AuditEventType.BUDGET_EXCEEDED.value
        assert event.details["budget_type"] == "tool_calls"

    def test_log_variant_violation(self, logger):
        """Test logging variant violation."""
        event = logger.log_variant_violation(
            "session123",
            "user456",
            attempted_variant="CloudNative",
            allowed_variant="ServerBased",
            resource="docs/ServerBased/file.html",
        )

        assert event.event_type == AuditEventType.VARIANT_VIOLATION.value
        assert event.severity == "WARNING"

    def test_log_access_denied(self, logger):
        """Test logging access denial."""
        event = logger.log_access_denied(
            "session123",
            "user456",
            "Insufficient permissions",
        )

        assert event.event_type == AuditEventType.ACCESS_DENIED.value

    def test_log_error(self, logger):
        """Test logging error."""
        event = logger.log_error(
            "session123",
            "user456",
            "Internal server error",
            error_type="RuntimeError",
        )

        assert event.event_type == AuditEventType.ERROR.value
        assert event.severity == "ERROR"

    def test_get_events_all(self, logger):
        """Test getting all events."""
        logger.log_session_created("session123", "user456", "CloudNative")
        logger.log_query_submitted("session123", "user456", "Test", "CloudNative")

        events = logger.get_events()

        assert len(events) == 2

    def test_get_events_filter_by_session(self, logger):
        """Test filtering events by session."""
        logger.log_session_created("session123", "user456", "CloudNative")
        logger.log_session_created("session456", "user456", "ServerBased")

        events = logger.get_events(session_id="session123")

        assert len(events) == 1
        assert events[0].session_id == "session123"

    def test_get_events_filter_by_user(self, logger):
        """Test filtering events by user."""
        logger.log_session_created("session123", "user456", "CloudNative")
        logger.log_session_created("session123", "user789", "ServerBased")

        events = logger.get_events(user_id="user456")

        assert len(events) == 1
        assert events[0].user_id == "user456"

    def test_get_events_filter_by_type(self, logger):
        """Test filtering events by type."""
        logger.log_session_created("session123", "user456", "CloudNative")
        logger.log_query_submitted("session123", "user456", "Test", "CloudNative")

        events = logger.get_events(event_type="session_created")

        assert len(events) == 1

    def test_get_session_audit_trail(self, logger):
        """Test getting session audit trail."""
        logger.log_session_created("session123", "user456", "CloudNative")
        logger.log_query_submitted("session123", "user456", "Test", "CloudNative")
        logger.log_session_closed("session123", "user456", 1)

        trail = logger.get_session_audit_trail("session123")

        assert len(trail) == 3

    def test_get_user_audit_trail(self, logger):
        """Test getting user audit trail."""
        logger.log_session_created("session123", "user456", "CloudNative")
        logger.log_session_created("session456", "user456", "ServerBased")

        trail = logger.get_user_audit_trail("user456")

        assert len(trail) == 2

    def test_get_statistics(self, logger):
        """Test getting audit statistics."""
        logger.log_session_created("session123", "user456", "CloudNative")
        logger.log_query_submitted("session123", "user456", "Test", "CloudNative")

        stats = logger.get_statistics()

        assert stats["total_events"] == 2
        assert "session_created" in stats["event_types"]
        assert stats["unique_sessions"] == 1
        assert stats["unique_users"] == 1

    def test_get_statistics_empty(self, logger):
        """Test getting statistics with no events."""
        stats = logger.get_statistics()

        assert stats["total_events"] == 0
        assert len(stats["event_types"]) == 0

    def test_export_logs(self, logger):
        """Test exporting logs."""
        logger.log_session_created("session123", "user456", "CloudNative")
        logger.log_query_submitted("session123", "user456", "Test", "CloudNative")

        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = Path(tmpdir) / "audit_export.jsonl"

            result = logger.export_logs(export_file)

            assert result is True
            assert export_file.exists()

            # Verify content
            with open(export_file) as f:
                lines = f.readlines()
            assert len(lines) == 2
