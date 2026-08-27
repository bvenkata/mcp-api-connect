"""Declarative payload <-> target-format mapping.

Field maps are `{"target.dot.path": "$.jsonpath.into.source"}`. No code
required: the same shape works for request-side mapping (payload ->
target's expected body) and response-side mapping (target's raw response
-> normalized dict), since both just take "a dict in" and "a dict, shaped
by the map, out".
"""

from __future__ import annotations

from typing import Any

import xmltodict
from jinja2 import Environment
from jsonpath_ng.ext import parse as jsonpath_parse

from mcp_api_connect.core.models import MCPAPIConnectError, RequestFormat, ResponseFormat

_jinja_env = Environment(autoescape=False)


def apply_field_map(field_map: dict[str, str], source: dict[str, Any]) -> dict[str, Any]:
    """Extract each jsonpath from `source` and set it at the corresponding
    dot-path in a freshly built target dict."""
    result: dict[str, Any] = {}
    for target_path, source_expr in field_map.items():
        matches = jsonpath_parse(source_expr).find(source)
        if not matches:
            continue
        value = matches[0].value if len(matches) == 1 else [m.value for m in matches]
        _set_dot_path(result, target_path, value)
    return result


def _set_dot_path(target: dict[str, Any], dot_path: str, value: Any) -> None:
    parts = dot_path.split(".")
    node = target
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def render_request_body(fmt: RequestFormat, payload: dict[str, Any]) -> tuple[bytes, str]:
    """Returns (body_bytes, content_type_header)."""
    if fmt.body_template:
        rendered = _jinja_env.from_string(fmt.body_template).render(
            payload=payload, soap_action=fmt.soap_action
        )
        content_type = "text/xml" if fmt.content_type in ("xml", "soap") else "application/json"
        return rendered.encode("utf-8"), content_type

    if fmt.content_type == "json":
        import json

        body = apply_field_map(fmt.field_map, payload) if fmt.field_map else payload
        return json.dumps(body).encode("utf-8"), "application/json"

    if fmt.content_type in ("xml", "soap"):
        body = apply_field_map(fmt.field_map, payload) if fmt.field_map else payload
        xml_str = xmltodict.unparse({"root": body}, full_document=False)
        content_type = "text/xml" if fmt.content_type == "soap" else "application/xml"
        return xml_str.encode("utf-8"), content_type

    raise MCPAPIConnectError(f"Unsupported request content_type '{fmt.content_type}'")


def parse_response_body(fmt: ResponseFormat, raw_text: str) -> dict[str, Any]:
    if not raw_text.strip():
        return {}

    if fmt.content_type == "json":
        import json

        try:
            parsed = json.loads(raw_text)
        except ValueError as exc:
            raise MCPAPIConnectError(f"Failed to parse JSON response: {exc}") from exc
    elif fmt.content_type in ("xml", "soap"):
        try:
            parsed = xmltodict.parse(raw_text)
        except Exception as exc:  # xmltodict raises expat errors
            raise MCPAPIConnectError(f"Failed to parse XML/SOAP response: {exc}") from exc
        if fmt.content_type == "soap" and fmt.unwrap_soap_body:
            parsed = _unwrap_soap_envelope(parsed)
    else:
        raise MCPAPIConnectError(f"Unsupported response content_type '{fmt.content_type}'")

    if not isinstance(parsed, dict):
        parsed = {"value": parsed}

    if fmt.field_map:
        return apply_field_map(fmt.field_map, parsed)
    return parsed


def _unwrap_soap_envelope(parsed: dict[str, Any]) -> dict[str, Any]:
    for env_key, env_val in parsed.items():
        if "envelope" in env_key.lower() and isinstance(env_val, dict):
            for body_key, body_val in env_val.items():
                if "body" in body_key.lower() and isinstance(body_val, dict):
                    return body_val
            return env_val
    return parsed
