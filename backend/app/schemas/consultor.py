from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ClientStatus = Literal["prospect", "ativo", "pausado", "encerrado", "inadimplente"]
DemandType = Literal["edital", "impugnação", "recurso", "habilitação", "proposta", "contrato", "cobrança"]
DemandPriority = Literal["baixa", "média", "alta", "crítica"]
DemandStatus = Literal["aberta", "em andamento", "aguardando cliente", "entregue", "cancelada", "atrasada"]


class ConsultorClienteCreate(BaseModel):
    organization_id: str | None = None
    nome: str = Field(..., min_length=2)
    documento: str = ""
    segmento: str = ""
    uf: str = ""
    contatos: list[str] = Field(default_factory=list)
    observacoes: str = ""
    status: ClientStatus | str = "prospect"
    score_potencial: int = Field(default=50, ge=0, le=100)
    metadata: dict = Field(default_factory=dict)


class ConsultorClienteRecord(ConsultorClienteCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConsultorDemandaCreate(BaseModel):
    organization_id: str | None = None
    tipo: DemandType | str
    descricao: str = Field(..., min_length=3)
    prazo: str = ""
    prioridade: DemandPriority | str = "média"
    status: DemandStatus | str = "aberta"
    caso_vivo_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class ConsultorDemandaRecord(ConsultorDemandaCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    cliente_id: str
    cliente_nome: str = ""
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConsultorDemandaStatusUpdate(BaseModel):
    status: DemandStatus | str
    observacao: str = ""


class ConsultorClientesResponse(BaseModel):
    total: int
    clientes: list[ConsultorClienteRecord]


class ConsultorDemandasResponse(BaseModel):
    total: int
    demandas: list[ConsultorDemandaRecord]


class ConsultorClienteDetalheResponse(BaseModel):
    cliente: ConsultorClienteRecord
    demandas: list[ConsultorDemandaRecord]
    casos_relacionados: list[dict] = Field(default_factory=list)
