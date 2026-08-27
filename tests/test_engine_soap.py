import httpx
import pytest
import respx

from mcp_api_connect.core.engine import MCPAPIConnectEngine
from mcp_api_connect.core.models import (
    AuthSpec,
    AuthType,
    InvokeSpec,
    Protocol,
    RequestFormat,
    ResponseFormat,
    Target,
)

SOAP_RESPONSE = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetOrderResponse>
      <OrderId>A1</OrderId>
      <Status>Shipped</Status>
    </GetOrderResponse>
  </soap:Body>
</soap:Envelope>"""

BODY_TEMPLATE = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetOrder>
      <OrderId>{{ payload.order_id }}</OrderId>
    </GetOrder>
  </soap:Body>
</soap:Envelope>"""


@pytest.mark.asyncio
@respx.mock
async def test_soap_invoke_round_trip():
    route = respx.post("https://legacy.example.com/OrderService").mock(
        return_value=httpx.Response(200, text=SOAP_RESPONSE)
    )

    spec = InvokeSpec(
        target=Target(base_url="https://legacy.example.com", protocol=Protocol.SOAP),
        auth=AuthSpec(type=AuthType.BASIC, config={"username": "u", "password": "p"}),
        request_format=RequestFormat(
            method="POST",
            path="/OrderService",
            content_type="soap",
            body_template=BODY_TEMPLATE,
            soap_action="GetOrder",
        ),
        response_format=ResponseFormat(
            content_type="soap",
            field_map={"orderId": "$.GetOrderResponse.OrderId", "status": "$.GetOrderResponse.Status"},
        ),
    )

    async with MCPAPIConnectEngine() as engine:
        result = await engine.invoke(spec, {"order_id": "A1"})

    assert result.success is True
    assert result.data == {"orderId": "A1", "status": "Shipped"}

    sent = route.calls.last.request
    assert sent.headers["SOAPAction"] == '"GetOrder"'
    assert "Basic" in sent.headers["Authorization"]
    assert b"<OrderId>A1</OrderId>" in sent.content
