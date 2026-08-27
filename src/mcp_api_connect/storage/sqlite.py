"""Persistent connector store backed by SQLite, with `auth.config` (the
only place raw credentials live) encrypted at rest via Fernet.

Requires the `mcp_api_connect[storage]` extra (`cryptography`).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from mcp_api_connect.core.models import Connector
from mcp_api_connect.storage.base import ConnectorStore

try:
    from cryptography.fernet import Fernet
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "SqliteConnectorStore requires the 'storage' extra: pip install 'mcp_api_connect[storage]'"
    ) from exc

_SCHEMA = """
CREATE TABLE IF NOT EXISTS connectors (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL DEFAULT '',
    spec_json TEXT NOT NULL,          -- everything except auth.config
    auth_config_encrypted BLOB NOT NULL
);
"""


class SqliteConnectorStore(ConnectorStore):
    def __init__(self, db_path: str | Path, encryption_key: bytes | None = None):
        """`encryption_key` must be a urlsafe-base64 32-byte Fernet key
        (generate one with `Fernet.generate_key()` and keep it out of
        source control, e.g. in an env var). If omitted, one is generated
        per-instance — fine for tests, NOT fine for real persistence since
        you'd lose the ability to decrypt after a restart."""
        self._path = str(db_path)
        self._fernet = Fernet(encryption_key or Fernet.generate_key())
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._path)
        try:
            conn.execute(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    async def save(self, connector: Connector) -> None:
        spec_dict = connector.spec.model_dump(mode="json")
        auth_config = spec_dict["auth"].pop("config", {})
        encrypted = self._fernet.encrypt(json.dumps(auth_config).encode("utf-8"))

        conn = sqlite3.connect(self._path)
        try:
            conn.execute(
                "INSERT INTO connectors (name, description, spec_json, auth_config_encrypted) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET description=excluded.description, "
                "spec_json=excluded.spec_json, auth_config_encrypted=excluded.auth_config_encrypted",
                (connector.name, connector.description, json.dumps(spec_dict), encrypted),
            )
            conn.commit()
        finally:
            conn.close()

    async def get(self, name: str) -> Connector | None:
        conn = sqlite3.connect(self._path)
        try:
            row = conn.execute(
                "SELECT description, spec_json, auth_config_encrypted FROM connectors WHERE name = ?",
                (name,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return self._row_to_connector(name, *row)

    async def list(self) -> list[Connector]:
        conn = sqlite3.connect(self._path)
        try:
            rows = conn.execute(
                "SELECT name, description, spec_json, auth_config_encrypted FROM connectors"
            ).fetchall()
        finally:
            conn.close()
        return [self._row_to_connector(*row) for row in rows]

    async def delete(self, name: str) -> bool:
        conn = sqlite3.connect(self._path)
        try:
            cur = conn.execute("DELETE FROM connectors WHERE name = ?", (name,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def _row_to_connector(
        self, name: str, description: str, spec_json: str, auth_config_encrypted: bytes
    ) -> Connector:
        spec_dict = json.loads(spec_json)
        auth_config = json.loads(self._fernet.decrypt(auth_config_encrypted).decode("utf-8"))
        spec_dict["auth"]["config"] = auth_config
        return Connector(name=name, description=description, spec=spec_dict)
