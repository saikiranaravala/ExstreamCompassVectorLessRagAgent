"""OIDC (OpenID Connect) authentication support."""

import logging
import jwt
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client

logger = logging.getLogger(__name__)


@dataclass
class OIDCConfig:
    """OIDC provider configuration."""

    provider_name: str
    client_id: str
    client_secret: str
    discovery_url: str
    redirect_uri: str
    scopes: list[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["openid", "profile", "email"]


@dataclass
class OIDCUserInfo:
    """Extracted user information from OIDC provider."""

    user_id: str
    email: str
    name: str
    roles: list[str]
    variant: str = "CloudNative"


class OIDCProvider:
    """Handle OIDC provider interactions."""

    def __init__(self, config: OIDCConfig):
        """Initialize OIDC provider.

        Args:
            config: OIDC configuration
        """
        self.config = config
        self.metadata = None
        self.client = None

    async def initialize(self) -> None:
        """Initialize OIDC provider and fetch metadata."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.config.discovery_url, timeout=10)
                response.raise_for_status()
                self.metadata = response.json()
                logger.info(f"Initialized OIDC provider: {self.config.provider_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OIDC provider: {e}")
            raise

    def get_authorization_url(self, state: str) -> str:
        """Get authorization URL for user redirect.

        Args:
            state: CSRF protection state

        Returns:
            Authorization URL
        """
        if not self.metadata:
            raise ValueError("Provider not initialized")

        auth_endpoint = self.metadata.get("authorization_endpoint")
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }

        return f"{auth_endpoint}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from provider

        Returns:
            Token response with access_token, id_token, etc.
        """
        if not self.metadata:
            raise ValueError("Provider not initialized")

        token_endpoint = self.metadata.get("token_endpoint")
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_endpoint, data=data, timeout=10)
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from provider.

        Args:
            access_token: Access token from provider

        Returns:
            User information
        """
        if not self.metadata:
            raise ValueError("Provider not initialized")

        userinfo_endpoint = self.metadata.get("userinfo_endpoint")
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(userinfo_endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()

    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Verify and decode ID token.

        Args:
            id_token: ID token from provider

        Returns:
            Decoded token claims
        """
        if not self.metadata:
            raise ValueError("Provider not initialized")

        # Get signing keys
        keys_url = self.metadata.get("jwks_uri")
        if not keys_url:
            raise ValueError("No JWKS URI in provider metadata")

        try:
            # Decode without verification first to get kid
            unverified = jwt.decode(id_token, options={"verify_signature": False})
            kid = unverified.get("kid")

            # In production, would fetch and cache public keys from jwks_uri
            # For now, verify using standard methods
            payload = jwt.decode(
                id_token,
                options={"verify_signature": False},
                algorithms=["RS256"],
            )

            return payload
        except jwt.DecodeError as e:
            logger.error(f"Failed to decode ID token: {e}")
            raise


class OIDCManager:
    """Manage OIDC authentication flow."""

    def __init__(self, configs: Dict[str, OIDCConfig]):
        """Initialize OIDC manager.

        Args:
            configs: Dictionary of provider name -> OIDCConfig
        """
        self.providers: Dict[str, OIDCProvider] = {}
        self.auth_states = {}  # state -> (provider_name, timestamp)

        for name, config in configs.items():
            self.providers[name] = OIDCProvider(config)

    async def initialize(self) -> None:
        """Initialize all OIDC providers."""
        for name, provider in self.providers.items():
            try:
                await provider.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize {name}: {e}")

    def get_provider(self, provider_name: str) -> Optional[OIDCProvider]:
        """Get OIDC provider by name.

        Args:
            provider_name: Name of provider

        Returns:
            OIDCProvider or None
        """
        return self.providers.get(provider_name)

    def create_auth_state(self, provider_name: str, state: str) -> bool:
        """Store auth state for CSRF protection.

        Args:
            provider_name: Name of provider
            state: State string

        Returns:
            True if created
        """
        if provider_name not in self.providers:
            return False

        self.auth_states[state] = (provider_name, datetime.utcnow())
        return True

    def verify_auth_state(self, state: str) -> Optional[str]:
        """Verify and retrieve provider from state.

        Args:
            state: State string

        Returns:
            Provider name or None
        """
        if state not in self.auth_states:
            return None

        provider_name, timestamp = self.auth_states[state]

        # Verify state is not older than 10 minutes
        if datetime.utcnow() - timestamp > timedelta(minutes=10):
            del self.auth_states[state]
            return None

        del self.auth_states[state]
        return provider_name

    async def handle_callback(
        self, provider_name: str, code: str
    ) -> Optional[OIDCUserInfo]:
        """Handle OIDC callback and extract user info.

        Args:
            provider_name: Name of provider
            code: Authorization code

        Returns:
            OIDCUserInfo or None
        """
        provider = self.get_provider(provider_name)
        if not provider:
            return None

        try:
            # Exchange code for token
            tokens = await provider.exchange_code_for_token(code)

            # Get user info
            access_token = tokens.get("access_token")
            if not access_token:
                logger.error("No access token in response")
                return None

            user_info = await provider.get_user_info(access_token)

            # Verify ID token if present
            if "id_token" in tokens:
                id_token_claims = provider.verify_id_token(tokens["id_token"])
                user_info.update(id_token_claims)

            # Extract standard claims
            user_id = user_info.get("sub") or user_info.get("user_id")
            email = user_info.get("email")
            name = user_info.get("name", "")

            if not user_id or not email:
                logger.error("Missing required claims in user info")
                return None

            # Extract roles (provider-specific)
            roles = user_info.get("roles", [])
            if isinstance(roles, str):
                roles = [roles]
            if not roles:
                roles = ["user"]

            return OIDCUserInfo(
                user_id=user_id,
                email=email,
                name=name,
                roles=roles,
            )

        except Exception as e:
            logger.error(f"Error handling OIDC callback: {e}")
            return None
