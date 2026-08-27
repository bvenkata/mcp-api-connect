# Contributing to ConfigMesh

## Setup

```bash
git clone https://github.com/bvenkata/configmesh.git
cd configmesh
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,api,storage,mcp]"
```

## Running tests and lint

```bash
pytest -q
ruff check src tests
```

Both must pass before a PR is merged. Tests use [`respx`](https://lundberg.github.io/respx/)
to mock `httpx` — no real network calls, no live services needed to run the
suite.

## Project layout

| Path | What lives there |
|---|---|
| `src/configmesh/core/` | The engine, models, auth strategies, protocol adapters, transform logic. No FastAPI/MCP dependency leaks in here. |
| `src/configmesh/storage/` | Pluggable `ConnectorStore` implementations. |
| `src/configmesh/api/` | FastAPI transport. |
| `src/configmesh/mcp_server/` | MCP transport. |
| `tests/` | Mirrors the above; add tests alongside whatever you change. |

See the [README](README.md#extending) for the extension points (new auth
type, new protocol adapter, new storage backend) — most contributions will
be one of these three shapes.

## Adding a new auth type or protocol adapter

1. Implement the interface (`AuthStrategy` in `core/auth/base.py`, or
   `ProtocolAdapter` in `core/adapters/base.py`).
2. Add it to the relevant `DEFAULT_*_REGISTRY` in that module's `__init__.py`
   so it's available out of the box (rather than requiring every caller to
   `register_auth_strategy`/`register_adapter` manually).
3. Add the new `AuthType`/`Protocol` enum value in `core/models.py`.
4. Add tests in `tests/` mirroring the existing REST/SOAP/OAuth2 examples.
5. Document the new `config` shape in `docs/auth-reference.md` (for auth
   types) so it's discoverable without reading source.

## PRs

- Keep PRs scoped to one logical change.
- Add/update tests for behavior changes — a PR that changes engine behavior
  without a test covering it will get asked for one.
- Run `ruff check` locally; CI will catch anything missed.

## Reporting issues

Open a GitHub issue with: what you tried (`InvokeSpec` shape is fine to
paste — redact real credentials first), what you expected, what happened
instead, and the `InvokeResult.error` if there was one.
