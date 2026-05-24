from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

OrgaoEventType = Literal[
    "edital publicado",
    "impugnação deferida",
    "impugnação indeferida",
    "recurso acolhido",
    "recurso negado",
    "pagamento atrasado",
    "contrato bem executado",
    "exigência restritiva",
    "concorrência baixa",
    "concorrência alta",
]

OrgaoRisk = Literal["baixo", "médio", "alto", "crítico", "desconhecido"]


class OrgaoCreate(BaseModel):
    organization_id: str | None = None
    nome: str = Field(..., min_length=2)
    cnpj: str = ""
    uf: str = ""
    esfera: str = ""
    risco: OrgaoRisk | str = "desconhecido"
    comportamento: str = ""
    exigencias_recorrentes: list[str] = Field(default_factory=list)
    historico_impugnacoes: list[str] = Field(default_factory=list)
    historico_pagamento: list[str] = Field(default_factory=list)
    padrao_julgamento: str = ""
    observacoes_estrategicas: str = ""
    score_confiabilidade: int = Field(default=50, ge=0, le=100)
    score_oportunidade: int = Field(default=50, ge=0, le=100)
    metadata: dict = Field(default_factory=dict)


class OrgaoUpdate(BaseModel):
    nome: str | None = None
    cnpj: str | None = None
    uf: str | None = None
    esfera: str | None = None
    risco: OrgaoRisk | str | None = None
    comportamento: str | None = None
    exigencias_recorrentes: list[str] | None = None
    historico_impugnacoes: list[str] | None = None
    historico_pagamento: list[str] | None = None
    padrao_julgamento: str | None = None
    observacoes_estrategicas: str | None = None
    score_confiabilidade: int | None = Field(default=None, ge=0, le=100)
    score_oportunidade: int | None = Field(default=None, ge=0, le=100)
    metadata: dict | None = None


class OrgaoRecord(OrgaoCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OrgaoEventCreate(BaseModel):
    organization_id: str | None = None
    tipo: OrgaoEventType | str
    descricao: str = Field(..., min_length=3)
    impacto: str = ""
    caso_id: str | None = None
    radar_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class OrgaoEvent(OrgaoEventCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    orgao_id: str
    data: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OrgaoListResponse(BaseModel):
    total: int
    orgaos: list[OrgaoRecord]


class OrgaoHistoricoResponse(BaseModel):
    orgao_id: str
    total: int
    eventos: list[OrgaoEvent]
