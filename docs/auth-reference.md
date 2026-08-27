# Auth types reference

Every `AuthSpec` is `{"type": "<one of below>", "config": {...}}`. `config`
keys are specific to `type` — this page is the source of truth for what
each one expects. Implementation: [`core/auth/strategies.py`](../src/mcp_api_connect/core/auth/strategies.py).

## `none`

No credentials attached.

```json
{ "type": "none", "config": {} }
```

## `api_key`

Attaches a static key as a header (default) or query param.

```json
{ "type": "api_key", "config": {
  "api_key": "sk_live_abc123",
  "header_name": "X-API-Key",
  "location": "header"
} }
```

| Field | Required | Default | Notes |
|---|---|---|---|
| `api_key` | yes | — | the raw key value |
| `header_name` | no | `"X-API-Key"` | used when `location` is `"header"` |
| `location` | no | `"header"` | `"header"` or `"query"` |
| `param_name` | no | `"api_key"` | used when `location` is `"query"` |

## `basic`

Standard HTTP Basic auth (`Authorization: Basic base64(user:pass)`).

```json
{ "type": "basic", "config": { "username": "svc-account", "password": "hunter2" } }
```

## `bearer`

Attaches a static, pre-obtained token as `Authorization: Bearer <token>`.
Use this when you already have a long-lived token (e.g. a PAT) — for
tokens you need to *fetch*, use `oauth2_client_credentials` instead.

```json
{ "type": "bearer", "config": { "token": "ghp_xxx..." } }
```

## `oauth2_client_credentials`

Fetches a token via the OAuth2 client-credentials grant, caches it
in-process until ~30s before `expires_in` elapses, and refreshes
automatically on the next call after that — you never see the token
exchange happen per-request.

```json
{ "type": "oauth2_client_credentials", "config": {
  "token_url": "https://auth.example.com/oauth/token",
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "scope": "orders:write",
  "audience": "https://api.example.com"
} }
```

| Field | Required | Notes |
|---|---|---|
| `token_url` | yes | the token endpoint |
| `client_id` | yes | |
| `client_secret` | yes | |
| `scope` | no | space-delimited scopes, if the provider needs them |
| `audience` | no | some providers (e.g. Auth0) require this |

Token caching is per `MCPAPIConnectEngine` instance, keyed by
`(token_url, client_id)` — long-running server/MCP processes reuse one
token across many calls instead of re-authenticating every time.

## Not yet implemented

OAuth2 authorization-code flow, mTLS, and AWS SigV4 are on the
[roadmap](../README.md#roadmap). Need one sooner? Implement `AuthStrategy`
([`core/auth/base.py`](../src/mcp_api_connect/core/auth/base.py)) and register
it with `engine.register_auth_strategy(AuthType.YOUR_TYPE, YourStrategy())`
— no core changes required, and contributions welcome.
