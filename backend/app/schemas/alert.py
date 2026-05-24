from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

AlertSeverity = Literal["critica", "alta", "media", "baixa"]
AlertSource = Literal["triagem", "radar", "case", "memory"]


class AlertRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    chave: str
    titulo: str
    mensagem: str
    severidade: AlertSeverity
    fonte: AlertSource | str
    referencia_id: str = ""
    orgao: str = ""
    objeto: str = ""
    risco: str = ""
    oportunidade: str = ""
    acao_recomendada: str = ""
    lido: bool = False
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlertListResponse(BaseModel):
    total: int
    nao_lidos: int
    alertas: list[AlertRecord]


class AlertGenerateRequest(BaseModel):
    incluir_lidos: bool = False
    limite_triagem: int = Field(default=200, ge=1, le=1000)
    limite_casos: int = Field(default=200, ge=1, le=1000)


class AlertGenerateLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    iniciado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finalizado_em: str = ""
    status: str = "em_execucao"
    total_gerados: int = 0
    novos: int = 0
    atualizados: int = 0
    critica: int = 0
    alta: int = 0
    media: int = 0
    baixa: int = 0
    erro: str = ""


class AlertGenerateResponse(BaseModel):
    log: AlertGenerateLog
    alertas: list[AlertRecord]


class AlertMarkReadResponse(BaseModel):
    alerta: AlertRecord


class AlertLogsResponse(BaseModel):
    total: int
    logs: list[AlertGenerateLog]
