"""The MCP server must run on just the `[mcp]` extra — it must not pull in the
FastAPI (`[api]`) stack transitively, or `pip install 'mcp-api-connect[mcp]'`
is broken (and Glama / MCP hosts that build the Dockerfile can't start it)."""

import sys

import pytest

from mcp_api_connect.core.models import (
    AuthSpec,
    AuthType,
    Connector,
    InvokeSpec,
    RequestFormat,
    Target,
)
from mcp_api_connect.storage.factory import build_store, redact_connector


def test_mcp_server_does_not_import_fastapi_stack():
    import mcp_api_connect.mcp_server.server  # noqa: F401

    assert "fastapi" not in sys.modules
    assert "mcp_api_connect.api.app" not in sys.modules


def test_build_store_defaults_to_in_memory(monkeypatch):
    monkeypatch.delenv("MCP_API_CONNECT_DB_PATH", raising=False)
    from mcp_api_connect.storage.memory import InMemoryConnectorStore

    assert isinstance(build_store(), InMemoryConnectorStore)


def test_redact_connector_masks_credentials():
    connector = Connector(
        name="x",
        spec=InvokeSpec(
            target=Target(base_url="https://api.example.com"),
            auth=AuthSpec(type=AuthType.API_KEY, config={"api_key": "secret", "header_name": "X-Key"}),
            request_format=RequestFormat(method="POST", path="/v1"),
        ),
    )
    redacted = redact_connector(connector)
    assert redacted["spec"]["auth"]["config"] == {"api_key": "***", "header_name": "***"}


@pytest.mark.asyncio
async def test_mcp_tools_are_registered():
    from mcp_api_connect.mcp_server.server import mcp

    tools = await mcp.list_tools()
    assert {t.name for t in tools} == {
        "invoke",
        "register_connector",
        "list_connectors",
        "invoke_connector",
        "delete_connector",
    }
