"""Session management for the Compass RAG service."""

import json
import logging
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SessionBudget:
    """Budget tracking for a session."""

    max_tool_calls: int = 20
    max_file_reads: int = 8
    tool_calls_used: int = 0
    file_reads_used: int = 0

    def has_tool_calls_remaining(self) -> bool:
        """Check if tool calls remain in budget."""
        return self.tool_calls_used < self.max_tool_calls

    def has_file_reads_remaining(self) -> bool:
        """Check if file reads remain in budget."""
        return self.file_reads_used < self.max_file_reads

    def increment_tool_calls(self, count: int = 1) -> bool:
        """Increment tool call count.

        Returns:
            True if increment was successful, False if budget exceeded
        """
        if self.tool_calls_used + count > self.max_tool_calls:
            logger.warning(
                f"Tool call budget exceeded: {self.tool_calls_used + count} > {self.max_tool_calls}"
            )
            return False

        self.tool_calls_used += count
        return True

    def increment_file_reads(self, count: int = 1) -> bool:
        """Increment file read count.

        Returns:
            True if increment was successful, False if budget exceeded
        """
        if self.file_reads_used + count > self.max_file_reads:
            logger.warning(
                f"File read budget exceeded: {self.file_reads_used + count} > {self.max_file_reads}"
            )
            return False

        self.file_reads_used += count
        return True

    def get_remaining_tool_calls(self) -> int:
        """Get remaining tool calls."""
        return max(0, self.max_tool_calls - self.tool_calls_used)

    def get_remaining_file_reads(self) -> int:
        """Get remaining file reads."""
        return max(0, self.max_file_reads - self.file_reads_used)


@dataclass
class QueryRecord:
    """Record of a query in a session."""

    query: str
    variant: str
    timestamp: str
    answer: Optional[str] = None
    tool_calls_count: int = 0
    file_reads_count: int = 0
    status: str = "pending"  # pending, completed, failed
    error: Optional[str] = None


@dataclass
class Session:
    """Session for a user's interaction with the RAG agent."""

    session_id: str
    user_id: str
    created_at: str
    last_activity: str
    variant: str = "CloudNative"
    queries: list[QueryRecord] = field(default_factory=list)
    budget: SessionBudget = field(default_factory=SessionBudget)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "variant": self.variant,
            "queries": [asdict(q) for q in self.queries],
            "budget": asdict(self.budget),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create session from dictionary."""
        budget_data = data.pop("budget", {})
        budget = SessionBudget(**budget_data)

        queries_data = data.pop("queries", [])
        queries = [QueryRecord(**q) for q in queries_data]

        return cls(
            queries=queries,
            budget=budget,
            **data,
        )


class SessionManager:
    """Manage user sessions."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        """Initialize session manager.

        Args:
            sessions_dir: Directory to store session files
        """
        self.sessions_dir = Path(sessions_dir) if sessions_dir else Path(".sessions")
        self.sessions_dir.mkdir(exist_ok=True)
        self.active_sessions: dict[str, Session] = {}

    def create_session(self, user_id: str, variant: str = "CloudNative") -> Session:
        """Create a new session.

        Args:
            user_id: User identifier
            variant: Documentation variant

        Returns:
            Created Session
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_activity=now,
            variant=variant,
        )

        self.active_sessions[session_id] = session
        logger.info(f"Created session {session_id} for user {user_id}")

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session or None if not found
        """
        return self.active_sessions.get(session_id)

    def update_session(self, session: Session) -> bool:
        """Update session activity timestamp.

        Args:
            session: Session to update

        Returns:
            True if successful
        """
        session.last_activity = datetime.utcnow().isoformat()
        self.active_sessions[session.session_id] = session
        return True

    def add_query(
        self,
        session_id: str,
        query: str,
        variant: str,
    ) -> Optional[QueryRecord]:
        """Add query to session.

        Args:
            session_id: Session identifier
            query: User query
            variant: Documentation variant

        Returns:
            QueryRecord or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return None

        record = QueryRecord(
            query=query,
            variant=variant,
            timestamp=datetime.utcnow().isoformat(),
        )

        session.queries.append(record)
        self.update_session(session)

        return record

    def update_query(
        self,
        session_id: str,
        query_index: int,
        answer: str,
        tool_calls_count: int,
        file_reads_count: int,
        status: str = "completed",
        error: Optional[str] = None,
    ) -> bool:
        """Update query with answer and metadata.

        Args:
            session_id: Session identifier
            query_index: Index of query in session
            answer: Generated answer
            tool_calls_count: Number of tool calls made
            file_reads_count: Number of file reads
            status: Query status
            error: Optional error message

        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session or query_index >= len(session.queries):
            logger.warning(f"Query not found in session {session_id}")
            return False

        query_record = session.queries[query_index]
        query_record.answer = answer
        query_record.tool_calls_count = tool_calls_count
        query_record.file_reads_count = file_reads_count
        query_record.status = status
        query_record.error = error

        self.update_session(session)
        return True

    def save_session(self, session_id: str) -> bool:
        """Save session to file.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return False

        try:
            file_path = self.sessions_dir / f"{session_id}.json"
            with open(file_path, "w") as f:
                json.dump(session.to_dict(), f, indent=2)

            logger.info(f"Saved session {session_id} to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load session from file.

        Args:
            session_id: Session identifier

        Returns:
            Loaded Session or None if not found
        """
        try:
            file_path = self.sessions_dir / f"{session_id}.json"

            if not file_path.exists():
                logger.warning(f"Session file not found: {file_path}")
                return None

            with open(file_path, "r") as f:
                data = json.load(f)

            session = Session.from_dict(data)
            self.active_sessions[session_id] = session

            logger.info(f"Loaded session {session_id}")
            return session

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

        try:
            file_path = self.sessions_dir / f"{session_id}.json"
            if file_path.exists():
                file_path.unlink()

            logger.info(f"Deleted session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    def list_sessions(self, user_id: Optional[str] = None) -> list[Session]:
        """List active sessions.

        Args:
            user_id: Optional filter by user

        Returns:
            List of active sessions
        """
        sessions = list(self.active_sessions.values())

        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]

        return sessions

    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Remove expired sessions.

        Args:
            max_age_hours: Maximum age of session in hours

        Returns:
            Number of sessions deleted
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired = []

        for session_id, session in list(self.active_sessions.items()):
            try:
                last_activity = datetime.fromisoformat(session.last_activity)
                if last_activity < cutoff_time:
                    expired.append(session_id)
            except (ValueError, TypeError):
                expired.append(session_id)

        for session_id in expired:
            self.delete_session(session_id)

        logger.info(f"Cleaned up {len(expired)} expired sessions")
        return len(expired)

    def get_session_stats(self, session_id: str) -> Optional[dict]:
        """Get statistics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Stats dict or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None

        completed_queries = [q for q in session.queries if q.status == "completed"]
        failed_queries = [q for q in session.queries if q.status == "failed"]

        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "variant": session.variant,
            "total_queries": len(session.queries),
            "completed_queries": len(completed_queries),
            "failed_queries": len(failed_queries),
            "total_tool_calls": sum(q.tool_calls_count for q in completed_queries),
            "total_file_reads": sum(q.file_reads_count for q in completed_queries),
            "budget": asdict(session.budget),
        }
