"""Core data models shared by every transport (HTTP API, MCP, library calls).

These are intentionally transport-agnostic pydantic models: the same
`InvokeSpec` you build in Python code is what gets posted to `/invoke`
or passed as MCP tool arguments.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Protocol(str, Enum):
    REST = "rest"
    SOAP = "soap"


class AuthType(str, Enum):
    NONE = "none"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER = "bearer"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"


class ApiKeyLocation(str, Enum):
    HEADER = "header"
    QUERY = "query"


class AuthSpec(BaseModel):
    """Auth configuration. `config` shape depends on `type`:

    - none: {}
    - api_key: {api_key, header_name?="X-API-Key", location?="header", param_name?}
    - basic: {username, password}
    - bearer: {token}
    - oauth2_client_credentials: {token_url, client_id, client_secret, scope?, audience?}
    """

    type: AuthType = AuthType.NONE
    config: dict[str, Any] = Field(default_factory=dict)


class Target(BaseModel):
    base_url: str
    protocol: Protocol = Protocol.REST
    timeout_seconds: float = 30.0
    default_headers: dict[str, str] = Field(default_factory=dict)
    verify_tls: bool = True


class RequestFormat(BaseModel):
    """How the normalized `payload` gets turned into an outbound call."""

    method: str = "POST"
    path: str = ""
    content_type: str = "json"  # "json" | "xml" | "soap"
    headers: dict[str, str] = Field(default_factory=dict)

    # JSON path-mapping: {"target.field.path": "$.source.jsonpath"}.
    # If omitted, the payload is forwarded as-is for content_type == "json".
    field_map: dict[str, str] | None = None

    # Jinja2 template rendering the outbound body. Required for content_type
    # in {"xml", "soap"} unless field_map + a default XML builder is enough.
    # Rendered with `payload` (and, for SOAP, `soap_action`) in scope.
    body_template: str | None = None

    # SOAP-specific
    soap_action: str | None = None


class ResponseFormat(BaseModel):
    """How the raw response is normalized back to a plain dict."""

    content_type: str = "json"  # "json" | "xml" | "soap"

    # Same target-path -> source-jsonpath mapping as RequestFormat.field_map,
    # applied to the parsed response body (XML/SOAP is parsed to dict first).
    field_map: dict[str, str] | None = None

    # For SOAP: unwrap <soap:Envelope><soap:Body>...</soap:Body></soap:Envelope>
    # before applying field_map / returning.
    unwrap_soap_body: bool = True

    include_raw: bool = False


class InvokeSpec(BaseModel):
    """Everything needed to reach a target service, minus the payload."""

    target: Target
    auth: AuthSpec = Field(default_factory=AuthSpec)
    request_format: RequestFormat = Field(default_factory=RequestFormat)
    response_format: ResponseFormat = Field(default_factory=ResponseFormat)


class InvokeRequest(BaseModel):
    """Body for the stateless `/invoke` endpoint / `invoke` MCP tool."""

    spec: InvokeSpec
    payload: dict[str, Any] = Field(default_factory=dict)


class InvokeResult(BaseModel):
    success: bool
    status_code: int | None = None
    data: dict[str, Any] | None = None
    raw_body: str | None = None
    error: str | None = None
    latency_ms: float = 0.0


class Connector(BaseModel):
    """A named, storable `InvokeSpec` — what `/connectors` persists."""

    name: str
    description: str = ""
    spec: InvokeSpec


class MCPAPIConnectError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
