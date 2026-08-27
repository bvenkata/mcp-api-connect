from __future__ import annotations

import asyncio

from configmesh.core.models import Connector
from configmesh.storage.base import ConnectorStore


class InMemoryConnectorStore(ConnectorStore):
    """Zero-setup default. Not persisted across restarts, not shared across
    processes — fine for a single dev/test process, swap in
    SqliteConnectorStore (or your own ConnectorStore) for anything real."""

    def __init__(self) -> None:
        self._connectors: dict[str, Connector] = {}
        self._lock = asyncio.Lock()

    async def save(self, connector: Connector) -> None:
        async with self._lock:
            self._connectors[connector.name] = connector

    async def get(self, name: str) -> Connector | None:
        return self._connectors.get(name)

    async def list(self) -> list[Connector]:
        return list(self._connectors.values())

    async def delete(self, name: str) -> bool:
        async with self._lock:
            return self._connectors.pop(name, None) is not None
