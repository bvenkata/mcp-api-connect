from __future__ import annotations

import time
from typing import Any

import httpx

from configmesh.core.adapters import DEFAULT_ADAPTER_REGISTRY, ProtocolAdapter
from configmesh.core.auth import DEFAULT_AUTH_REGISTRY, AuthStrategy
from configmesh.core.models import AuthType, ConfigMeshError, InvokeResult, InvokeSpec, Protocol
from configmesh.core.transform import parse_response_body


class ConfigMeshEngine:
    """The one thing every transport (FastAPI, MCP, your own script) calls.

    Usage:
        engine = ConfigMeshEngine()
        result = await engine.invoke(spec, payload)
        await engine.aclose()

    Or as an async context manager:
        async with ConfigMeshEngine() as engine:
            result = await engine.invoke(spec, payload)
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        auth_registry: dict[AuthType, AuthStrategy] | None = None,
        adapter_registry: dict[Protocol, ProtocolAdapter] | None = None,
    ) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient()
        self._auth_registry = dict(DEFAULT_AUTH_REGISTRY) if auth_registry is None else auth_registry
        self._adapter_registry = (
            dict(DEFAULT_ADAPTER_REGISTRY) if adapter_registry is None else adapter_registry
        )

    def register_auth_strategy(self, auth_type: AuthType, strategy: AuthStrategy) -> None:
        """Extend with a custom auth type (e.g. mTLS, AWS SigV4, oauth2 auth-code)."""
        self._auth_registry[auth_type] = strategy

    def register_adapter(self, protocol: Protocol, adapter: ProtocolAdapter) -> None:
        """Extend with a custom protocol adapter (e.g. GraphQL)."""
        self._adapter_registry[protocol] = adapter

    async def invoke(self, spec: InvokeSpec, payload: dict[str, Any]) -> InvokeResult:
        start = time.monotonic()
        try:
            auth_strategy = self._auth_registry.get(spec.auth.type)
            if auth_strategy is None:
                raise ConfigMeshError(f"No auth strategy registered for '{spec.auth.type}'")

            adapter = self._adapter_registry.get(spec.target.protocol)
            if adapter is None:
                raise ConfigMeshError(f"No protocol adapter registered for '{spec.target.protocol}'")

            prepared_auth = await auth_strategy.prepare(spec.auth, self._client)
            raw = await adapter.execute(spec.target, spec.request_format, prepared_auth, payload, self._client)
            data = parse_response_body(spec.response_format, raw.text)

            return InvokeResult(
                success=200 <= raw.status_code < 400,
                status_code=raw.status_code,
                data=data,
                raw_body=raw.text if spec.response_format.include_raw else None,
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except ConfigMeshError as exc:
            return InvokeResult(
                success=False,
                status_code=exc.status_code,
                error=exc.message,
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except httpx.HTTPError as exc:
            return InvokeResult(
                success=False,
                error=f"Transport error: {exc}",
                latency_ms=(time.monotonic() - start) * 1000,
            )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> ConfigMeshEngine:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
