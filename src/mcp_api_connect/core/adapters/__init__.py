from mcp_api_connect.core.adapters.base import ProtocolAdapter, RawResponse
from mcp_api_connect.core.adapters.rest import RestAdapter
from mcp_api_connect.core.adapters.soap import SoapAdapter
from mcp_api_connect.core.models import Protocol

DEFAULT_ADAPTER_REGISTRY: dict[Protocol, ProtocolAdapter] = {
    Protocol.REST: RestAdapter(),
    Protocol.SOAP: SoapAdapter(),
}

__all__ = ["DEFAULT_ADAPTER_REGISTRY", "ProtocolAdapter", "RawResponse", "RestAdapter", "SoapAdapter"]
