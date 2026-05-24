from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class RagClient:
    """Cliente leve para a base/RAG local de licitações.

    A integração é best-effort: se a base não estiver online, o Decision Engine
    continua funcionando e sinaliza que a consulta documental ficou pendente.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout_seconds: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def consultar(self, pergunta: str) -> dict[str, Any]:
        payload = {"pergunta": pergunta}
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.base_url}/consultar",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {
                "erro": "base/RAG indisponível",
                "detalhe": str(exc),
                "base_url": self.base_url,
            }
