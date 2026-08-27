from __future__ import annotations

from abc import ABC, abstractmethod

from configmesh.core.models import Connector


class ConnectorStore(ABC):
    """Pluggable registry for named, reusable connectors. Implementations
    are responsible for keeping `spec.auth.config` (raw credentials) safe —
    e.g. encrypted at rest — since that's where secrets live."""

    @abstractmethod
    async def save(self, connector: Connector) -> None: ...

    @abstractmethod
    async def get(self, name: str) -> Connector | None: ...

    @abstractmethod
    async def list(self) -> list[Connector]: ...

    @abstractmethod
    async def delete(self, name: str) -> bool: ...
