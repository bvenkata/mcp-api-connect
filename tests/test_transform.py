from configmesh.core.models import ResponseFormat
from configmesh.core.transform import apply_field_map, parse_response_body


def test_apply_field_map_simple():
    source = {"order": {"id": "A1", "customer": {"email": "a@example.com"}}}
    field_map = {
        "orderId": "$.order.id",
        "customer.email": "$.order.customer.email",
    }
    result = apply_field_map(field_map, source)
    assert result == {"orderId": "A1", "customer": {"email": "a@example.com"}}


def test_apply_field_map_missing_path_is_skipped():
    result = apply_field_map({"x": "$.does.not.exist"}, {"a": 1})
    assert result == {}


def test_parse_response_body_json_passthrough():
    fmt = ResponseFormat(content_type="json")
    result = parse_response_body(fmt, '{"status": "ok", "id": 42}')
    assert result == {"status": "ok", "id": 42}


def test_parse_response_body_json_with_field_map():
    fmt = ResponseFormat(content_type="json", field_map={"orderId": "$.id"})
    result = parse_response_body(fmt, '{"id": 42, "noise": true}')
    assert result == {"orderId": 42}


def test_parse_response_body_soap_unwraps_envelope():
    xml = """
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetOrderResponse>
          <OrderId>A1</OrderId>
        </GetOrderResponse>
      </soap:Body>
    </soap:Envelope>
    """
    fmt = ResponseFormat(content_type="soap", field_map={"orderId": "$.GetOrderResponse.OrderId"})
    result = parse_response_body(fmt, xml)
    assert result == {"orderId": "A1"}
