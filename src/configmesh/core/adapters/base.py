from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from configmesh.core.auth.base import PreparedAuth
from configmesh.core.models import RequestFormat, Target


@dataclass
class RawResponse:
    status_code: int
    headers: dict[str, str]
    text: str


class ProtocolAdapter(ABC):
    @abstractmethod
    async def execute(
        self,
        target: Target,
        request_format: RequestFormat,
        auth: PreparedAuth,
        payload: dict[str, Any],
        client: httpx.AsyncClient,
    ) -> RawResponse:
        raise NotImplementedError
