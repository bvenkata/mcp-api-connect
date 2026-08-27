from mcp_api_connect.core.auth.base import AuthStrategy, PreparedAuth
from mcp_api_connect.core.auth.strategies import (
    ApiKeyAuth,
    BasicAuth,
    BearerAuth,
    NoneAuth,
    OAuth2ClientCredentialsAuth,
)
from mcp_api_connect.core.models import AuthType

DEFAULT_AUTH_REGISTRY: dict[AuthType, AuthStrategy] = {
    AuthType.NONE: NoneAuth(),
    AuthType.API_KEY: ApiKeyAuth(),
    AuthType.BASIC: BasicAuth(),
    AuthType.BEARER: BearerAuth(),
    AuthType.OAUTH2_CLIENT_CREDENTIALS: OAuth2ClientCredentialsAuth(),
}

__all__ = [
    "DEFAULT_AUTH_REGISTRY",
    "ApiKeyAuth",
    "AuthStrategy",
    "BasicAuth",
    "BearerAuth",
    "NoneAuth",
    "OAuth2ClientCredentialsAuth",
    "PreparedAuth",
]
