from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ChatActionType = Literal[
    "criar_caso",
    "gerar_peca",
    "registrar_memoria",
    "analisar_edital",
    "consultar_orgao",
    "criar_demanda_consultor",
    "gerar_checklist",
]

ChatActionStatus = Literal["preview", "pendente", "confirmada", "executada", "cancelada", "erro"]


class ChatActionRequest(BaseModel):
    pergunta: str = Field(default="", max_length=8000)
    acao: ChatActionType | None = None
    parametros: dict[str, Any] = Field(default_factory=dict)
    acao_id: str | None = None
    confirmar: bool = False
    cancelar: bool = False
    conversa_id: str | None = None


class ChatActionResponse(BaseModel):
    acao_id: str
    acao: ChatActionType
    status: ChatActionStatus
    intencao: str
    parametros: dict[str, Any] = Field(default_factory=dict)
    parametros_faltantes: list[str] = Field(default_factory=list)
    previa: str
    requer_confirmacao: bool = True
    resultado: dict[str, Any] | None = None
    erro: str = ""
    fontes: list[str] = Field(default_factory=list)
    criado_em: datetime
    atualizado_em: datetime
