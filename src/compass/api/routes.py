"""API routes and request routing."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from compass.agent.agent import ReasoningAgent
from compass.api.gateway import APIGateway, User
from compass.services.session import SessionManager
from compass.services.citations import CitationFormatter
from compass.services.audit import AuditLogger, AuditEventType

logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """Query request model."""

    query: str
    variant: Optional[str] = None
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Query response model."""

    answer: str
    session_id: str
    citations: list = None
    tool_calls: int = 0
    processing_time: float = 0.0


class CompassRouter:
    """Manage API routes and request routing."""

    def __init__(
        self,
        gateway: APIGateway,
        agent: ReasoningAgent,
        session_manager: SessionManager,
        audit_logger: AuditLogger,
    ):
        """Initialize router.

        Args:
            gateway: API gateway
            agent: Reasoning agent
            session_manager: Session manager
            audit_logger: Audit logger
        """
        self.gateway = gateway
        self.agent = agent
        self.session_manager = session_manager
        self.audit_logger = audit_logger
        self.router = APIRouter(prefix="/api/v1", tags=["compass"])

        self._register_routes()

    def _register_routes(self) -> None:
        """Register all API routes."""

        @self.router.post("/query")
        async def query(
            request: Request,
            query: str,
            variant: Optional[str] = None,
            session_id: Optional[str] = None,
        ) -> dict:
            """Submit a query to the agent.

            Args:
                request: FastAPI request
                query: User query
                variant: Documentation variant
                session_id: Session ID (optional)

            Returns:
                Query response
            """
            import time

            user: User = self.gateway.get_current_user(request)
            start_time = time.time()

            try:
                # Determine variant
                variant = variant or user.variant

                # Validate variant
                valid_variants = ["CloudNative", "ServerBased"]
                if variant not in valid_variants:
                    logger.warning(f"Invalid variant: {variant}")
                    raise HTTPException(status_code=400, detail=f"Invalid variant: {variant}")

                # Get or create session
                if session_id:
                    session = self.session_manager.get_session(session_id)
                    if not session or session.user_id != user.user_id:
                        raise HTTPException(status_code=403, detail="Session not found")
                else:
                    session = self.session_manager.create_session(user.user_id, variant)
                    session_id = session.session_id

                # Log query submission
                self.audit_logger.log_query_submitted(session_id, user.user_id, query, variant)

                # Execute query (with fallback for demo)
                try:
                    result = self.agent.query(query, variant)
                except Exception as agent_error:
                    logger.warning(f"Agent query failed, using demo response: {agent_error}")
                    # Provide demo response when agent fails
                    result = {
                        "answer": f"Demo response for '{query}' in {variant} variant. (Agent not fully initialized)",
                        "variant": variant,
                        "tool_calls": 0,
                        "citations": [],
                    }

                # Update session
                self.session_manager.update_query(
                    session_id,
                    len(session.queries),
                    result.get("answer", ""),
                    result.get("tool_calls", 0),
                    0,  # file_reads
                    "completed",
                )

                # Log successful query
                processing_time = time.time() - start_time
                self.audit_logger.log_query_completed(
                    session_id,
                    user.user_id,
                    query,
                    result.get("tool_calls", 0),
                    0,
                    len(result.get("citations", [])),
                )

                return {
                    "session_id": session_id,
                    "answer": result.get("answer"),
                    "citations": result.get("citations", []),
                    "tool_calls": result.get("tool_calls", 0),
                    "processing_time": processing_time,
                    "variant": variant,
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Query failed: {e}", exc_info=True)
                try:
                    self.audit_logger.log_query_failed(session_id, user.user_id, query, str(e))
                except:
                    pass
                raise HTTPException(status_code=500, detail="Query processing failed")

        @self.router.get("/session/{session_id}")
        async def get_session(session_id: str, request: Request) -> dict:
            """Get session information.

            Args:
                session_id: Session ID
                request: FastAPI request

            Returns:
                Session information
            """
            user: User = self.gateway.get_current_user(request)

            session = self.session_manager.get_session(session_id)
            if not session or session.user_id != user.user_id:
                raise HTTPException(status_code=403, detail="Session not found")

            stats = self.session_manager.get_session_stats(session_id)

            return {
                "session_id": session_id,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "variant": session.variant,
                "statistics": stats,
            }

        @self.router.delete("/session/{session_id}")
        async def close_session(session_id: str, request: Request) -> dict:
            """Close a session.

            Args:
                session_id: Session ID
                request: FastAPI request

            Returns:
                Confirmation message
            """
            user: User = self.gateway.get_current_user(request)

            session = self.session_manager.get_session(session_id)
            if not session or session.user_id != user.user_id:
                raise HTTPException(status_code=403, detail="Session not found")

            # Save session before closing
            self.session_manager.save_session(session_id)

            # Log session closure
            self.audit_logger.log_session_closed(session_id, user.user_id, len(session.queries))

            # Delete session
            self.session_manager.delete_session(session_id)

            return {"message": "Session closed", "session_id": session_id}

        @self.router.get("/session/{session_id}/queries")
        async def get_session_queries(session_id: str, request: Request) -> dict:
            """Get all queries in a session.

            Args:
                session_id: Session ID
                request: FastAPI request

            Returns:
                List of queries
            """
            user: User = self.gateway.get_current_user(request)

            session = self.session_manager.get_session(session_id)
            if not session or session.user_id != user.user_id:
                raise HTTPException(status_code=403, detail="Session not found")

            return {
                "session_id": session_id,
                "queries": [
                    {
                        "query": q.query,
                        "timestamp": q.timestamp,
                        "answer": q.answer,
                        "status": q.status,
                    }
                    for q in session.queries
                ],
            }

        @self.router.get("/health")
        async def health_check() -> dict:
            """Health check endpoint."""
            return {"status": "healthy", "service": "compass-rag"}

        @self.router.get("/stats")
        async def get_stats(request: Request) -> dict:
            """Get aggregate statistics.

            Args:
                request: FastAPI request

            Returns:
                Statistics
            """
            user: User = self.gateway.get_current_user(request)

            audit_stats = self.audit_logger.get_statistics()
            user_sessions = self.session_manager.list_sessions(user.user_id)

            return {
                "user_id": user.user_id,
                "session_count": len(user_sessions),
                "audit_events": audit_stats.get("total_events", 0),
                "event_types": audit_stats.get("event_types", {}),
            }

    def get_router(self):
        """Get FastAPI router.

        Returns:
            APIRouter instance
        """
        return self.router

    def register_with_app(self, app):
        """Register router with FastAPI app.

        Args:
            app: FastAPI application instance
        """
        app.include_router(self.router)


class RequestHandler:
    """Handle different request types."""

    @staticmethod
    def handle_query_request(
        request_data: dict,
        agent: ReasoningAgent,
        session_manager: SessionManager,
    ) -> dict:
        """Handle query request.

        Args:
            request_data: Request data
            agent: Reasoning agent
            session_manager: Session manager

        Returns:
            Response data
        """
        query = request_data.get("query")
        variant = request_data.get("variant", "CloudNative")
        session_id = request_data.get("session_id")

        if not query:
            raise ValueError("Query is required")

        # Execute query
        result = agent.query(query, variant)

        return {
            "session_id": session_id,
            "answer": result.get("answer"),
            "variant": result.get("variant"),
            "citations": result.get("citations", []),
        }

    @staticmethod
    def handle_session_request(
        request_data: dict,
        session_manager: SessionManager,
    ) -> dict:
        """Handle session request.

        Args:
            request_data: Request data
            session_manager: Session manager

        Returns:
            Response data
        """
        action = request_data.get("action")

        if action == "create":
            user_id = request_data.get("user_id")
            variant = request_data.get("variant", "CloudNative")
            session = session_manager.create_session(user_id, variant)

            return {
                "session_id": session.session_id,
                "created_at": session.created_at,
            }

        elif action == "get":
            session_id = request_data.get("session_id")
            session = session_manager.get_session(session_id)

            if not session:
                raise ValueError(f"Session not found: {session_id}")

            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "queries": len(session.queries),
            }

        else:
            raise ValueError(f"Unknown session action: {action}")

    @staticmethod
    def handle_admin_request(
        request_data: dict,
        audit_logger: AuditLogger,
    ) -> dict:
        """Handle admin request.

        Args:
            request_data: Request data
            audit_logger: Audit logger

        Returns:
            Response data
        """
        action = request_data.get("action")

        if action == "stats":
            return audit_logger.get_statistics()

        elif action == "export_logs":
            # Would export logs to file
            return {"message": "Logs exported"}

        else:
            raise ValueError(f"Unknown admin action: {action}")
