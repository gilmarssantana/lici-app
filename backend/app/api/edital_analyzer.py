from __future__ import annotations

from fastapi import APIRouter

from app.schemas.edital import (
    EditalAnalysisResponse,
    EditalAnalyzeTextRequest,
    EditalChecklistRequest,
    EditalChecklistResponse,
)
from app.services.edital_analyzer import LiciEditalAnalyzer

router = APIRouter(prefix="/edital", tags=["LICI Edital Analyzer"])
analyzer = LiciEditalAnalyzer()


@router.get("/analyzer")
def obter_edital_analyzer() -> dict[str, object]:
    return {
        "nome": "LICI Edital Analyzer",
        "objetivo": "Analisar editais de forma estruturada e alimentar o Decision Engine.",
        "endpoints": [
            "GET /edital/analyzer",
            "POST /edital/analisar-texto",
            "POST /edital/checklist",
        ],
        "identifica": [
            "objeto da licitação",
            "modalidade",
            "prazos críticos",
            "exigências de habilitação",
            "qualificação técnica",
            "atestados",
            "riscos de inabilitação",
            "cláusulas restritivas",
            "oportunidades de impugnação",
            "pontos de ataque a concorrentes",
            "blindagem do usuário",
            "recomendação para Decision Engine",
        ],
        "integracoes": [
            "Protocolo Oficial de Análise Viva",
            "Memory Core",
            "RAG/base",
            "Decision Engine",
        ],
    }


@router.post("/analisar-texto", response_model=EditalAnalysisResponse)
def analisar_texto(payload: EditalAnalyzeTextRequest) -> EditalAnalysisResponse:
    return analyzer.analisar_texto(payload)


@router.post("/checklist", response_model=EditalChecklistResponse)
def checklist(payload: EditalChecklistRequest) -> EditalChecklistResponse:
    return analyzer.checklist(payload)
