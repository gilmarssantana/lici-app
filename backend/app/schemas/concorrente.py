from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

CompetitorEventType = Literal[
    "participou",
    "venceu",
    "perdeu",
    "inabilitado",
    "recurso",
    "impugnação",
    "abandono",
    "comportamento agressivo",
    "preço muito baixo",
    "padrão documental",
    "vínculo com órgão",
    "vínculo com caso",
]
RiskLevel = Literal["baixo", "médio", "alto", "crítico", "desconhecido"]


class ConcorrenteCreate(BaseModel):
    organization_id: str | None = None
    nome: str = Field(..., min_length=2)
    cnpj: str = ""
    segmento: str = ""
    uf: str = ""
    observacoes_estrategicas: str = ""
    risco_operacional: RiskLevel | str = "desconhecido"
    padroes_documentais: list[str] = Field(default_factory=list)
    padroes_preco: list[str] = Field(default_factory=list)
    orgaos_relacionados: list[str] = Field(default_factory=list)
    casos_relacionados: list[str] = Field(default_factory=list)
    frequencia: int = Field(default=0, ge=0)
    vitorias: int = Field(default=0, ge=0)
    derrotas: int = Field(default=0, ge=0)
    inabilitacoes: int = Field(default=0, ge=0)
    recursos: int = Field(default=0, ge=0)
    impugnacoes: int = Field(default=0, ge=0)
    score_risco: int = Field(default=50, ge=0, le=100)
    score_competitividade: int = Field(default=50, ge=0, le=100)
    metadata: dict = Field(default_factory=dict)


class ConcorrenteUpdate(BaseModel):
    nome: str | None = None
    cnpj: str | None = None
    segmento: str | None = None
    uf: str | None = None
    observacoes_estrategicas: str | None = None
    risco_operacional: RiskLevel | str | None = None
    padroes_documentais: list[str] | None = None
    padroes_preco: list[str] | None = None
    orgaos_relacionados: list[str] | None = None
    casos_relacionados: list[str] | None = None
    frequencia: int | None = Field(default=None, ge=0)
    vitorias: int | None = Field(default=None, ge=0)
    derrotas: int | None = Field(default=None, ge=0)
    inabilitacoes: int | None = Field(default=None, ge=0)
    recursos: int | None = Field(default=None, ge=0)
    impugnacoes: int | None = Field(default=None, ge=0)
    score_risco: int | None = Field(default=None, ge=0, le=100)
    score_competitividade: int | None = Field(default=None, ge=0, le=100)
    metadata: dict | None = None


class ConcorrenteRecord(ConcorrenteCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConcorrenteEventCreate(BaseModel):
    organization_id: str | None = None
    tipo: CompetitorEventType | str
    descricao: str = Field(..., min_length=3)
    orgao: str = ""
    caso_id: str | None = None
    radar_id: str | None = None
    valor_proposta: float | None = None
    impacto: str = ""
    metadata: dict = Field(default_factory=dict)


class ConcorrenteEvent(ConcorrenteEventCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    concorrente_id: str
    data: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConcorrenteListResponse(BaseModel):
    total: int
    concorrentes: list[ConcorrenteRecord]


class ConcorrenteHistoricoResponse(BaseModel):
    concorrente_id: str
    total: int
    eventos: list[ConcorrenteEvent]


class ConcorrenteAnaliseResponse(BaseModel):
    total_concorrentes: int
    total_eventos: int
    ranking_concorrentes: list[dict] = Field(default_factory=list)
    orgaos_mais_disputados: list[dict] = Field(default_factory=list)
    padroes_risco: list[dict] = Field(default_factory=list)
    padroes_preco: list[dict] = Field(default_factory=list)
    risco_operacional: dict = Field(default_factory=dict)
    dashboard: dict = Field(default_factory=dict)
