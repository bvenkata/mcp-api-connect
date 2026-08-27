# Using mcp-api-connect as an MCP server

mcp-api-connect's MCP server turns every registered (or ad-hoc) API connector
into a tool an agent can call — so instead of an agent needing to know a
target's URL, auth scheme, and payload shape every time, it can just say
*"call the orders API with this payload"*.

This guide covers: installing it, wiring it into your MCP client, the full
tool reference, a worked example end to end, and troubleshooting.

## 1. Install

```bash
pip install "mcp-api-connect[mcp]"
```

This installs the `mcp-api-connect` console script alongside the `mcp` SDK.
If you're working from a clone instead of a published package:

```bash
git clone https://github.com/bvenkata/mcp-api-connect.git
cd mcp-api-connect
python -m venv .venv && source .venv/bin/activate
pip install -e ".[mcp,storage]"
```

**Find the absolute path to the installed command** — MCP clients launch
this as a subprocess and usually won't have your virtualenv on `PATH`:

```bash
which mcp-api-connect
# e.g. /Users/you/mcp-api-connect/.venv/bin/mcp-api-connect
```

Use that absolute path in every config below (a relative `mcp-api-connect`
only works if the client happens to inherit your activated shell's `PATH`,
which most GUI apps don't).

## 2. Configure your MCP client

The server speaks stdio, so any MCP client works. A few common ones:

### Claude Desktop

Edit the config file (create it if it doesn't exist):
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mcp-api-connect": {
      "command": "/Users/you/mcp-api-connect/.venv/bin/mcp-api-connect"
    }
  }
}
```

Restart Claude Desktop. Look for the 🔌 tools icon to confirm mcp-api-connect's
five tools loaded.

### Claude Code

Project-scoped — add a `.mcp.json` at your project root:

```json
{
  "mcpServers": {
    "mcp-api-connect": {
      "command": "/Users/you/mcp-api-connect/.venv/bin/mcp-api-connect"
    }
  }
}
```

Or user-scoped via the CLI (check `claude mcp add --help` for the exact
flags on your installed version):

```bash
claude mcp add mcp-api-connect /Users/you/mcp-api-connect/.venv/bin/mcp-api-connect
```

### Cursor / other JSON-config MCP clients

Same shape as Claude Desktop — most clients accept:

```json
{
  "mcpServers": {
    "mcp-api-connect": { "command": "/Users/you/mcp-api-connect/.venv/bin/mcp-api-connect" }
  }
}
```

### Running it manually (debugging)

```bash
mcp-api-connect
```

It'll sit there waiting on stdio — that's normal, it's not meant to print
anything until a client speaks MCP to it. Ctrl+C to stop.

## 3. Persisting connectors across restarts

By default, connectors registered via `register_connector` live in memory
and vanish when the server process restarts. For anything beyond a single
session, point it at an encrypted SQLite store:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# save this key somewhere safe — losing it makes stored credentials unrecoverable
```

Add both env vars to your client config:

```json
{
  "mcpServers": {
    "mcp-api-connect": {
      "command": "/Users/you/mcp-api-connect/.venv/bin/mcp-api-connect",
      "env": {
        "MCP_API_CONNECT_DB_PATH": "/Users/you/.mcp-api-connect/connectors.db",
        "MCP_API_CONNECT_ENCRYPTION_KEY": "<the key you generated above>"
      }
    }
  }
}
```

Without `MCP_API_CONNECT_DB_PATH` set, mcp-api-connect uses an in-memory store —
fine for trying things out, but every `register_connector` call is gone
the moment the MCP client restarts the server process.

## 4. Tool reference

| Tool | Arguments | Returns | Use for |
|---|---|---|---|
| `invoke` | `spec` (full `InvokeSpec`), `payload` (dict) | `InvokeResult` | One-off calls to a service you won't reuse, or testing a spec before registering it |
| `register_connector` | `name`, `spec`, `description` (optional) | the saved connector (credentials redacted) | Save a target's URL/auth/format once |
| `list_connectors` | — | list of connectors (credentials redacted) | Let the agent discover what's already registered |
| `invoke_connector` | `name`, `payload` (dict) | `InvokeResult` | The common case — call a known service by name |
| `delete_connector` | `name` | `{"deleted": true/false}` | Remove a stale connector |

