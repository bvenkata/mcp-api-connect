from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx

from mcp_api_connect.core.adapters.base import ProtocolAdapter, RawResponse
from mcp_api_connect.core.auth.base import PreparedAuth
from mcp_api_connect.core.models import RequestFormat, Target
from mcp_api_connect.core.transform import render_request_body


class RestAdapter(ProtocolAdapter):
    async def execute(
        self,
        target: Target,
        request_format: RequestFormat,
        auth: PreparedAuth,
        payload: dict[str, Any],
        client: httpx.AsyncClient,
    ) -> RawResponse:
        url = urljoin(target.base_url.rstrip("/") + "/", request_format.path.lstrip("/"))

        headers = {**target.default_headers, **request_format.headers, **auth.headers}
        method = request_format.method.upper()

        content: bytes | None = None
        if method in ("POST", "PUT", "PATCH", "DELETE") or payload:
            content, content_type = render_request_body(request_format, payload)
            headers.setdefault("Content-Type", content_type)

        resp = await client.request(
            method,
            url,
            headers=headers,
            params=auth.params or None,
            content=content,
            timeout=target.timeout_seconds,
        )
        return RawResponse(status_code=resp.status_code, headers=dict(resp.headers), text=resp.text)
