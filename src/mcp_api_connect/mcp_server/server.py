"""MCP transport over MCPAPIConnectEngine — lets an LLM agent call arbitrary
REST/SOAP services (stateless `invoke`) or pre-registered connectors
(`register_connector` + `invoke_connector`) as tools.

Run with:
    mcp-api-connect                    # stdio transport (default MCP client config)

Point an MCP client at it, e.g. in Claude Desktop / Claude Code config:
    {
      "mcpServers": {
        "mcp-api-connect": { "command": "mcp-api-connect" }
      }
    }

Env vars: MCP_API_CONNECT_DB_PATH / MCP_API_CONNECT_ENCRYPTION_KEY (see
mcp_api_connect.storage.factory.build_store) — set these so connectors
registered by one agent session persist and are visible to the next.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from mcp_api_connect.core.engine import MCPAPIConnectEngine
from mcp_api_connect.core.models import Connector, InvokeSpec
from mcp_api_connect.storage.factory import build_store, redact_connector

mcp = MCPServer("MCPAPIConnect")

_engine = MCPAPIConnectEngine()
_store = build_store()


@mcp.tool()
async def invoke(spec: InvokeSpec, payload: dict[str, Any]) -> dict[str, Any]:
    """Call any REST or SOAP service in one shot: give the target URL,
    auth details, and request/response format alongside the payload. Use
    this for one-off/unregistered targets; prefer `invoke_connector` for
    services you'll call repeatedly."""
    result = await _engine.invoke(spec, payload)
    return result.model_dump(mode="json")


@mcp.tool()
async def register_connector(name: str, spec: InvokeSpec, description: str = "") -> dict[str, Any]:
    """Register a reusable, named connector (target + auth + formats) so
    it can be invoked later by name via `invoke_connector` without
    resending credentials each time."""
    connector = Connector(name=name, description=description, spec=spec)
    await _store.save(connector)
    return redact_connector(connector)


@mcp.tool()
async def list_connectors() -> list[dict[str, Any]]:
    """List registered connectors (credentials redacted) so an agent can
    discover what's already available before calling `invoke_connector`."""
    return [redact_connector(c) for c in await _store.list()]


@mcp.tool()
async def invoke_connector(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Invoke a previously registered connector by name with just a
    payload — the target/auth/format details were supplied at
    registration time."""
    connector = await _store.get(name)
    if connector is None:
        return {"success": False, "error": f"No connector named '{name}'"}
    result = await _engine.invoke(connector.spec, payload)
    return result.model_dump(mode="json")


@mcp.tool()
async def delete_connector(name: str) -> dict[str, Any]:
    """Remove a registered connector."""
    deleted = await _store.delete(name)
    return {"deleted": deleted}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