`InvokeResult` always looks like:
```json
{ "success": true, "status_code": 200, "data": {...}, "raw_body": null, "error": null, "latency_ms": 42.1 }
```

The full `InvokeSpec` shape (what `spec` looks like in `invoke` /
`register_connector`) is documented in the [main README](../README.md#core-concepts)
and [`core/models.py`](../src/mcp_api_connect/core/models.py). Auth `config`
shapes per type are in [docs/auth-reference.md](auth-reference.md).

## 5. Worked example

Say you want an agent to be able to create orders in an internal REST API
protected by an API key.

**Step 1 — register the connector.** The agent (or you, directly) calls:

```json
// tool: register_connector
{
  "name": "orders-api",
  "description": "Internal order creation service",
  "spec": {
    "target": { "base_url": "https://internal-api.company.com" },
    "auth": {
      "type": "api_key",
      "config": { "api_key": "sk_live_abc123", "header_name": "X-API-Key" }
    },
    "request_format": {
      "method": "POST",
      "path": "/v1/orders",
      "content_type": "json",
      "field_map": { "customer_name": "$.customer.name", "amount": "$.order.total" }
    },
    "response_format": {
      "content_type": "json",
      "field_map": { "orderId": "$.id", "status": "$.state" }
    }
  }
}
```

Response — note the credential comes back redacted, confirming it saved
without echoing the secret into the transcript again:
```json
{ "name": "orders-api", "description": "Internal order creation service",
  "spec": { "auth": { "type": "api_key", "config": { "api_key": "***" } }, ... } }
```

**Step 2 — from then on, the agent just does this** (no URL, no auth, no
format — all of that is already saved):

```json
// tool: invoke_connector
{ "name": "orders-api", "payload": { "customer": { "name": "Jane Doe" }, "order": { "total": 249.99 } } }
```

```json
{ "success": true, "status_code": 201, "data": { "orderId": "A1", "status": "created" }, "latency_ms": 142.3 }
```

The agent never needed to know the base URL, the header name, or the API
key on this second call — that's the point.

**Step 3 — discovery.** In a fresh conversation, an agent can call
`list_connectors` first to see `orders-api` (and whatever else your team
has registered) is available before deciding to use it.

## 6. Security notes

- **`list_connectors` / `register_connector`'s response redact secrets**,
  but the *arguments you send to* `register_connector` necessarily contain
  the raw credential once (that's how it gets in) — expect it to appear in
  your MCP client's own request logs/transcript the same way any secret
  you paste into a chat would. Treat that transcript accordingly.
- **In-memory store = plaintext in process memory**, gone on restart. The
  SQLite store encrypts `auth.config` at rest with Fernet, but the
  encryption key itself is only as safe as the env var / secrets manager
  you keep it in.
- **This server does not currently allow-list target URLs.** If you expose
  `invoke` to an agent that takes untrusted instructions, it could be
  directed to call an internal/unintended host. Fine for a personal or
  trusted-team setup; before exposing this more broadly, see the SSRF item
  in the [README roadmap](../README.md#roadmap).

## 7. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Tools don't show up in the client | Config file JSON is invalid, or the client wasn't restarted after editing it. Validate the JSON, restart the client. |
| `command not found` / spawn error | You used a bare `mcp-api-connect` instead of the absolute path from `which mcp-api-connect` — the client's subprocess doesn't have your shell's `PATH`. |
| `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` | You have `mcp` 1.x installed; mcp-api-connect's MCP transport targets 2.x (`MCPServer`). `pip install --upgrade "mcp>=2.0"`. |
| Registered connectors disappear after restarting the client | You're on the default in-memory store — set `MCP_API_CONNECT_DB_PATH` (+ `MCP_API_CONNECT_ENCRYPTION_KEY`) as in step 3. |
| `invoke`/`invoke_connector` returns `"success": false` with an auth error | Check `auth.config` has every field that auth type requires — see [auth-reference.md](auth-reference.md). |
