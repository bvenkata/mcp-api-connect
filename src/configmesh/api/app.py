"""Thin FastAPI transport over ConfigMeshEngine. Run directly:

    uvicorn configmesh.api.app:app --reload

or via the installed console script:

    configmesh-api

Env vars:
    CONFIGMESH_DB_PATH        - if set, uses SqliteConnectorStore at this path
                                 (needs `pip install 'configmesh[storage]'`)
    CONFIGMESH_ENCRYPTION_KEY - Fernet key for the sqlite store (required
                                 alongside CONFIGMESH_DB_PATH for real use;
                                 generate with Fernet.generate_key())
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException

from configmesh.core.engine import ConfigMeshEngine
from configmesh.core.models import Connector, InvokeRequest, InvokeResult
from configmesh.storage.base import ConnectorStore
from configmesh.storage.memory import InMemoryConnectorStore


def _build_store() -> ConnectorStore:
    db_path = os.environ.get("CONFIGMESH_DB_PATH")
    if not db_path:
        return InMemoryConnectorStore()
    from configmesh.storage.sqlite import SqliteConnectorStore

    key = os.environ.get("CONFIGMESH_ENCRYPTION_KEY")
    return SqliteConnectorStore(db_path, encryption_key=key.encode() if key else None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = ConfigMeshEngine()
    app.state.store = _build_store()
    yield
    await app.state.engine.aclose()


app = FastAPI(
    title="ConfigMesh",
    description="Protocol- and auth-agnostic API connector engine.",
    version="0.1.0",
    lifespan=lifespan,
)


def _redact(connector: Connector) -> dict[str, Any]:
    """Never echo back raw credentials in list/get responses."""
    data = connector.model_dump(mode="json")
    if data["spec"]["auth"]["config"]:
        data["spec"]["auth"]["config"] = {k: "***" for k in data["spec"]["auth"]["config"]}
    return data


@app.post("/invoke", response_model=InvokeResult)
async def invoke(request: InvokeRequest) -> InvokeResult:
    """Stateless call: full target/auth/format spec + payload in one shot."""
    return await app.state.engine.invoke(request.spec, request.payload)


@app.post("/connectors", status_code=201)
async def create_connector(connector: Connector) -> dict[str, Any]:
    await app.state.store.save(connector)
    return _redact(connector)


@app.get("/connectors")
async def list_connectors() -> list[dict[str, Any]]:
    return [_redact(c) for c in await app.state.store.list()]


@app.get("/connectors/{name}")
async def get_connector(name: str) -> dict[str, Any]:
    connector = await app.state.store.get(name)
    if connector is None:
        raise HTTPException(status_code=404, detail=f"No connector named '{name}'")
    return _redact(connector)


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

    uvicorn.run("configmesh.api.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
