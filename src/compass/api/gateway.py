"""API Gateway with authentication and rate limiting."""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from urllib.parse import quote

from fastapi import FastAPI, Request, HTTPException, Depends, APIRouter
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from compass.api.oidc import OIDCConfig, OIDCManager, OIDCUserInfo

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    """Login request body."""

    email: str
    password: str


@dataclass
class User:
    """Authenticated user."""

    user_id: str
    email: str
    roles: list[str]
    variant: str = "CloudNative"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10


class RateLimiter:
    """Rate limiter for API requests."""

    def __init__(self, config: RateLimitConfig):
        """Initialize rate limiter.

        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.requests = {}  # user_id -> list of timestamps

    def is_allowed(self, user_id: str) -> bool:
        """Check if request is allowed.

        Args:
            user_id: User identifier

        Returns:
            True if request is allowed
        """
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        # Initialize user if not seen
        if user_id not in self.requests:
            self.requests[user_id] = []

        # Clean old requests
        self.requests[user_id] = [
            ts for ts in self.requests[user_id] if ts > hour_ago
        ]

        # Check limits
        recent_minute = len([ts for ts in self.requests[user_id] if ts > minute_ago])
        if recent_minute >= self.config.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {user_id} (per minute)")
            return False

        total_hour = len(self.requests[user_id])
        if total_hour >= self.config.requests_per_hour:
            logger.warning(f"Rate limit exceeded for {user_id} (per hour)")
            return False

        # Record request
        self.requests[user_id].append(now)
        return True

    def get_remaining_requests(self, user_id: str) -> dict:
        """Get remaining requests for user.

        Args:
            user_id: User identifier

        Returns:
            Dict with remaining request counts
        """
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        if user_id not in self.requests:
            return {
                "remaining_per_minute": self.config.requests_per_minute,
                "remaining_per_hour": self.config.requests_per_hour,
            }

        recent_minute = len([ts for ts in self.requests[user_id] if ts > minute_ago])
        total_hour = len([ts for ts in self.requests[user_id] if ts > hour_ago])

        return {
            "remaining_per_minute": max(0, self.config.requests_per_minute - recent_minute),
            "remaining_per_hour": max(0, self.config.requests_per_hour - total_hour),
        }


class AuthenticationManager:
    """Manage user authentication."""

    def __init__(self):
        """Initialize authentication manager."""
        self.users = {}  # user_id -> User
        self.tokens = {}  # token -> user_id
        self.token_expiry = {}  # token -> expiry_time

    def authenticate_token(self, token: str) -> Optional[User]:
        """Authenticate user by token.

        Args:
            token: Authentication token

        Returns:
            User if authenticated, None otherwise
        """
        # Check if token exists
        if token not in self.tokens:
            logger.warning(f"Invalid token")
            return None

        # Check expiry
        expiry = self.token_expiry.get(token)
        if expiry and datetime.utcnow() > expiry:
            logger.warning(f"Token expired")
            self.revoke_token(token)
            return None

        user_id = self.tokens[token]
        return self.users.get(user_id)

    def create_token(self, user: User, expires_in_hours: int = 24) -> str:
        """Create authentication token for user.

        Args:
            user: User to authenticate
            expires_in_hours: Token expiry time

        Returns:
            Authentication token
        """
        import uuid

        token = str(uuid.uuid4())
        self.tokens[token] = user.user_id
        self.token_expiry[token] = datetime.utcnow() + timedelta(hours=expires_in_hours)
        self.users[user.user_id] = user

        logger.info(f"Created token for user {user.user_id}")
        return token

    def revoke_token(self, token: str) -> bool:
        """Revoke authentication token.

        Args:
            token: Token to revoke

        Returns:
            True if successful
        """
        if token in self.tokens:
            user_id = self.tokens.pop(token)
            self.token_expiry.pop(token, None)
            logger.info(f"Revoked token for user {user_id}")
            return True

        return False

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User or None
        """
        return self.users.get(user_id)

    def register_user(self, user: User) -> bool:
        """Register new user.

        Args:
            user: User to register

        Returns:
            True if successful
        """
        if user.user_id in self.users:
            logger.warning(f"User already exists: {user.user_id}")
            return False

        self.users[user.user_id] = user
        logger.info(f"Registered user {user.user_id}")
        return True


