from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_permission
from app.schemas.radar import (
    RadarCreateCaseRequest,
    RadarCreateCaseResponse,
    RadarOpportunityListResponse,
    RadarSearchRequest,
    RadarSearchResponse,
)
from app.services.radar_engine import LiciRadarEngine

router = APIRouter(prefix="/radar", tags=["LICI Radar Engine"])
engine = LiciRadarEngine()


@router.get("/engine")
def obter_radar_engine(_: dict = Depends(require_permission("radar:ler"))) -> dict[str, object]:
    return {
        "nome": "LICI Radar Engine",
        "objetivo": "Transformar prospecção de oportunidades em fluxo automático conectado aos casos vivos.",
        "fonte_principal": "PNCP",
        "persistencia": "/root/lici-app/radar/oportunidades.json",
        "endpoints": [
            "GET /radar/engine",
            "POST /radar/buscar",
            "GET /radar/oportunidades",
            "POST /radar/oportunidades/{id}/criar-caso",
        ],
        "funcoes": [
            "buscar oportunidades no PNCP",
            "filtrar por UF",
            "filtrar por palavras-chave",
            "calcular score preliminar",
            "identificar órgão, objeto, modalidade, valor estimado e datas",
            "salvar oportunidades encontradas",
            "transformar oportunidade em caso vivo",
            "sugerir memória quando identificar padrão relevante",
        ],
        "criterios_score": [
            "aderência ao segmento",
            "valor estimado",
            "prazo disponível",
            "risco aparente",
            "oportunidade estratégica",
            "histórico/memória do órgão",
        ],
        "integracoes": ["Case Engine", "Memory Core", "Decision Engine", "Protocolo Oficial de Análise Viva"],
    }


@router.post("/buscar", response_model=RadarSearchResponse)
def buscar_oportunidades(payload: RadarSearchRequest, _: dict = Depends(require_permission("radar:escrever"))) -> RadarSearchResponse:
    return engine.buscar(payload)


@router.get("/oportunidades", response_model=RadarOpportunityListResponse)
def listar_oportunidades(_: dict = Depends(require_permission("radar:ler"))) -> RadarOpportunityListResponse:
    return engine.listar_oportunidades()


@router.post("/oportunidades/{opportunity_id}/criar-caso", response_model=RadarCreateCaseResponse)
def criar_caso(opportunity_id: str, payload: RadarCreateCaseRequest, _: dict = Depends(require_permission("radar:escrever", "casos:escrever"))) -> RadarCreateCaseResponse:
    return engine.criar_caso(opportunity_id, payload)
