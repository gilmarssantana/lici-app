from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ConsultorFullTipo = Literal['lead', 'agenda', 'tarefa', 'financeiro', 'portal', 'carteira']
LeadStatus = Literal['novo', 'contato', 'diagnóstico', 'proposta', 'negociação', 'ganho', 'perdido', 'arquivado']
PipelineEtapa = Literal['Lead', 'Diagnóstico', 'Proposta', 'Negociação', 'Cliente', 'Operação', 'Recorrência']
ClassificacaoCliente = Literal['A', 'B', 'C']
Prioridade = Literal['baixa', 'media', 'alta', 'critica']


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ConsultorFullRecordCreate(BaseModel):
    tipo: ConsultorFullTipo
    titulo: str = Field(..., min_length=2, max_length=220)
    cliente_id: str | None = None
    cliente_nome: str = ''
    status: str = 'ativo'
    etapa: str = ''
    prioridade: str = 'media'
    responsavel: str = ''
    valor: float = 0
    data: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    observacoes: str = ''


class ConsultorFullRecordUpdate(BaseModel):
    titulo: str | None = None
    cliente_id: str | None = None
    cliente_nome: str | None = None
    status: str | None = None
    etapa: str | None = None
    prioridade: str | None = None
    responsavel: str | None = None
    valor: float | None = None
    data: str | None = None
    payload: dict[str, Any] | None = None
    observacoes: str | None = None


class ConsultorFullRecord(BaseModel):
    id: str = Field(default_factory=lambda: f'cons-{uuid4().hex[:12]}')
    organization_id: str = 'default-org'
    tipo: ConsultorFullTipo
    titulo: str
    cliente_id: str | None = None
    cliente_nome: str = ''
    status: str = 'ativo'
    etapa: str = ''
    prioridade: str = 'media'
    responsavel: str = ''
    valor: float = 0
    score: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)
    data: str | None = None
    observacoes: str = ''
    criado_em: datetime = Field(default_factory=now_utc)
    atualizado_em: datetime = Field(default_factory=now_utc)


class ConsultorLeadCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=220)
    empresa: str = ''
    cliente_id: str | None = None
    origem: str = 'manual'
    status: LeadStatus = 'novo'
    estagio_comercial: LeadStatus = 'novo'
    pipeline_etapa: PipelineEtapa = 'Lead'
    follow_up_em: str | None = None
    responsavel: str = ''
    potencial: float = 0
    ticket_medio: float = 0
    recorrencia: float = 0
    risco_churn: int = Field(default=0, ge=0, le=100)
    lucratividade: float = 0
    orgaos_prioritarios: list[str] = Field(default_factory=list)
    classificacao: ClassificacaoCliente = 'C'
    historico_comercial: list[dict[str, Any]] = Field(default_factory=list)
    observacoes: str = ''
    payload: dict[str, Any] = Field(default_factory=dict)


class ConsultorLeadUpdate(BaseModel):
    nome: str | None = None
    empresa: str | None = None
    cliente_id: str | None = None
    origem: str | None = None
    status: LeadStatus | None = None
    estagio_comercial: LeadStatus | None = None
    pipeline_etapa: PipelineEtapa | None = None
    follow_up_em: str | None = None
    responsavel: str | None = None
    potencial: float | None = None
    ticket_medio: float | None = None
    recorrencia: float | None = None
    risco_churn: int | None = Field(default=None, ge=0, le=100)
    lucratividade: float | None = None
    orgaos_prioritarios: list[str] | None = None
    classificacao: ClassificacaoCliente | None = None
    historico_comercial: list[dict[str, Any]] | None = None
    observacoes: str | None = None
    payload: dict[str, Any] | None = None


class ConsultorLead(BaseModel):
    id: str = Field(default_factory=lambda: f'lead-{uuid4().hex[:12]}')
    organization_id: str = 'default-org'
    nome: str
    empresa: str = ''
    cliente_id: str | None = None
    origem: str = 'manual'
    status: LeadStatus = 'novo'
    estagio_comercial: LeadStatus = 'novo'
    pipeline_etapa: PipelineEtapa = 'Lead'
    follow_up_em: str | None = None
    responsavel: str = ''
    potencial: float = 0
    ticket_medio: float = 0
    recorrencia: float = 0
    risco_churn: int = 0
    lucratividade: float = 0
    orgaos_prioritarios: list[str] = Field(default_factory=list)
    classificacao: ClassificacaoCliente = 'C'
    score_cliente: int = 0
    historico_comercial: list[dict[str, Any]] = Field(default_factory=list)
    observacoes: str = ''
    payload: dict[str, Any] = Field(default_factory=dict)
    criado_em: datetime = Field(default_factory=now_utc)
    atualizado_em: datetime = Field(default_factory=now_utc)


class ConsultorFollowupCreate(BaseModel):
    lead_id: str | None = None
    cliente_id: str | None = None
    cliente_nome: str = ''
    titulo: str = Field(..., min_length=2, max_length=220)
    tipo: str = 'follow-up'
    status: str = 'pendente'
    data: str | None = None
    responsavel: str = ''
    prioridade: Prioridade = 'media'
    sla_horas: int = Field(default=24, ge=0)
    resultado: str = ''
    payload: dict[str, Any] = Field(default_factory=dict)


class ConsultorFollowupUpdate(BaseModel):
    lead_id: str | None = None
    cliente_id: str | None = None
    cliente_nome: str | None = None
    titulo: str | None = None
    tipo: str | None = None
    status: str | None = None
    data: str | None = None
    responsavel: str | None = None
    prioridade: Prioridade | None = None
    sla_horas: int | None = Field(default=None, ge=0)
    resultado: str | None = None
    payload: dict[str, Any] | None = None


class ConsultorFollowup(BaseModel):
    id: str = Field(default_factory=lambda: f'fol-{uuid4().hex[:12]}')
    organization_id: str = 'default-org'
    lead_id: str | None = None
    cliente_id: str | None = None
    cliente_nome: str = ''
    titulo: str
    tipo: str = 'follow-up'
    status: str = 'pendente'
    data: str | None = None
    responsavel: str = ''
    prioridade: Prioridade = 'media'
    sla_horas: int = 24
    resultado: str = ''
    payload: dict[str, Any] = Field(default_factory=dict)
    criado_em: datetime = Field(default_factory=now_utc)
    atualizado_em: datetime = Field(default_factory=now_utc)


class ConsultorFullListResponse(BaseModel):
    itens: list[ConsultorFullRecord]
    total: int


class ConsultorLeadListResponse(BaseModel):
    itens: list[ConsultorLead]
    total: int


class ConsultorFollowupListResponse(BaseModel):
    itens: list[ConsultorFollowup]
    total: int


class ConsultorFullDashboardResponse(BaseModel):
    leads_abertos: int
    leads_ativos: int = 0
    conversao: float = 0
    clientes_ativos: int
    clientes_risco: int = 0
    tarefas_pendentes: int
    receita_prevista: float
    faturamento: float = 0
    inadimplencia: float
    ticket_medio: float
    produtividade: dict[str, Any] = Field(default_factory=dict)
    por_tipo: dict[str, int]
    pipeline: dict[str, int]
    pipeline_comercial: dict[str, int] = Field(default_factory=dict)
    carteira: dict[str, int]
    agenda_proxima: list[ConsultorFullRecord]
    tarefas: list[ConsultorFullRecord]
    followups: list[ConsultorFollowup] = Field(default_factory=list)
    central_clientes: list[dict[str, Any]]
