"""Tests for API gateway."""

import pytest

from compass.api.gateway import (
    User,
    RateLimitConfig,
    RateLimiter,
    AuthenticationManager,
)


class TestUser:
    """Test User dataclass."""

    def test_create_user(self):
        """Test creating a user."""
        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user", "admin"],
        )

        assert user.user_id == "user123"
        assert user.email == "user@example.com"
        assert "admin" in user.roles

    def test_user_default_variant(self):
        """Test user default variant."""
        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user"],
        )

        assert user.variant == "CloudNative"


class TestRateLimitConfig:
    """Test RateLimitConfig."""

    def test_default_config(self):
        """Test default rate limit config."""
        config = RateLimitConfig()

        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000

    def test_custom_config(self):
        """Test custom rate limit config."""
        config = RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=500,
        )

        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 500


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_rate_limiter_initialization(self):
        """Test initializing rate limiter."""
        config = RateLimitConfig()
        limiter = RateLimiter(config)

        assert limiter.config.requests_per_minute == 60

    def test_allow_request_under_limit(self):
        """Test allowing request under limit."""
        config = RateLimitConfig(requests_per_minute=10)
        limiter = RateLimiter(config)

        result = limiter.is_allowed("user123")

        assert result is True

    def test_deny_request_over_minute_limit(self):
        """Test denying request over per-minute limit."""
        config = RateLimitConfig(requests_per_minute=2)
        limiter = RateLimiter(config)

        # Use up limit
        limiter.is_allowed("user123")
        limiter.is_allowed("user123")

        # Next request should be denied
        result = limiter.is_allowed("user123")

        assert result is False

    def test_multiple_users_independent_limits(self):
        """Test multiple users have independent limits."""
        config = RateLimitConfig(requests_per_minute=2)
        limiter = RateLimiter(config)

        limiter.is_allowed("user1")
        limiter.is_allowed("user1")

        # user2 should still be able to make requests
        result = limiter.is_allowed("user2")

        assert result is True

    def test_get_remaining_requests_new_user(self):
        """Test getting remaining requests for new user."""
        config = RateLimitConfig(requests_per_minute=60)
        limiter = RateLimiter(config)

        remaining = limiter.get_remaining_requests("user123")

        assert remaining["remaining_per_minute"] == 60

    def test_get_remaining_requests_after_usage(self):
        """Test remaining requests after usage."""
        config = RateLimitConfig(requests_per_minute=10)
        limiter = RateLimiter(config)

        limiter.is_allowed("user123")
        limiter.is_allowed("user123")
        limiter.is_allowed("user123")

        remaining = limiter.get_remaining_requests("user123")

        assert remaining["remaining_per_minute"] == 7


class TestAuthenticationManager:
    """Test AuthenticationManager class."""

    def test_manager_initialization(self):
        """Test initializing authentication manager."""
        manager = AuthenticationManager()

        assert len(manager.users) == 0
        assert len(manager.tokens) == 0

    def test_register_user(self):
        """Test registering a user."""
        manager = AuthenticationManager()

        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user"],
        )

        result = manager.register_user(user)

        assert result is True
        assert "user123" in manager.users

    def test_register_duplicate_user(self):
        """Test registering duplicate user."""
        manager = AuthenticationManager()

        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user"],
        )

        manager.register_user(user)
        result = manager.register_user(user)

        assert result is False

    def test_create_token(self):
        """Test creating authentication token."""
        manager = AuthenticationManager()

        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user"],
        )

        token = manager.create_token(user)

        assert token is not None
        assert token in manager.tokens

    def test_authenticate_valid_token(self):
        """Test authenticating with valid token."""
        manager = AuthenticationManager()

        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user"],
        )

        token = manager.create_token(user)
        authenticated_user = manager.authenticate_token(token)

        assert authenticated_user is not None
        assert authenticated_user.user_id == "user123"

    def test_authenticate_invalid_token(self):
        """Test authenticating with invalid token."""
        manager = AuthenticationManager()

        user = manager.authenticate_token("invalid_token")

        assert user is None

    def test_revoke_token(self):
        """Test revoking token."""
        manager = AuthenticationManager()

        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user"],
        )

        token = manager.create_token(user)

        result = manager.revoke_token(token)

        assert result is True
        assert manager.authenticate_token(token) is None

    def test_revoke_nonexistent_token(self):
        """Test revoking non-existent token."""
        manager = AuthenticationManager()

        result = manager.revoke_token("nonexistent")

        assert result is False

    def test_get_user(self):
        """Test getting user by ID."""
        manager = AuthenticationManager()

        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user"],
        )

        manager.register_user(user)

        retrieved = manager.get_user("user123")

        assert retrieved is not None
        assert retrieved.email == "user@example.com"

    def test_get_nonexistent_user(self):
        """Test getting non-existent user."""
        manager = AuthenticationManager()

        user = manager.get_user("nonexistent")

        assert user is None

    def test_token_expiry(self):
        """Test token expiry (basic check)."""
        manager = AuthenticationManager()

        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user"],
        )

        # Create token with 0 hour expiry (would expire immediately in production)
        token = manager.create_token(user, expires_in_hours=0)

        # Token should still be valid for a moment (depends on timing)
        # This is a basic test
        assert token in manager.tokens


class TestRolePermissions:
    """Test role-based permissions."""

    def test_user_with_multiple_roles(self):
        """Test user with multiple roles."""
        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user", "admin", "moderator"],
        )

        assert "admin" in user.roles
        assert "user" in user.roles
        assert len(user.roles) == 3

    def test_user_with_single_role(self):
        """Test user with single role."""
        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user"],
        )

        assert "user" in user.roles
        assert len(user.roles) == 1


class TestAuthenticationFlow:
    """Test complete authentication flow."""

    def test_full_auth_flow(self):
        """Test full authentication flow."""
        manager = AuthenticationManager()

        # Register user
        user = User(
            user_id="user123",
            email="user@example.com",
            roles=["user"],
        )
        manager.register_user(user)

        # Create token
        token = manager.create_token(user)

        # Authenticate with token
        authenticated = manager.authenticate_token(token)

        assert authenticated is not None
        assert authenticated.user_id == "user123"

        # Revoke token
        manager.revoke_token(token)

        # Token should no longer authenticate
        authenticated = manager.authenticate_token(token)

        assert authenticated is None


class TestAPIGatewayWithOIDC:
    """Test API Gateway with OIDC integration."""

    def test_gateway_initialization_without_oidc(self):
        """Test initializing gateway without OIDC."""
        from fastapi import FastAPI

        from compass.api.gateway import APIGateway

        app = FastAPI()
        gateway = APIGateway(app)

        assert gateway.oidc_manager is not None
        assert len(gateway.oidc_manager.providers) == 0

    def test_gateway_initialization_with_oidc(self):
        """Test initializing gateway with OIDC."""
        from fastapi import FastAPI

        from compass.api.gateway import APIGateway
        from compass.api.oidc import OIDCConfig

        app = FastAPI()
        oidc_configs = {
            "azure": OIDCConfig(
                provider_name="azure",
                client_id="test_client",
                client_secret="test_secret",
                discovery_url="https://example.com/.well-known/openid-configuration",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        }

        gateway = APIGateway(app, oidc_configs)

        assert len(gateway.oidc_manager.providers) == 1
        assert gateway.oidc_manager.get_provider("azure") is not None
