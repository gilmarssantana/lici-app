from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

NotificationEventType = Literal[
    "oportunidade_prioridade_alta",
    "alerta_critico",
    "risco_concorrencial_alto",
    "falha_backup",
    "healthcheck_erro",
    "prazo_critico",
    "teste",
]


class NotificationSendRequest(BaseModel):
    tipo: NotificationEventType | str
    titulo: str = Field(..., min_length=3, max_length=180)
    mensagem: str = Field(..., min_length=3, max_length=3000)
    referencia_id: str = ""
    severidade: str = "critica"
    canal: str | None = None
    forcar: bool = False
    dry_run: bool = False
    metadata: dict = Field(default_factory=dict)


class NotificationTestRequest(BaseModel):
    canal: str | None = None
    dry_run: bool = True


class NotificationLogRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tipo: str
    titulo: str
    canal: str
    status: str
    destino: str = ""
    referencia_id: str = ""
    dedupe_key: str = ""
    dry_run: bool = False
    erro: str = ""
    metadata: dict = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    status: str
    enviado: bool
    canal: str
    destino: str = ""
    motivo: str = ""
    log: NotificationLogRecord
