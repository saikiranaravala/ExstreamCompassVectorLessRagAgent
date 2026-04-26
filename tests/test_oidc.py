"""Tests for OIDC authentication."""

import pytest
from datetime import datetime, timedelta

from compass.api.oidc import OIDCConfig, OIDCUserInfo, OIDCProvider, OIDCManager


class TestOIDCConfig:
    """Test OIDCConfig dataclass."""

    def test_create_config(self):
        """Test creating OIDC config."""
        config = OIDCConfig(
            provider_name="azure",
            client_id="test_client",
            client_secret="test_secret",
            discovery_url="https://example.com/.well-known/openid-configuration",
            redirect_uri="http://localhost:8000/auth/callback",
        )

        assert config.provider_name == "azure"
        assert config.client_id == "test_client"
        assert len(config.scopes) == 3
        assert "openid" in config.scopes

    def test_custom_scopes(self):
        """Test OIDC config with custom scopes."""
        config = OIDCConfig(
            provider_name="okta",
            client_id="test_client",
            client_secret="test_secret",
            discovery_url="https://example.com/.well-known/openid-configuration",
            redirect_uri="http://localhost:8000/auth/callback",
            scopes=["openid", "profile", "email", "offline_access"],
        )

        assert len(config.scopes) == 4
        assert "offline_access" in config.scopes


class TestOIDCUserInfo:
    """Test OIDCUserInfo dataclass."""

    def test_create_user_info(self):
        """Test creating user info."""
        user_info = OIDCUserInfo(
            user_id="user123",
            email="user@example.com",
            name="Test User",
            roles=["user"],
        )

        assert user_info.user_id == "user123"
        assert user_info.email == "user@example.com"
        assert user_info.variant == "CloudNative"

    def test_user_info_custom_variant(self):
        """Test user info with custom variant."""
        user_info = OIDCUserInfo(
            user_id="user123",
            email="user@example.com",
            name="Test User",
            roles=["user", "admin"],
            variant="ServerBased",
        )

        assert user_info.variant == "ServerBased"
        assert len(user_info.roles) == 2


class TestOIDCManager:
    """Test OIDCManager class."""

    def test_manager_initialization(self):
        """Test initializing OIDC manager."""
        configs = {
            "azure": OIDCConfig(
                provider_name="azure",
                client_id="test_client",
                client_secret="test_secret",
                discovery_url="https://example.com/.well-known/openid-configuration",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        }

        manager = OIDCManager(configs)

        assert len(manager.providers) == 1
        assert "azure" in manager.providers

    def test_get_provider(self):
        """Test getting OIDC provider."""
        configs = {
            "azure": OIDCConfig(
                provider_name="azure",
                client_id="test_client",
                client_secret="test_secret",
                discovery_url="https://example.com/.well-known/openid-configuration",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        }

        manager = OIDCManager(configs)
        provider = manager.get_provider("azure")

        assert provider is not None
        assert provider.config.provider_name == "azure"

    def test_get_nonexistent_provider(self):
        """Test getting non-existent provider."""
        manager = OIDCManager({})

        provider = manager.get_provider("azure")

        assert provider is None

    def test_create_auth_state(self):
        """Test creating auth state."""
        configs = {
            "azure": OIDCConfig(
                provider_name="azure",
                client_id="test_client",
                client_secret="test_secret",
                discovery_url="https://example.com/.well-known/openid-configuration",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        }

        manager = OIDCManager(configs)
        state = "test_state_123"

        result = manager.create_auth_state("azure", state)

        assert result is True
        assert state in manager.auth_states

    def test_create_auth_state_invalid_provider(self):
        """Test creating auth state with invalid provider."""
        manager = OIDCManager({})

        result = manager.create_auth_state("invalid", "state")

        assert result is False

    def test_verify_auth_state(self):
        """Test verifying auth state."""
        configs = {
            "azure": OIDCConfig(
                provider_name="azure",
                client_id="test_client",
                client_secret="test_secret",
                discovery_url="https://example.com/.well-known/openid-configuration",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        }

        manager = OIDCManager(configs)
        state = "test_state_123"

        manager.create_auth_state("azure", state)
        provider_name = manager.verify_auth_state(state)

        assert provider_name == "azure"
        assert state not in manager.auth_states

    def test_verify_invalid_state(self):
        """Test verifying invalid state."""
        manager = OIDCManager({})

        provider_name = manager.verify_auth_state("invalid_state")

        assert provider_name is None

    def test_verify_expired_state(self):
        """Test verifying expired state."""
        configs = {
            "azure": OIDCConfig(
                provider_name="azure",
                client_id="test_client",
                client_secret="test_secret",
                discovery_url="https://example.com/.well-known/openid-configuration",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        }

        manager = OIDCManager(configs)
        state = "test_state_123"

        manager.create_auth_state("azure", state)

        # Manually set timestamp to 15 minutes ago
        provider_name, _ = manager.auth_states[state]
        manager.auth_states[state] = (provider_name, datetime.utcnow() - timedelta(minutes=15))

        provider_name = manager.verify_auth_state(state)

        assert provider_name is None
        assert state not in manager.auth_states

    def test_multiple_providers(self):
        """Test manager with multiple providers."""
        configs = {
            "azure": OIDCConfig(
                provider_name="azure",
                client_id="azure_client",
                client_secret="azure_secret",
                discovery_url="https://azure.com/.well-known/openid-configuration",
                redirect_uri="http://localhost:8000/auth/callback",
            ),
            "okta": OIDCConfig(
                provider_name="okta",
                client_id="okta_client",
                client_secret="okta_secret",
                discovery_url="https://okta.com/.well-known/openid-configuration",
                redirect_uri="http://localhost:8000/auth/callback",
            ),
        }

        manager = OIDCManager(configs)

        assert len(manager.providers) == 2
        assert manager.get_provider("azure") is not None
        assert manager.get_provider("okta") is not None
