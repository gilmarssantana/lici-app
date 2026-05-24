from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.decision import MemorySuggestion


class RadarSearchRequest(BaseModel):
    uf: str | None = Field(default=None, min_length=2, max_length=2)
    palavras_chave: list[str] = Field(default_factory=list)
    segmento: str = ""
    data_inicial: date | None = None
    data_final: date | None = None
    codigo_modalidade_contratacao: int | None = None
    limite: int = Field(default=20, ge=1, le=100)
    cliente: str = "prospect"
    salvar: bool = True


class RadarOpportunity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    fonte: str = "PNCP"
    pncp_id: str = ""
    orgao: str = ""
    unidade: str = ""
    uf: str = ""
    objeto: str = ""
    modalidade: str = ""
    valor_estimado: float | None = None
    data_publicacao: str = ""
    data_abertura: str = ""
    data_encerramento: str = ""
    link: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)
    score_preliminar: int = Field(default=50, ge=0, le=100)
    criterios_score: dict[str, int] = Field(default_factory=dict)
    riscos_aparentes: list[str] = Field(default_factory=list)
    oportunidades_estrategicas: list[str] = Field(default_factory=list)
    memorias_relacionadas: list[dict[str, Any]] = Field(default_factory=list)
    memoria_sugerida: MemorySuggestion | None = None
    caso_id: str | None = None
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RadarSearchResponse(BaseModel):
    total: int
    oportunidades: list[RadarOpportunity]
    filtros: RadarSearchRequest
    fonte: str = "PNCP"
    aviso: str = ""


class RadarOpportunityListResponse(BaseModel):
    total: int
    oportunidades: list[RadarOpportunity]


class RadarCreateCaseRequest(BaseModel):
    cliente: str = Field(default="prospect", min_length=1)
    contexto: str = ""


class RadarCreateCaseResponse(BaseModel):
    oportunidade: RadarOpportunity
    caso: dict[str, Any]
    memoria_sugerida: MemorySuggestion | None = None
