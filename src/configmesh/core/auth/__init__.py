from configmesh.core.auth.base import AuthStrategy, PreparedAuth
from configmesh.core.auth.strategies import (
    ApiKeyAuth,
    BasicAuth,
    BearerAuth,
    NoneAuth,
    OAuth2ClientCredentialsAuth,
)
from configmesh.core.models import AuthType

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
