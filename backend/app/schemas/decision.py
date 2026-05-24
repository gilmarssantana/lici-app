from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Decision = Literal["PARTICIPAR", "IMPUGNAR", "ESTRATÉGIA HÍBRIDA", "DESISTIR", "ANALISAR MAIS"]


class DecisionCriteria(BaseModel):
    aderencia_tecnica: int | None = Field(default=None, ge=0, le=100)
    risco_habilitacao: int | None = Field(default=None, ge=0, le=100)
    risco_juridico: int | None = Field(default=None, ge=0, le=100)
    oportunidade_competitiva: int | None = Field(default=None, ge=0, le=100)
    risco_execucao: int | None = Field(default=None, ge=0, le=100)
    historico_memoria_viva: int | None = Field(default=None, ge=0, le=100)
    necessidade_impugnacao: int | None = Field(default=None, ge=0, le=100)
    chance_estrategica_vitoria: int | None = Field(default=None, ge=0, le=100)


class DecisionRequest(BaseModel):
    pergunta: str = Field(..., min_length=3)
    termo_memoria: str | None = None
    criterios: DecisionCriteria = Field(default_factory=DecisionCriteria)
    contexto: str = ""
    consultar_rag: bool = False
    registrar_consequencia: bool = False
    caso_id: str | None = None
    cliente_id: str | None = None
    titulo_caso: str | None = None


class MemorySuggestion(BaseModel):
    tipo: str
    titulo: str
    descricao: str
    estrategia: str
    aprendizado: str
    uso_futuro: str
    tags: list[str] = Field(default_factory=list)


class DecisionResponse(BaseModel):
    decisao: Decision
    score: int = Field(..., ge=0, le=100)
    justificativa_objetiva: str
    riscos_criticos: list[str]
    acao_imediata: str
    risco_concorrencial: dict = Field(default_factory=dict)
    concorrentes_relevantes: list[dict] = Field(default_factory=list)
    oportunidade_ataque: str = ""
    recomendacao_blindagem: str = ""
    criterios: DecisionCriteria
    intencao: str
    termo_memoria: str
    memoria_consultada: dict
    consultar_rag: bool
    rag_orientacao: str
    memoria_sugerida: MemorySuggestion | None = None
    protocolo_aplicado: list[str]
    consequencia_operacional: dict = Field(default_factory=dict)
