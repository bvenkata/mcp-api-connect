from __future__ import annotations

import base64
import time

import httpx

from mcp_api_connect.core.auth.base import AuthStrategy, PreparedAuth
from mcp_api_connect.core.models import AuthSpec, MCPAPIConnectError


class NoneAuth(AuthStrategy):
    async def prepare(self, auth: AuthSpec, client: httpx.AsyncClient) -> PreparedAuth:
        return PreparedAuth()


class ApiKeyAuth(AuthStrategy):
    async def prepare(self, auth: AuthSpec, client: httpx.AsyncClient) -> PreparedAuth:
        cfg = auth.config
        api_key = _require(cfg, "api_key")
        location = cfg.get("location", "header")
        if location == "query":
            param_name = cfg.get("param_name", "api_key")
            return PreparedAuth(params={param_name: api_key})
        header_name = cfg.get("header_name", "X-API-Key")
        return PreparedAuth(headers={header_name: api_key})


class BasicAuth(AuthStrategy):
    async def prepare(self, auth: AuthSpec, client: httpx.AsyncClient) -> PreparedAuth:
        cfg = auth.config
        username = _require(cfg, "username")
        password = _require(cfg, "password")
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return PreparedAuth(headers={"Authorization": f"Basic {token}"})


class BearerAuth(AuthStrategy):
    async def prepare(self, auth: AuthSpec, client: httpx.AsyncClient) -> PreparedAuth:
        token = _require(auth.config, "token")
        return PreparedAuth(headers={"Authorization": f"Bearer {token}"})


class OAuth2ClientCredentialsAuth(AuthStrategy):
    """Fetches (and caches, per token_url+client_id, until near-expiry) a
    client-credentials token, then attaches it as a Bearer token."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], tuple[str, float]] = {}

    async def prepare(self, auth: AuthSpec, client: httpx.AsyncClient) -> PreparedAuth:
        cfg = auth.config
        token_url = _require(cfg, "token_url")
        client_id = _require(cfg, "client_id")
        client_secret = _require(cfg, "client_secret")
        scope = cfg.get("scope")
        audience = cfg.get("audience")

        cache_key = (token_url, client_id)
        cached = self._cache.get(cache_key)
        now = time.monotonic()
        if cached and cached[1] > now:
            return PreparedAuth(headers={"Authorization": f"Bearer {cached[0]}"})

        data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
        if scope:
            data["scope"] = scope
        if audience:
            data["audience"] = audience

        resp = await client.post(token_url, data=data)
        if resp.status_code >= 400:
            raise MCPAPIConnectError(
                f"OAuth2 token request failed ({resp.status_code}): {resp.text}",
                status_code=resp.status_code,
            )
        body = resp.json()
        access_token = body.get("access_token")
        if not access_token:
            raise MCPAPIConnectError("OAuth2 token response missing 'access_token'")
        expires_in = float(body.get("expires_in", 3600))
        # Refresh a little early to avoid races right at expiry.
        self._cache[cache_key] = (access_token, now + max(expires_in - 30, 0))
        return PreparedAuth(headers={"Authorization": f"Bearer {access_token}"})


def _require(cfg: dict, key: str) -> str:
    value = cfg.get(key)
    if not value:
        raise MCPAPIConnectError(f"auth.config missing required field '{key}'")
    return value
