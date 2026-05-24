from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.schemas.memory import MemoryCreate


class MemoryCoreClient:
    """Client for the official isolated LICI Memory Core service.

    The main LICI flow can use this client before and after strategic analyses
    without coupling the app to the JSON storage implementation.
    """

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 3.0):
        self.base_url = (base_url or settings.memory_core_url).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def buscar(self, termo: str) -> dict[str, Any]:
        query = urlencode({"q": termo})
        return self._get(f"/memoria/buscar?{query}")

    def registrar(self, memoria: MemoryCreate | dict[str, Any]) -> dict[str, Any]:
        payload = memoria.model_dump() if isinstance(memoria, MemoryCreate) else dict(memoria)
        payload = self._normalizar_payload_oficial(payload)
        return self._post("/memoria/registrar", payload)

    def _normalizar_payload_oficial(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Adapta o schema modular ao serviço isolado de memória.

        A API principal usa confiança de 0 a 1; o serviço isolado usa inteiro 0 a
        100. Essa conversão mantém compatibilidade sem alterar APIs existentes.
        """
        payload = dict(payload)
        confianca = payload.get("confianca")
        if isinstance(confianca, float) and 0 <= confianca <= 1:
            payload["confianca"] = round(confianca * 100)
        return payload

    def _get(self, path: str) -> dict[str, Any]:
        request = Request(f"{self.base_url}{path}", method="GET")
        return self._open(request)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._open(request)

    def _open(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {
                "erro": "memory core indisponível",
                "detalhe": str(exc),
                "base_url": self.base_url,
            }
