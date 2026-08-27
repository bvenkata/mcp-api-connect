from configmesh.core.adapters.base import ProtocolAdapter, RawResponse
from configmesh.core.adapters.rest import RestAdapter
from configmesh.core.adapters.soap import SoapAdapter
from configmesh.core.models import Protocol

DEFAULT_ADAPTER_REGISTRY: dict[Protocol, ProtocolAdapter] = {
    Protocol.REST: RestAdapter(),
    Protocol.SOAP: SoapAdapter(),
}

__all__ = ["DEFAULT_ADAPTER_REGISTRY", "ProtocolAdapter", "RawResponse", "RestAdapter", "SoapAdapter"]
