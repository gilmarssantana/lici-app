from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

AUDIT_DIR = Path("/root/lici-app/audit")
AUDIT_LOG_FILE = AUDIT_DIR / "audit.log"


class LiciAuditLog:
    """Serviço interno de auditoria operacional da LICI.

    O arquivo é JSON Lines para preservar escrita simples, leitura incremental
    e compatibilidade com tail/grep mesmo quando o banco estiver indisponível.
    """

    def __init__(self, log_file: Path | str = AUDIT_LOG_FILE):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.touch(exist_ok=True)

    def registrar(
        self,
        modulo: str,
        acao: str,
        status: str,
        detalhes: dict[str, Any] | str | None = None,
        id_relacionado: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modulo": modulo,
            "acao": acao,
            "status": status,
            "detalhes": self._normalizar_detalhes(detalhes),
            "id_relacionado": id_relacionado,
        }
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        return event

    def listar(self, limite: int = 200, modulo: str | None = None, acao: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        limite = max(1, min(limite, 1000))
        if not self.log_file.exists():
            return []

        eventos: list[dict[str, Any]] = []
        with self.log_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    event = {
                        "id": None,
                        "timestamp": None,
                        "modulo": "audit",
                        "acao": "linha_invalida",
                        "status": "erro",
                        "detalhes": {"linha": line},
                        "id_relacionado": None,
                    }
                if modulo and event.get("modulo") != modulo:
                    continue
                if acao and event.get("acao") != acao:
                    continue
                if status and event.get("status") != status:
                    continue
                eventos.append(event)

        return list(reversed(eventos[-limite:]))

    def _normalizar_detalhes(self, detalhes: dict[str, Any] | str | None) -> dict[str, Any]:
        if detalhes is None:
            return {}
        if isinstance(detalhes, dict):
            return detalhes
        return {"mensagem": str(detalhes)}


def audit_event(
    modulo: str,
    acao: str,
    status: str,
    detalhes: dict[str, Any] | str | None = None,
    id_relacionado: str | None = None,
) -> None:
    """Registra evento sem quebrar o fluxo principal em caso de falha."""
    try:
        LiciAuditLog().registrar(modulo, acao, status, detalhes, id_relacionado)
    except Exception:
        # Auditoria nunca deve derrubar endpoints operacionais existentes.
        pass
