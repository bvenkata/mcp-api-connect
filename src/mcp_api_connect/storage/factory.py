"""Environment-driven ConnectorStore construction and credential redaction.

Lives here (not in a transport module) so both the REST API and the MCP
server can share it without one pulling in the other's optional dependencies.
"""

from __future__ import annotations

import os
from typing import Any

from mcp_api_connect.core.models import Connector
from mcp_api_connect.storage.base import ConnectorStore
from mcp_api_connect.storage.memory import InMemoryConnectorStore


def build_store() -> ConnectorStore:
    """Build a ConnectorStore from environment variables:

    - ``MCP_API_CONNECT_DB_PATH`` — if set, use a ``SqliteConnectorStore`` at
      this path (requires the ``mcp-api-connect[storage]`` extra).
    - ``MCP_API_CONNECT_ENCRYPTION_KEY`` — Fernet key for that store.

    Falls back to an in-memory store when ``MCP_API_CONNECT_DB_PATH`` is unset.
    """
    db_path = os.environ.get("MCP_API_CONNECT_DB_PATH")
    if not db_path:
        return InMemoryConnectorStore()

    from mcp_api_connect.storage.sqlite import SqliteConnectorStore

    key = os.environ.get("MCP_API_CONNECT_ENCRYPTION_KEY")
    return SqliteConnectorStore(db_path, encryption_key=key.encode() if key else None)


def redact_connector(connector: Connector) -> dict[str, Any]:
    """A JSON-ready dict for ``connector`` with auth credentials masked, for
    use in any list/get response so raw secrets are never echoed back."""
    data = connector.model_dump(mode="json")
    if data["spec"]["auth"]["config"]:
        data["spec"]["auth"]["config"] = {k: "***" for k in data["spec"]["auth"]["config"]}
    return data
