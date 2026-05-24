from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ChatIntent = Literal[
    "caso",
    "edital",
    "memoria",
    "oportunidade",
    "orgao",
    "concorrente",
    "cliente_consultor",
    "peca",
    "decisao",
    "busca_geral",
]


class ChatMessageRequest(BaseModel):
    pergunta: str = Field(..., min_length=1, max_length=4000)
    conversa_id: str | None = None
    contexto: dict[str, Any] | None = None


class ChatFonte(BaseModel):
    modulo: str
    tipo: str
    total: int = 0
    ids: list[str] = Field(default_factory=list)
    status: str = "ok"
    detalhe: str | None = None


class ChatMessageResponse(BaseModel):
    conversa_id: str
    mensagem_id: str
    intencao: ChatIntent
    pergunta: str
    resposta: str
    fontes: list[ChatFonte] = Field(default_factory=list)
    dados: dict[str, Any] = Field(default_factory=dict)
    encontrou_dados: bool
    criado_em: datetime


class ChatHistoryResponse(BaseModel):
    conversa_id: str | None = None
    total: int
    mensagens: list[dict[str, Any]]


class ChatConversationSummary(BaseModel):
    id: str
    titulo: str
    intencao_principal: str | None = None
    total_mensagens: int
    criado_em: datetime
    atualizado_em: datetime


class ChatConversationsResponse(BaseModel):
    total: int
    conversas: list[ChatConversationSummary]
