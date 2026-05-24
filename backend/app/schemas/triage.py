from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.decision import MemorySuggestion
from app.schemas.radar import RadarOpportunity

TriageClassification = Literal["prioridade_alta", "analisar", "monitorar", "descartar"]
TriageStatus = Literal["pendente", "marcado", "caso_criado", "descartado", "monitorando"]


class TriageItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    oportunidade_id: str
    pncp_id: str = ""
    orgao: str = ""
    uf: str = ""
    objeto: str = ""
    modalidade: str = ""
    valor_estimado: float | None = None
    data_encerramento: str = ""
    score_preliminar: int = Field(default=50, ge=0, le=100)
    classificacao: TriageClassification
    justificativa: str
    risco_aparente: str
    oportunidade_estrategica: str
    sugerir_criacao_caso: bool = False
    acao_recomendada: str = ""
    status: TriageStatus = "pendente"
    marcado_como: str = ""
    observacao: str = ""
    memoria_sugerida: MemorySuggestion | None = None
    oportunidade: RadarOpportunity | None = None
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TriageQueueResponse(BaseModel):
    total: int
    itens: list[TriageItem]


class TriageRunRequest(BaseModel):
    incluir_oportunidade_com_caso: bool = False
    limite: int = Field(default=100, ge=1, le=500)


class TriageRunLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    iniciado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finalizado_em: str = ""
    status: str = "em_execucao"
    total_lidas: int = 0
    total_classificadas: int = 0
    prioridade_alta: int = 0
    analisar: int = 0
    monitorar: int = 0
    descartar: int = 0
    erro: str = ""


class TriageRunResponse(BaseModel):
    log: TriageRunLog
    fila: list[TriageItem]


class TriageMarkRequest(BaseModel):
    status: TriageStatus | None = None
    marcado_como: str = ""
    observacao: str = ""
    criar_caso: bool = False
    cliente: str = "prospect-triagem"


class TriageMarkResponse(BaseModel):
    item: TriageItem
    caso: dict[str, Any] | None = None


class TriageLogsResponse(BaseModel):
    total: int
    logs: list[TriageRunLog]
