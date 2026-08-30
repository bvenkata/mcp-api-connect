"""Thin FastAPI transport over MCPAPIConnectEngine. Run directly:

    uvicorn mcp_api_connect.api.app:app --reload

or via the installed console script:

    mcp_api_connect-api

Env vars:
    MCP_API_CONNECT_DB_PATH        - if set, uses SqliteConnectorStore at this path
                                 (needs `pip install 'mcp_api_connect[storage]'`)
    MCP_API_CONNECT_ENCRYPTION_KEY - Fernet key for the sqlite store (required
                                 alongside MCP_API_CONNECT_DB_PATH for real use;
                                 generate with Fernet.generate_key())
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException

from mcp_api_connect.core.engine import MCPAPIConnectEngine
from mcp_api_connect.core.models import Connector, InvokeRequest, InvokeResult
from mcp_api_connect.storage.factory import build_store, redact_connector


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = MCPAPIConnectEngine()
    app.state.store = build_store()
    yield
    await app.state.engine.aclose()


app = FastAPI(
    title="mcp-api-connect",
    description="Protocol- and auth-agnostic API connector engine.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.post("/invoke", response_model=InvokeResult)
async def invoke(request: InvokeRequest) -> InvokeResult:
    """Stateless call: full target/auth/format spec + payload in one shot."""
    return await app.state.engine.invoke(request.spec, request.payload)


@app.post("/connectors", status_code=201)
async def create_connector(connector: Connector) -> dict[str, Any]:
    await app.state.store.save(connector)
    return redact_connector(connector)


@app.get("/connectors")
async def list_connectors() -> list[dict[str, Any]]:
    return [redact_connector(c) for c in await app.state.store.list()]


@app.get("/connectors/{name}")
async def get_connector(name: str) -> dict[str, Any]:
    connector = await app.state.store.get(name)
    if connector is None:
        raise HTTPException(status_code=404, detail=f"No connector named '{name}'")
    return redact_connector(connector)


@app.delete("/connectors/{name}", status_code=204)
async def delete_connector(name: str) -> None:
    deleted = await app.state.store.delete(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No connector named '{name}'")


@app.post("/connectors/{name}/invoke", response_model=InvokeResult)
async def invoke_connector(name: str, payload: dict[str, Any]) -> InvokeResult:
    connector = await app.state.store.get(name)
    if connector is None:
        raise HTTPException(status_code=404, detail=f"No connector named '{name}'")
    return await app.state.engine.invoke(connector.spec, payload)


def main() -> None:
    import uvicorn

    uvicorn.run("mcp_api_connect.api.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
