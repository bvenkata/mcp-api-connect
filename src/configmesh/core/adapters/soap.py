from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx

from configmesh.core.adapters.base import ProtocolAdapter, RawResponse
from configmesh.core.auth.base import PreparedAuth
from configmesh.core.models import ConfigMeshError, RequestFormat, Target
from configmesh.core.transform import render_request_body


class SoapAdapter(ProtocolAdapter):
    """v1 SOAP support: caller supplies a Jinja2 `body_template` that renders
    the full SOAP envelope from `payload`. No WSDL introspection yet — that's
    a natural fast-follow (see README roadmap) via the optional `zeep` extra.
    """

    async def execute(
        self,
        target: Target,
        request_format: RequestFormat,
        auth: PreparedAuth,
        payload: dict[str, Any],
        client: httpx.AsyncClient,
    ) -> RawResponse:
        if not request_format.body_template:
            raise ConfigMeshError(
                "SOAP requests require request_format.body_template (a Jinja2 template "
                "rendering the full <soap:Envelope>)."
            )

        url = urljoin(target.base_url.rstrip("/") + "/", request_format.path.lstrip("/"))
        body, content_type = render_request_body(request_format, payload)

        headers = {**target.default_headers, **request_format.headers, **auth.headers}
        headers.setdefault("Content-Type", f"{content_type}; charset=utf-8")
        if request_format.soap_action:
            headers.setdefault("SOAPAction", f'"{request_format.soap_action}"')

        resp = await client.request(
            request_format.method.upper() or "POST",
            url,
            headers=headers,
            params=auth.params or None,
            content=body,
            timeout=target.timeout_seconds,
        )
        return RawResponse(status_code=resp.status_code, headers=dict(resp.headers), text=resp.text)
