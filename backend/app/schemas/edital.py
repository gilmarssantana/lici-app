from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.decision import DecisionResponse, MemorySuggestion


class EditalAnalyzeTextRequest(BaseModel):
    texto: str = Field(..., min_length=20)
    termo_memoria: str | None = None
    contexto_usuario: str = ""
    consultar_rag: bool = True


class EditalChecklistRequest(BaseModel):
    texto: str = Field(..., min_length=20)
    perfil_usuario: str = ""
    termo_memoria: str | None = None


class EditalChecklistItem(BaseModel):
    fase: str
    item: str
    risco: str
    acao: str
    prioridade: str


class EditalResumo(BaseModel):
    objeto: str
    modalidade: str
    prazos_criticos: list[str]
    exigencias_habilitacao: list[str]
    qualificacao_tecnica: list[str]
    atestados: list[str]


class EditalAnalysisResponse(BaseModel):
    resumo_edital: EditalResumo
    riscos: list[str]
    oportunidades: list[str]
    clausulas_restritivas: list[str]
    oportunidades_impugnacao: list[str]
    pontos_ataque_concorrentes: list[str]
    blindagem_usuario: list[str]
    checklist: list[EditalChecklistItem]
    decisao_recomendada: DecisionResponse
    memoria_consultada: dict
    rag_resultado: dict | None = None
    memoria_sugerida: MemorySuggestion | None = None


class EditalChecklistResponse(BaseModel):
    checklist: list[EditalChecklistItem]
    riscos_de_inabilitacao: list[str]
    blindagem_usuario: list[str]
    pontos_ataque_concorrentes: list[str]
    memoria_consultada: dict
