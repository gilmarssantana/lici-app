from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.decision import MemorySuggestion

CasePhase = Literal[
    "prospecção",
    "análise",
    "impugnação",
    "habilitação",
    "disputa",
    "recurso",
    "homologação",
    "contrato",
    "execução",
    "pagamento",
    "encerrado",
]

CaseStatus = Literal["ativo", "suspenso", "vencido", "perdido", "encerrado", "arquivado"]

CaseEventType = Literal[
    "edital analisado",
    "impugnação enviada",
    "recurso protocolado",
    "concorrente inabilitado",
    "vitória",
    "perda",
    "contrato assinado",
    "pagamento atrasado",
    "reequilíbrio solicitado",
]


class CaseEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    data: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tipo: CaseEventType | str
    fase: CasePhase | str
    descricao: str
    impacto: str = ""
    aprendizado_operacional: str = ""
    memoria_sugerida: MemorySuggestion | None = None


class CaseCreate(BaseModel):
    organization_id: str | None = None
    cliente: str = Field(..., min_length=1)
    orgao: str = Field(..., min_length=1)
    objeto: str = Field(..., min_length=3)
    modalidade: str = ""
    status: CaseStatus = "ativo"
    fase_atual: CasePhase = "prospecção"
    score_estrategico: int = Field(default=50, ge=0, le=100)
    riscos: list[str] = Field(default_factory=list)
    oportunidades: list[str] = Field(default_factory=list)
    memorias_relacionadas: list[dict] = Field(default_factory=list)
    contexto: str = ""
    texto_edital: str | None = None


class CaseUpdate(BaseModel):
    cliente: str | None = None
    orgao: str | None = None
    objeto: str | None = None
    modalidade: str | None = None
    status: CaseStatus | None = None
    fase_atual: CasePhase | None = None
    score_estrategico: int | None = Field(default=None, ge=0, le=100)
    riscos: list[str] | None = None
    oportunidades: list[str] | None = None
    contexto: str | None = None


class CaseRecord(CaseCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    historico_operacional: list[CaseEvent] = Field(default_factory=list)
    memoria_sugerida: MemorySuggestion | None = None


class CaseListResponse(BaseModel):
    total: int
    casos: list[CaseRecord]


class CasePhaseUpdate(BaseModel):
    fase_atual: CasePhase
    status: CaseStatus | None = None
    descricao: str = ""
    aprendizado_operacional: str = ""


class CaseEventCreate(BaseModel):
    tipo: CaseEventType | str
    descricao: str
    impacto: str = ""
    aprendizado_operacional: str = ""
    gerar_memoria_sugerida: bool = True


class CaseTimelineResponse(BaseModel):
    caso_id: str
    total: int
    timeline: list[CaseEvent]
