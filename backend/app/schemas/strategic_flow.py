from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.memory import MemoryCreate


class MemoryConsultRequest(BaseModel):
    termo: str = Field(..., min_length=1)


class MemoryConsultResponse(BaseModel):
    termo: str
    memoria: dict


class StrategicAnalysisRequest(BaseModel):
    pergunta: str = Field(..., min_length=3)
    termo_memoria: str | None = None
    consultar_rag: bool = False


class StrategicAnalysisPreparation(BaseModel):
    pergunta: str
    intencao: str
    termo_memoria: str
    memoria_consultada: dict
    consultar_rag: bool
    rag_orientacao: str
    protocolo: list[str]
    regra_resposta: list[str]
    memoria_sugerida_template: dict[str, str | list[str]]


class SuggestedMemoryRegistration(BaseModel):
    memoria: MemoryCreate
