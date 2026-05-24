from __future__ import annotations

from fastapi import APIRouter

from app.schemas.triage import (
    TriageLogsResponse,
    TriageMarkRequest,
    TriageMarkResponse,
    TriageQueueResponse,
    TriageRunRequest,
    TriageRunResponse,
)
from app.services.triage_engine import LiciTriageEngine

router = APIRouter(prefix="/triagem", tags=["LICI Triage Engine"])
engine = LiciTriageEngine()


@router.get("/engine")
def obter_triage_engine() -> dict[str, object]:
    return {
        "nome": "LICI Triage Engine",
        "objetivo": "Analisar automaticamente a fila de oportunidades do Radar e separar o que merece atenção humana.",
        "endpoints": [
            "GET /triagem/engine",
            "GET /triagem/fila",
            "POST /triagem/executar",
            "POST /triagem/oportunidades/{id}/marcar",
        ],
        "classificacoes": ["prioridade_alta", "analisar", "monitorar", "descartar"],
        "funcoes": [
            "ler oportunidades pendentes do Radar",
            "classificar prioridade operacional",
            "justificar classificação",
            "identificar risco aparente",
            "identificar oportunidade estratégica",
            "sugerir criação de caso vivo quando prioridade for alta",
            "registrar log de triagem",
        ],
        "persistencia": ["/root/lici-app/triagem/fila.json", "/root/lici-app/triagem/logs.json"],
        "integracoes": ["Radar Engine", "Memory Core", "Decision Engine", "Case Engine"],
    }


@router.get("/fila", response_model=TriageQueueResponse)
def fila() -> TriageQueueResponse:
    return engine.fila()


@router.post("/executar", response_model=TriageRunResponse)
def executar(payload: TriageRunRequest | None = None) -> TriageRunResponse:
    return engine.executar(payload)


@router.post("/oportunidades/{opportunity_id}/marcar", response_model=TriageMarkResponse)
def marcar(opportunity_id: str, payload: TriageMarkRequest) -> TriageMarkResponse:
    return engine.marcar(opportunity_id, payload)


@router.get("/logs", response_model=TriageLogsResponse)
def logs() -> TriageLogsResponse:
    return engine.logs()
