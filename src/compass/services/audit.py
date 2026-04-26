"""Audit logging for the Compass RAG service."""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""

    SESSION_CREATED = "session_created"
    SESSION_CLOSED = "session_closed"
    QUERY_SUBMITTED = "query_submitted"
    QUERY_COMPLETED = "query_completed"
    QUERY_FAILED = "query_failed"
    TOOL_CALLED = "tool_called"
    TOOL_SUCCEEDED = "tool_succeeded"
    TOOL_FAILED = "tool_failed"
    BUDGET_EXCEEDED = "budget_exceeded"
    VARIANT_VIOLATION = "variant_violation"
    CITATION_VERIFIED = "citation_verified"
    CITATION_FAILED = "citation_failed"
    ERROR = "error"
    ACCESS_DENIED = "access_denied"


@dataclass
class AuditEvent:
    """An audit event record."""

    timestamp: str
    event_type: str
    session_id: str
    user_id: str
    details: dict
    severity: str = "INFO"  # INFO, WARNING, ERROR

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "details": self.details,
            "severity": self.severity,
        }

    def to_json_line(self) -> str:
        """Convert to JSON line for logging."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Audit logger for operations."""

    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize audit logger.

        Args:
            log_dir: Directory to store audit logs
        """
        self.log_dir = Path(log_dir) if log_dir else Path(".audit_logs")
        self.log_dir.mkdir(exist_ok=True)
        self.events: list[AuditEvent] = []

    def _get_log_file(self) -> Path:
        """Get path to current day's log file."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_dir / f"audit-{date_str}.jsonl"

    def log_event(
        self,
        event_type: AuditEventType,
        session_id: str,
        user_id: str,
        details: dict,
        severity: str = "INFO",
    ) -> AuditEvent:
        """Log an audit event.

        Args:
            event_type: Type of event
            session_id: Session identifier
            user_id: User identifier
            details: Event details
            severity: Log level

        Returns:
            Created AuditEvent
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type.value if isinstance(event_type, AuditEventType) else str(event_type),
            session_id=session_id,
            user_id=user_id,
            details=details,
            severity=severity,
        )

        self.events.append(event)

        # Write to file immediately
        self._write_event_to_file(event)

        # Log to standard logger
        log_func = {
            "INFO": logger.info,
            "WARNING": logger.warning,
            "ERROR": logger.error,
        }.get(severity, logger.info)

        log_func(f"{event.event_type}: {user_id} - {details}")

        return event

    def _write_event_to_file(self, event: AuditEvent) -> bool:
        """Write event to audit log file.

        Args:
            event: Event to write

        Returns:
            True if successful
        """
        try:
            log_file = self._get_log_file()

            with open(log_file, "a") as f:
                f.write(event.to_json_line() + "\n")

            return True

        except Exception as e:
            logger.error(f"Failed to write audit event: {e}")
            return False

    def log_session_created(
        self,
        session_id: str,
        user_id: str,
        variant: str,
    ) -> AuditEvent:
        """Log session creation."""
        return self.log_event(
            AuditEventType.SESSION_CREATED,
            session_id,
            user_id,
            {"variant": variant},
        )

    def log_session_closed(
        self,
        session_id: str,
        user_id: str,
        query_count: int,
    ) -> AuditEvent:
        """Log session closure."""
        return self.log_event(
            AuditEventType.SESSION_CLOSED,
            session_id,
            user_id,
            {"query_count": query_count},
        )

    def log_query_submitted(
        self,
        session_id: str,
        user_id: str,
        query: str,
        variant: str,
    ) -> AuditEvent:
        """Log query submission."""
        return self.log_event(
            AuditEventType.QUERY_SUBMITTED,
            session_id,
            user_id,
            {
                "query": query[:200],  # Truncate long queries
                "variant": variant,
            },
        )

    def log_query_completed(
        self,
        session_id: str,
        user_id: str,
        query: str,
        tool_calls_count: int,
        file_reads_count: int,
        citations_count: int,
    ) -> AuditEvent:
        """Log successful query completion."""
        return self.log_event(
            AuditEventType.QUERY_COMPLETED,
            session_id,
            user_id,
            {
                "query": query[:200],
                "tool_calls": tool_calls_count,
                "file_reads": file_reads_count,
                "citations": citations_count,
            },
        )

    def log_query_failed(
        self,
        session_id: str,
        user_id: str,
        query: str,
        error: str,
    ) -> AuditEvent:
        """Log query failure."""
        return self.log_event(
            AuditEventType.QUERY_FAILED,
            session_id,
            user_id,
            {
                "query": query[:200],
                "error": error[:200],
            },
            severity="WARNING",
        )

    def log_tool_called(
        self,
        session_id: str,
        user_id: str,
        tool_name: str,
        tool_args: dict,
    ) -> AuditEvent:
        """Log tool call."""
        return self.log_event(
            AuditEventType.TOOL_CALLED,
            session_id,
            user_id,
            {
                "tool": tool_name,
                "args_keys": list(tool_args.keys()),
            },
        )

    def log_tool_succeeded(
        self,
        session_id: str,
        user_id: str,
        tool_name: str,
        result_summary: str,
    ) -> AuditEvent:
        """Log successful tool execution."""
        return self.log_event(
            AuditEventType.TOOL_SUCCEEDED,
            session_id,
            user_id,
            {
                "tool": tool_name,
                "result_summary": result_summary[:100],
            },
        )

    def log_tool_failed(
        self,
        session_id: str,
        user_id: str,
        tool_name: str,
        error: str,
    ) -> AuditEvent:
        """Log tool execution failure."""
        return self.log_event(
            AuditEventType.TOOL_FAILED,
            session_id,
            user_id,
            {
                "tool": tool_name,
                "error": error[:200],
            },
            severity="WARNING",
        )

    def log_budget_exceeded(
        self,
        session_id: str,
        user_id: str,
        budget_type: str,
        current: int,
        limit: int,
    ) -> AuditEvent:
        """Log budget exceeded event."""
        return self.log_event(
            AuditEventType.BUDGET_EXCEEDED,
            session_id,
            user_id,
            {
                "budget_type": budget_type,
                "current": current,
                "limit": limit,
            },
            severity="WARNING",
        )

    def log_variant_violation(
        self,
        session_id: str,
        user_id: str,
        attempted_variant: str,
        allowed_variant: str,
        resource: str,
    ) -> AuditEvent:
        """Log variant isolation violation."""
        return self.log_event(
            AuditEventType.VARIANT_VIOLATION,
            session_id,
            user_id,
            {
                "attempted_variant": attempted_variant,
                "allowed_variant": allowed_variant,
                "resource": resource[:200],
            },
            severity="WARNING",
        )

    def log_access_denied(
        self,
        session_id: str,
        user_id: str,
        reason: str,
    ) -> AuditEvent:
        """Log access denial."""
        return self.log_event(
            AuditEventType.ACCESS_DENIED,
            session_id,
            user_id,
            {"reason": reason},
            severity="WARNING",
        )

    def log_error(
        self,
        session_id: str,
        user_id: str,
        error_message: str,
        error_type: Optional[str] = None,
    ) -> AuditEvent:
        """Log error."""
        return self.log_event(
            AuditEventType.ERROR,
            session_id,
            user_id,
            {
                "error": error_message[:200],
                "error_type": error_type,
            },
            severity="ERROR",
        )

    def get_events(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> list[AuditEvent]:
        """Get audit events with optional filtering.

        Args:
            session_id: Filter by session
            user_id: Filter by user
            event_type: Filter by event type

        Returns:
            Filtered list of events
        """
        events = self.events

        if session_id:
            events = [e for e in events if e.session_id == session_id]

        if user_id:
            events = [e for e in events if e.user_id == user_id]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events

    def get_session_audit_trail(self, session_id: str) -> list[AuditEvent]:
        """Get all events for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of events for session
        """
        return self.get_events(session_id=session_id)

    def get_user_audit_trail(self, user_id: str) -> list[AuditEvent]:
        """Get all events for a user.

        Args:
            user_id: User identifier

        Returns:
            List of events for user
        """
        return self.get_events(user_id=user_id)

    def get_statistics(self) -> dict:
        """Get audit log statistics.

        Returns:
            Statistics dict
        """
        if not self.events:
            return {
                "total_events": 0,
                "event_types": {},
                "severity_counts": {},
            }

        event_types = {}
        severity_counts = {}

        for event in self.events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
            severity_counts[event.severity] = severity_counts.get(event.severity, 0) + 1

        return {
            "total_events": len(self.events),
            "event_types": event_types,
            "severity_counts": severity_counts,
            "unique_sessions": len(set(e.session_id for e in self.events)),
            "unique_users": len(set(e.user_id for e in self.events)),
        }

    def export_logs(self, output_file: Path) -> bool:
        """Export all logs to file.

        Args:
            output_file: Path to export file

        Returns:
            True if successful
        """
        try:
            with open(output_file, "w") as f:
                for event in self.events:
                    f.write(event.to_json_line() + "\n")

            logger.info(f"Exported {len(self.events)} events to {output_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to export logs: {e}")
            return False
