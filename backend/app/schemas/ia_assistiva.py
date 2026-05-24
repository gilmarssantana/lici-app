from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

AssistiveKind = Literal['resumo', 'explicacao', 'sugestao', 'chat']
AssistiveFocus = Literal[
    'cliente', 'caso', 'edital', 'concorrencial', 'documental', 'operacional',
    'risco', 'pendencia', 'decisao', 'score', 'inaptidao_documental', 'proxima_acao',
    'follow_up', 'regularizacao', 'prioridade', 'sugestao_operacional'
]
FeedbackKind = Literal['aceita', 'ignorada', 'util', 'insuficiente']


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AssistiveRequest(BaseModel):
    tipo: AssistiveKind = 'chat'
    foco: AssistiveFocus = 'operacional'
    pergunta: str = Field('', max_length=4000)
    termo: str = Field('', max_length=300)
    caso_id: str | None = None
    cliente_id: str | None = None
    cliente_nome: str = ''
    empresa_id: str | None = None
    empresa_nome: str = ''
    edital_texto: str = Field('', max_length=12000)
    incluir_dados: bool = True


class AssistiveSource(BaseModel):
    modulo: str
    tipo: str
    total: int = 0
    ids: list[str] = Field(default_factory=list)
    origem: str = 'interna'
    status: str = 'ok'
    detalhe: str = ''


class AssistiveSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: f'sug-{uuid4().hex[:12]}')
    tipo: str
    titulo: str
    descricao: str
    prioridade: str = 'media'
    supervisionada: bool = True
    executa_automaticamente: bool = False
    motivo: str = ''


class AssistiveResponse(BaseModel):
    id: str = Field(default_factory=lambda: f'iactx-{uuid4().hex[:12]}')
    tipo: AssistiveKind
    foco: AssistiveFocus
    pergunta: str = ''
    resposta: str
    resumo: list[str] = Field(default_factory=list)
    explicacoes: list[str] = Field(default_factory=list)
    sugestoes: list[AssistiveSuggestion] = Field(default_factory=list)
    fontes: list[AssistiveSource] = Field(default_factory=list)
    dados_contexto: dict[str, Any] = Field(default_factory=dict)
    confianca: float = Field(default=0, ge=0, le=1)
    contexto_isolado_por_org: bool = True
    supervisionada: bool = True
    executa_automaticamente: bool = False
    criado_em: datetime = Field(default_factory=now_utc)


class AssistiveFeedbackRequest(BaseModel):
    resposta_id: str
    feedback: FeedbackKind
    comentario: str = Field('', max_length=1000)


class AssistiveTelemetryRecord(BaseModel):
    id: str = Field(default_factory=lambda: f'iatelem-{uuid4().hex[:12]}')
    organization_id: str = 'default-org'
    resposta_id: str = ''
    tipo: str = ''
    foco: str = ''
    confianca: float = 0
    feedback: str | None = None
    comentario: str = ''
    usuario_id: str | None = None
    criado_em: datetime = Field(default_factory=now_utc)


class AssistiveTelemetrySummary(BaseModel):
    total_respostas: int = 0
    sugestoes_aceitas: int = 0
    sugestoes_ignoradas: int = 0
    respostas_uteis: int = 0
    respostas_insuficientes: int = 0
    confianca_media: float = 0
    por_foco: dict[str, int] = Field(default_factory=dict)
