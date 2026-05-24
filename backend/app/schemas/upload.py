from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.edital import EditalAnalysisResponse

DocumentStatus = Literal["recebido", "texto_extraido", "analisado", "erro", "arquivado"]


class UploadDocumentRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    organization_id: str = "default-org"
    nome_original: str
    nome_arquivo: str
    caminho: str
    content_type: str = ""
    extensao: str
    tamanho_bytes: int = 0
    status: DocumentStatus = "recebido"
    texto_extraido: str = ""
    caracteres_extraidos: int = 0
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    erro: str = ""
    analise: dict[str, Any] | None = None
    caso_id: str | None = None
    memoria_sugerida: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UploadDocumentUpdate(BaseModel):
    caso_id: str | None = None
    metadata: dict[str, Any] | None = None
    status: DocumentStatus | None = None
    erro: str | None = None


class UploadDocumentListResponse(BaseModel):
    total: int
    documentos: list[UploadDocumentRecord]


class UploadResponse(BaseModel):
    documento: UploadDocumentRecord


class UploadAnalyzeRequest(BaseModel):
    consultar_rag: bool = True
    criar_caso: bool = False
    cliente: str = "upload-engine"
    orgao: str = "Órgão não identificado"
    modalidade: str = ""
    fase_atual: str = "análise"
    status: str = "ativo"
    contexto_usuario: str = ""


class UploadAnalyzeResponse(BaseModel):
    documento: UploadDocumentRecord
    analise: EditalAnalysisResponse
    caso_id: str | None = None
    memoria_sugerida: dict[str, Any] | None = None
