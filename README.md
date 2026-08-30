<!-- mcp-name: io.github.bvenkata/mcp-api-connect -->

# mcp-api-connect&trade;

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

**One payload in, any API out.** mcp-api-connect is a protocol- and auth-agnostic
connector engine: describe a target service (URL, protocol, auth, request/
response shape) once, then send it a normalized payload and get a normalized
response back — whether the target is a REST/JSON API, a legacy SOAP service,
protected by an API key, Basic auth, a Bearer token, or OAuth2 client
credentials.

It ships as three things built on the same core engine, so however you want
to use it, you can:

- **A Python library** — `pip install mcp-api-connect`, call `MCPAPIConnectEngine`
  directly, no server required.
- **A standalone HTTP API** — `pip install mcp-api-connect[api]`, run
  `mcp-api-connect-api`, POST to `/invoke`.
- **An MCP server** — `pip install mcp-api-connect[mcp]`, run `mcp-api-connect`,
  point any MCP client (Claude, etc.) at it so an agent can call registered
  connectors — or arbitrary services on the fly — as tools.

## Why

Every integration project reinvents the same wheel: a REST client here, a
SOAP client there, one auth flow per service, ad-hoc request/response
mapping scattered across the codebase. mcp-api-connect centralizes that into one
declarative spec (`InvokeSpec`) and one execution engine, so adding a new
target service is config, not code.

## Quick start (library)

```bash
pip install mcp-api-connect
```

```python
import asyncio
from mcp_api_connect import MCPAPIConnectEngine, InvokeSpec, Target, AuthSpec, AuthType, RequestFormat, ResponseFormat

spec = InvokeSpec(
    target=Target(base_url="https://api.example.com"),
    auth=AuthSpec(type=AuthType.API_KEY, config={"api_key": "secret", "header_name": "X-API-Key"}),
    request_format=RequestFormat(method="POST", path="/v1/orders", content_type="json"),
    response_format=ResponseFormat(content_type="json"),
)

async def main():
    async with MCPAPIConnectEngine() as engine:
        result = await engine.invoke(spec, {"customer": "jane"})
        print(result.success, result.data)

asyncio.run(main())
```

## Quick start (HTTP API)

```bash
pip install "mcp-api-connect[api]"
mcp-api-connect-api   # serves on :8000, interactive docs at /docs
```

```bash
curl -X POST http://localhost:8000/invoke -H 'content-type: application/json' -d '{
  "spec": {
    "target": {"base_url": "https://api.example.com"},
    "auth": {"type": "api_key", "config": {"api_key": "secret"}},
    "request_format": {"method": "POST", "path": "/v1/orders"},
    "response_format": {"content_type": "json"}
  },
  "payload": {"customer": "jane"}
}'
```

Register a reusable connector once, then invoke it by name:

```bash
curl -X POST http://localhost:8000/connectors -d '{"name": "orders-api", "spec": {...}}'
curl -X POST http://localhost:8000/connectors/orders-api/invoke -d '{"customer": "jane"}'
```

## Quick start (MCP)

```bash
pip install "mcp-api-connect[mcp]"
```

```json
{
  "mcpServers": {
    "mcp-api-connect": { "command": "/path/to/.venv/bin/mcp-api-connect" }
  }
}
```

Or run it in a container (stdio transport):

```bash
docker build -t mcp-api-connect .
docker run --rm -i mcp-api-connect
```

Exposes tools: `invoke` (stateless, one-off), `register_connector`,
`list_connectors`, `invoke_connector` (by name), `delete_connector`. An agent
can register a connector for "the Salesforce API" once, then just say "call
it with this payload" from then on.

**➜ Full setup for Claude Desktop / Claude Code / Cursor, persistence,
security notes, and a worked example: [docs/mcp-integration.md](docs/mcp-integration.md).**

## Core concepts

- **`Target`** — base URL, protocol (`rest` | `soap`), timeout, default headers.
- **`AuthSpec`** — `type` (`none`, `api_key`, `basic`, `bearer`,
  `oauth2_client_credentials`) + a `config` dict shaped for that type. OAuth2
  tokens are fetched and cached automatically.
- **`RequestFormat`** / **`ResponseFormat`** — content type (`json`, `xml`,
  `soap`) plus a declarative `field_map` (`{"target.path": "$.source.jsonpath"}`)
  for reshaping payloads without writing code, or a Jinja2 `body_template`
  for full control (required for SOAP envelopes).
- **`InvokeSpec`** — bundles the three above; the unit of "how to reach one
  service." Store it as a named `Connector` or pass it inline per call.

See [`src/mcp_api_connect/core/models.py`](src/mcp_api_connect/core/models.py) for the
full schema, and [docs/auth-reference.md](docs/auth-reference.md) for the
`config` shape each auth `type` expects.

## Documentation

- [docs/mcp-integration.md](docs/mcp-integration.md) — full MCP client setup
  (Claude Desktop, Claude Code, Cursor), persistence, security, tool
  reference, worked example, troubleshooting
- [docs/auth-reference.md](docs/auth-reference.md) — `config` fields for
  every auth type
- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup, running tests, PR expectations

## Extending

- New auth type: implement `AuthStrategy`, register via
  `engine.register_auth_strategy(...)`.
- New protocol (e.g. GraphQL): implement `ProtocolAdapter`, register via
  `engine.register_adapter(...)`.
- New connector storage backend: implement `ConnectorStore` (ships with
  `InMemoryConnectorStore` and `SqliteConnectorStore`, credentials encrypted
  at rest via Fernet).

## Roadmap

- OAuth2 authorization-code flow, mTLS, AWS SigV4 auth strategies
- WSDL-driven SOAP (optional `zeep`-backed adapter, no hand-written envelope needed)
- GraphQL adapter
- Postgres-backed `ConnectorStore`
- Retry/backoff + rate limiting policies per connector
- SSRF-safe target allow-listing for public deployments

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,api,storage,mcp]"
pytest
```

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

Contributions are accepted under the same license (inbound = outbound); see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Trademark

**mcp-api-connect&trade;** is a trademark of Balaji Venkatasubramaniyar. The
Apache 2.0 license covers copyright and patents but grants no trademark rights.
You may use the name to refer to this project and to state compatibility, but
not to name a fork, product, or service, or to imply endorsement. See
[TRADEMARKS.md](TRADEMARKS.md) for the full policy.