class APIGateway:
    """API Gateway for request routing and security."""

    def __init__(self, app: FastAPI, oidc_configs: Optional[dict[str, OIDCConfig]] = None):
        """Initialize API gateway.

        Args:
            app: FastAPI application
            oidc_configs: Optional OIDC provider configurations
        """
        self.app = app
        self.auth_manager = AuthenticationManager()
        self.rate_limiter = RateLimiter(RateLimitConfig())
        self.security = HTTPBearer()

        # Initialize OIDC if provided
        self.oidc_manager = OIDCManager(oidc_configs or {})
        self._oidc_initialized = False

        # Register middleware
        self._register_middleware()

    def _register_middleware(self) -> None:
        """Register gateway middleware."""

        @self.app.middleware("http")
        async def gateway_middleware(request: Request, call_next):
            """Main gateway middleware."""
            # Skip auth for health check, login, OIDC, and docs
            skip_auth_paths = ["/health", "/login", "/api/v1/login", "/docs", "/openapi.json", "/api/v1/swagger.json"]
            skip_auth_prefixes = ["/auth", "/auth/", "/api/v1/auth"]

            # Check if path should skip auth
            if request.url.path in skip_auth_paths:
                return await call_next(request)

            # Check if path starts with skip prefix
            for prefix in skip_auth_prefixes:
                if request.url.path.startswith(prefix):
                    return await call_next(request)

            # For /api/v1/query and other non-auth endpoints, check if token is provided
            # If no token, skip auth for demo mode
            auth_header = request.headers.get("Authorization", "")
            if not auth_header:
                # Allow unauthenticated access to demo endpoints in development
                if request.url.path.startswith("/api/v1/query") or request.url.path.startswith("/api/v1/session"):
                    # Add a demo user for development
                    class DemoUser:
                        user_id = "demo"
                        email = "demo@example.com"
                        roles = ["user"]
                        variant = "CloudNative"
                    request.state.user = DemoUser()
                    return await call_next(request)
                else:
                    raise HTTPException(status_code=401, detail="Missing authorization token")

            # Verify token format
            if not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Invalid authorization header")

            token = auth_header.replace("Bearer ", "")

            # Authenticate
            user = self.auth_manager.authenticate_token(token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid or expired token")

            # Extract token
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing authorization token")

            token = auth_header.replace("Bearer ", "")

            # Authenticate
            user = self.auth_manager.authenticate_token(token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid or expired token")

            # Rate limiting
            if not self.rate_limiter.is_allowed(user.user_id):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            # Add user to request state
            request.state.user = user

            # Add rate limit headers
            remaining = self.rate_limiter.get_remaining_requests(user.user_id)

            response = await call_next(request)
            response.headers["X-RateLimit-Remaining-Minute"] = str(
                remaining["remaining_per_minute"]
            )
            response.headers["X-RateLimit-Remaining-Hour"] = str(
                remaining["remaining_per_hour"]
            )

            return response

    def get_current_user(self, request: Request) -> User:
        """Get current authenticated user.

        Args:
            request: FastAPI request

        Returns:
            Current user
        """
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user

    def require_roles(self, required_roles: list[str]) -> Callable:
        """Require specific roles for endpoint.

        Args:
            required_roles: List of required roles

        Returns:
            Dependency function
        """

        def role_checker(request: Request) -> User:
            user = self.get_current_user(request)

            # Check roles
            if not any(role in user.roles for role in required_roles):
                logger.warning(
                    f"User {user.user_id} lacks required roles: {required_roles}"
                )
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            return user

        return role_checker

    async def initialize_oidc(self) -> None:
        """Initialize OIDC provider connections."""
        if not self._oidc_initialized and self.oidc_manager.providers:
            await self.oidc_manager.initialize()
            self._oidc_initialized = True

    def register_routes(self) -> None:
        """Register gateway routes."""
        router = APIRouter(prefix="/api/v1", tags=["auth"])

        @router.get("/auth/{provider}")
        async def start_oidc_auth(provider: str):
            """Start OIDC authentication flow.

            Args:
                provider: OIDC provider name (e.g., 'azure', 'okta')

            Returns:
                Redirect to provider authorization endpoint
            """
            oidc_provider = self.oidc_manager.get_provider(provider)
            if not oidc_provider:
                raise HTTPException(
                    status_code=400, detail=f"Unknown OIDC provider: {provider}"
                )

            # Generate CSRF state
            state = str(uuid.uuid4())
            if not self.oidc_manager.create_auth_state(provider, state):
                raise HTTPException(status_code=500, detail="Failed to create auth state")

            # Get authorization URL
            auth_url = oidc_provider.get_authorization_url(state)

            return RedirectResponse(url=auth_url)

        @router.get("/auth/callback")
        async def oidc_callback(code: str, state: str):
            """Handle OIDC provider callback.

            Args:
                code: Authorization code from provider
                state: CSRF state for verification

            Returns:
                Redirect to frontend with token or error
            """
            # Verify state
            provider_name = self.oidc_manager.verify_auth_state(state)
            if not provider_name:
                raise HTTPException(status_code=400, detail="Invalid or expired state")

            # Handle callback
            user_info = await self.oidc_manager.handle_callback(provider_name, code)
            if not user_info:
                raise HTTPException(status_code=400, detail="Failed to authenticate")

            # Create user in auth manager
            from compass.api.gateway import User

            user = User(
                user_id=user_info.user_id,
                email=user_info.email,
                roles=user_info.roles,
                variant=user_info.variant,
            )

            self.auth_manager.register_user(user)
            token = self.auth_manager.create_token(user)

            # Redirect to frontend with token
            frontend_url = f"/auth/success?token={quote(token)}&user_id={quote(user.user_id)}"
            return RedirectResponse(url=frontend_url)

        @router.get("/auth/success")
        async def auth_success(token: str, user_id: str):
            """Auth success page (frontend would handle token storage).

            Args:
                token: Authentication token
                user_id: User ID

            Returns:
                Success response with token info
            """
            return {
                "status": "success",
                "access_token": token,
                "token_type": "bearer",
                "user_id": user_id,
            }

        @router.post("/login")
        async def login(request: LoginRequest) -> dict:
            """Login endpoint."""
            # In production, validate credentials against auth provider
            # For now, create test user
            user = User(
                user_id=request.email.split("@")[0],
                email=request.email,
                roles=["user"],
            )

            token = self.auth_manager.create_token(user)

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "roles": user.roles,
                },
            }

        @router.post("/logout")
        async def logout(request: Request) -> dict:
            """Logout endpoint."""
            user = self.get_current_user(request)

            auth_header = request.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "")

            self.auth_manager.revoke_token(token)

            logger.info(f"User {user.user_id} logged out")

            return {"message": "Logged out successfully"}

        @router.get("/user/profile")
        async def get_profile(request: Request) -> dict:
            """Get user profile."""
            user = self.get_current_user(request)

            return {
                "user_id": user.user_id,
                "email": user.email,
                "roles": user.roles,
                "variant": user.variant,
            }

        @router.get("/user/rate-limit")
        async def get_rate_limit(request: Request) -> dict:
            """Get rate limit status."""
            user = self.get_current_user(request)

            remaining = self.rate_limiter.get_remaining_requests(user.user_id)

            return {
                "user_id": user.user_id,
                **remaining,
            }

        # Register router with app
        self.app.include_router(router)

    def create_dependency(
        self,
        required_roles: Optional[list[str]] = None,
    ) -> Callable:
        """Create dependency for protecting endpoints.

        Args:
            required_roles: Optional list of required roles

        Returns:
            Dependency function
        """
        if required_roles:
            return self.require_roles(required_roles)
        else:
            return self.get_current_user
