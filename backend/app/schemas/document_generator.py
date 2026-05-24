from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

DocumentType = Literal["impugnacao", "recurso", "contrarrazoes"]


class DocumentGenerateRequest(BaseModel):
    organization_id: str | None = None
    analise: dict[str, Any] | None = None
    case_id: str | None = None
    documento_id: str | None = None
    cliente: str = ""
    orgao: str = ""
    processo: str = ""
    modalidade: str = ""
    objeto: str = ""
    recorrente: str = ""
    recorrido: str = ""
    autoridade: str = "Pregoeiro(a)/Agente de Contratação/Comissão de Contratação"
    fatos: str = ""
    tese_principal: str = ""
    pedidos: list[str] = Field(default_factory=list)
    fundamentos: list[str] = Field(default_factory=list)
    contexto: str = ""
    registrar_memoria: bool = False


class GeneratedDocumentRecord(BaseModel):
    organization_id: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))
    tipo: DocumentType
    titulo: str
    arquivo: str
    caminho: str
    texto: str
    cliente: str = ""
    orgao: str = ""
    processo: str = ""
    modalidade: str = ""
    objeto: str = ""
    case_id: str | None = None
    documento_id: str | None = None
    decisao_base: str = ""
    score_base: int | None = None
    memoria_sugerida: dict[str, Any] | None = None
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeneratedDocumentUpdate(BaseModel):
    titulo: str | None = None
    texto: str | None = None
    cliente: str | None = None
    orgao: str | None = None
    processo: str | None = None
    modalidade: str | None = None
    objeto: str | None = None
    metadata: dict[str, Any] | None = None


class DocumentGenerateResponse(BaseModel):
    documento: GeneratedDocumentRecord
    memoria_sugerida: dict[str, Any] | None = None


class GeneratedDocumentListResponse(BaseModel):
    total: int
    documentos: list[GeneratedDocumentRecord]
