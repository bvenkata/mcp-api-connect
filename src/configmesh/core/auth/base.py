from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from configmesh.core.models import AuthSpec


@dataclass
class PreparedAuth:
    """What an AuthStrategy contributes to the outbound request."""

    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)


class AuthStrategy(ABC):
    """One implementation per AuthType. Strategies may need to make their
    own HTTP calls first (e.g. OAuth2 token fetch) — hence async + given
    a shared httpx.AsyncClient to reuse connections."""

    @abstractmethod
    async def prepare(self, auth: AuthSpec, client: httpx.AsyncClient) -> PreparedAuth:
        raise NotImplementedError
