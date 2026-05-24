from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

FornecedorTipo = Literal['contrato', 'execucao', 'financeiro', 'risco']


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class FornecedorRecordCreate(BaseModel):
    tipo: FornecedorTipo
    titulo: str = Field(..., min_length=2, max_length=220)
    orgao: str = ''
    contrato_id: str | None = None
    caso_id: str | None = None
    status: str = 'ativo'
    prioridade: str = 'media'
    valor: float = 0
    data_inicio: str | None = None
    data_fim: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    observacoes: str = ''


class FornecedorRecordUpdate(BaseModel):
    titulo: str | None = None
    orgao: str | None = None
    contrato_id: str | None = None
    caso_id: str | None = None
    status: str | None = None
    prioridade: str | None = None
    valor: float | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    payload: dict[str, Any] | None = None
    observacoes: str | None = None


class FornecedorRecord(BaseModel):
    id: str = Field(default_factory=lambda: f'forn-{uuid4().hex[:12]}')
    organization_id: str = 'default-org'
    tipo: FornecedorTipo
    titulo: str
    orgao: str = ''
    contrato_id: str | None = None
    caso_id: str | None = None
    status: str = 'ativo'
    prioridade: str = 'media'
    valor: float = 0
    risco_score: int = 0
    margem_operacional: float = 0
    data_inicio: str | None = None
    data_fim: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    observacoes: str = ''
    criado_em: datetime = Field(default_factory=now_utc)
    atualizado_em: datetime = Field(default_factory=now_utc)


class FornecedorListResponse(BaseModel):
    itens: list[FornecedorRecord]
    total: int


class FornecedorDashboardResponse(BaseModel):
    contratos_ativos: int
    pagamentos_pendentes: int
    risco_contratual_medio: float
    margem_operacional_media: float
    orgaos_criticos: list[dict[str, Any]]
    por_tipo: dict[str, int]
    por_status: dict[str, int]
    proximas_renovacoes: list[FornecedorRecord]
    pendencias_execucao: list[FornecedorRecord]
    financeiro: dict[str, float]
