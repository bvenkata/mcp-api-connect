import httpx
import pytest
import respx

from configmesh.core.engine import ConfigMeshEngine
from configmesh.core.models import (
    AuthSpec,
    AuthType,
    InvokeSpec,
    Protocol,
    RequestFormat,
    ResponseFormat,
    Target,
)


@pytest.mark.asyncio
@respx.mock
async def test_rest_invoke_with_api_key_auth():
    route = respx.post("https://api.example.com/v1/orders").mock(
        return_value=httpx.Response(200, json={"id": "A1", "status": "created"})
    )

    spec = InvokeSpec(
        target=Target(base_url="https://api.example.com", protocol=Protocol.REST),
        auth=AuthSpec(type=AuthType.API_KEY, config={"api_key": "secret123", "header_name": "X-API-Key"}),
        request_format=RequestFormat(method="POST", path="/v1/orders", content_type="json"),
        response_format=ResponseFormat(content_type="json"),
    )

    async with ConfigMeshEngine() as engine:
        result = await engine.invoke(spec, {"customer": "jane"})

    assert result.success is True
    assert result.status_code == 200
    assert result.data == {"id": "A1", "status": "created"}

    sent = route.calls.last.request
    assert sent.headers["X-API-Key"] == "secret123"


@pytest.mark.asyncio
@respx.mock
async def test_rest_invoke_with_field_mapping():
    respx.post("https://api.example.com/v1/orders").mock(
        return_value=httpx.Response(200, json={"orderId": "A1"})
    )

    spec = InvokeSpec(
        target=Target(base_url="https://api.example.com"),
        auth=AuthSpec(type=AuthType.NONE),
        request_format=RequestFormat(
            method="POST",
            path="/v1/orders",
            content_type="json",
            field_map={"customer_name": "$.customer.name"},
        ),
        response_format=ResponseFormat(content_type="json", field_map={"id": "$.orderId"}),
    )

    async with ConfigMeshEngine() as engine:
        result = await engine.invoke(spec, {"customer": {"name": "Jane Doe"}})

    assert result.success is True
    assert result.data == {"id": "A1"}

    sent_body = respx.calls.last.request.content
    assert b"customer_name" in sent_body
    assert b"Jane Doe" in sent_body


@pytest.mark.asyncio
@respx.mock
async def test_rest_invoke_error_status_marks_unsuccessful():
    respx.post("https://api.example.com/v1/orders").mock(
        return_value=httpx.Response(500, json={"error": "boom"})
    )

    spec = InvokeSpec(
        target=Target(base_url="https://api.example.com"),
        request_format=RequestFormat(method="POST", path="/v1/orders"),
    )

    async with ConfigMeshEngine() as engine:
        result = await engine.invoke(spec, {})

    assert result.success is False
    assert result.status_code == 500


@pytest.mark.asyncio
async def test_oauth2_client_credentials_fetches_and_attaches_token():
    with respx.mock:
        respx.post("https://auth.example.com/token").mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )
        api_route = respx.post("https://api.example.com/v1/orders").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        spec = InvokeSpec(
            target=Target(base_url="https://api.example.com"),
            auth=AuthSpec(
                type=AuthType.OAUTH2_CLIENT_CREDENTIALS,
                config={
                    "token_url": "https://auth.example.com/token",
                    "client_id": "cid",
                    "client_secret": "csecret",
                },
            ),
            request_format=RequestFormat(method="POST", path="/v1/orders"),
        )

        async with ConfigMeshEngine() as engine:
            result = await engine.invoke(spec, {})

        assert result.success is True
        assert api_route.calls.last.request.headers["Authorization"] == "Bearer tok-abc"
