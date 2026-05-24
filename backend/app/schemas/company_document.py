from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

DocumentScope = Literal['empresa', 'cliente']
DocumentStatus = Literal['válido', 'vencendo', 'vencido', 'pendente', 'inválido', 'arquivado']
Criticality = Literal['baixa', 'media', 'alta', 'critica']

DOCUMENT_TYPES = [
    'contrato_social', 'alteracao_contratual', 'cartao_cnpj', 'certidao', 'balanco',
    'indices_contabeis', 'atestado', 'procuracao', 'alvara', 'iso', 'compliance',
    'declaracao', 'documento_tecnico', 'documento_trabalhista', 'documento_fiscal'
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CompanyDocumentCreate(BaseModel):
    escopo: DocumentScope = 'empresa'
    empresa_id: str | None = None
    empresa_nome: str = ''
    cliente_id: str | None = None
    cliente_nome: str = ''
    tipo_documental: str = Field(..., min_length=2, max_length=120)
    categoria: str = 'habilitação'
    titulo: str = Field(..., min_length=2, max_length=240)
    validade: str | None = None
    orgao_emissor: str = ''
    tags: list[str] = Field(default_factory=list)
    criticidade: Criticality = 'media'
    status: DocumentStatus = 'pendente'
    observacoes: str = ''
    payload: dict[str, Any] = Field(default_factory=dict)
    atestado: dict[str, Any] = Field(default_factory=dict)


class CompanyDocumentUpdate(BaseModel):
    escopo: DocumentScope | None = None
    empresa_id: str | None = None
    empresa_nome: str | None = None
    cliente_id: str | None = None
    cliente_nome: str | None = None
    tipo_documental: str | None = None
    categoria: str | None = None
    titulo: str | None = None
    validade: str | None = None
    orgao_emissor: str | None = None
    tags: list[str] | None = None
    criticidade: Criticality | None = None
    status: DocumentStatus | None = None
    observacoes: str | None = None
    payload: dict[str, Any] | None = None
    atestado: dict[str, Any] | None = None


class CompanyDocument(BaseModel):
    id: str = Field(default_factory=lambda: f'docemp-{uuid4().hex[:12]}')
    organization_id: str = 'default-org'
    escopo: DocumentScope = 'empresa'
    empresa_id: str | None = None
    empresa_nome: str = ''
    cliente_id: str | None = None
    cliente_nome: str = ''
    tipo_documental: str
    categoria: str = 'habilitação'
    titulo: str
    validade: str | None = None
    orgao_emissor: str = ''
    tags: list[str] = Field(default_factory=list)
    criticidade: Criticality = 'media'
    status: DocumentStatus = 'pendente'
    risco_documental: int = 0
    score_documental: int = 0
    arquivo_nome: str | None = None
    arquivo_caminho: str | None = None
    content_type: str = ''
    tamanho_bytes: int = 0
    versao_atual: int = 1
    observacoes: str = ''
    payload: dict[str, Any] = Field(default_factory=dict)
    atestado: dict[str, Any] = Field(default_factory=dict)
    criado_em: datetime = Field(default_factory=now_utc)
    atualizado_em: datetime = Field(default_factory=now_utc)


class CompanyDocumentVersion(BaseModel):
    id: str = Field(default_factory=lambda: f'docver-{uuid4().hex[:12]}')
    organization_id: str = 'default-org'
    document_id: str
    versao: int = 1
    arquivo_nome: str | None = None
    arquivo_caminho: str | None = None
    content_type: str = ''
    tamanho_bytes: int = 0
    criado_em: datetime = Field(default_factory=now_utc)
    payload: dict[str, Any] = Field(default_factory=dict)


class CompanyDocumentAlert(BaseModel):
    id: str = Field(default_factory=lambda: f'docalert-{uuid4().hex[:12]}')
    organization_id: str = 'default-org'
    document_id: str
    empresa_id: str | None = None
    empresa_nome: str = ''
    tipo: str = 'validade'
    severidade: Criticality = 'media'
    status: str = 'ativo'
    mensagem: str
    dias_para_vencer: int | None = None
    criado_em: datetime = Field(default_factory=now_utc)
    resolvido_em: str | None = None


class CompanyDocumentListResponse(BaseModel):
    itens: list[CompanyDocument]
    total: int


class CompanyDocumentDashboard(BaseModel):
    total_documentos: int
    documentos_vencendo: int
    documentos_vencidos: int
    empresas_em_risco: int
    score_documental_medio: float
    alertas_criticos: int
    atestados_estrategicos: int
    por_status: dict[str, int]
    por_tipo: dict[str, int]
    documentos_criticos: list[CompanyDocument]
    alertas: list[CompanyDocumentAlert]


class CompanyDossier(BaseModel):
    empresa_id: str | None = None
    empresa_nome: str
    documentos_validos: int
    pendencias: int
    riscos: int
    vencimentos: list[CompanyDocument]
    capacidade_tecnica: list[CompanyDocument]
    score_documental: int
    aptidao_licitatoria: str
    documentos: list[CompanyDocument]


class CompanyChecklistRequest(BaseModel):
    empresa_id: str | None = None
    empresa_nome: str = ''
    edital_texto: str = ''
    upload_document_id: str | None = None
    tipos_exigidos: list[str] = Field(default_factory=list)


class CompanyChecklistResponse(BaseModel):
    empresa_nome: str
    exigidos: list[str]
    presentes: list[str]
    faltantes: list[str]
    vencidos: list[str]
    risco_inabilitacao: str
    sugestoes_regularizacao: list[str]
    score_documental: int
