from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

MemoryType = Literal[
    "orgao",
    "concorrente",
    "tese",
    "vitoria",
    "perda",
    "risco",
    "padrao",
    "contrato",
    "impugnacao",
    "recurso",
]


class MemoryCreate(BaseModel):
    organization_id: str | None = None
    tipo: MemoryType
    titulo: str = Field(..., min_length=3)
    descricao: str = Field(..., min_length=3)
    contexto: str = ""
    estrategia: str = ""
    resultado: str = ""
    aprendizado: str = ""
    uso_futuro: str = ""
    tags: list[str] = Field(default_factory=list)
    fonte: str = ""
    confianca: float = Field(default=0.7, ge=0, le=100)


class MemoryUpdate(BaseModel):
    tipo: MemoryType | None = None
    titulo: str | None = None
    descricao: str | None = None
    contexto: str | None = None
    estrategia: str | None = None
    resultado: str | None = None
    aprendizado: str | None = None
    uso_futuro: str | None = None
    tags: list[str] | None = None
    fonte: str | None = None
    confianca: float | None = Field(default=None, ge=0, le=100)


class MemoryRecord(MemoryCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    data: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MemorySearchResult(BaseModel):
    total: int
    items: list[MemoryRecord]
