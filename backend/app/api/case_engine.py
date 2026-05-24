from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas.case import (
    CaseCreate,
    CaseEventCreate,
    CaseListResponse,
    CasePhaseUpdate,
    CaseRecord,
    CaseTimelineResponse,
    CaseUpdate,
)
from app.api.security import require_permission
from app.services.case_engine import LiciCaseEngine

router = APIRouter(prefix="/casos", tags=["LICI Case Engine"])
engine = LiciCaseEngine()

FASES = [
    "prospecção",
    "análise",
    "impugnação",
    "habilitação",
    "disputa",
    "recurso",
    "homologação",
    "contrato",
    "execução",
    "pagamento",
    "encerrado",
]

EVENTOS = [
    "edital analisado",
    "impugnação enviada",
    "recurso protocolado",
    "concorrente inabilitado",
    "vitória",
    "perda",
    "contrato assinado",
    "pagamento atrasado",
    "reequilíbrio solicitado",
]


@router.get("")
def listar_casos(user: dict = Depends(require_permission("casos:ler"))) -> CaseListResponse:
    return engine.list_cases(organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/criar", response_model=CaseRecord)
def criar_caso(payload: CaseCreate, user: dict = Depends(require_permission("casos:escrever"))) -> CaseRecord:
    return engine.create_case(payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/engine")
def obter_case_engine(_: dict = Depends(require_permission("casos:ler"))) -> dict[str, object]:
    return {
        "nome": "LICI Case Engine",
        "objetivo": "Transformar análises isoladas em casos operacionais completos e acompanhar o ciclo da licitação.",
        "fases": FASES,
        "eventos": EVENTOS,
        "integracoes": ["Memory Core", "Decision Engine", "Edital Analyzer", "RAG/base"],
    }


@router.get("/{case_id}", response_model=CaseRecord)
def obter_caso(case_id: str, user: dict = Depends(require_permission("casos:ler"))) -> CaseRecord:
    return engine.get_case(case_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.patch("/{case_id}", response_model=CaseRecord)
def atualizar_caso(case_id: str, payload: CaseUpdate, user: dict = Depends(require_permission("casos:escrever"))) -> CaseRecord:
    return engine.update_case(case_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/{case_id}/arquivar", response_model=CaseRecord)
def arquivar_caso(case_id: str, user: dict = Depends(require_permission("casos:escrever"))) -> CaseRecord:
    return engine.archive_case(case_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/{case_id}/atualizar-fase", response_model=CaseRecord)
def atualizar_fase(case_id: str, payload: CasePhaseUpdate, user: dict = Depends(require_permission("casos:escrever"))) -> CaseRecord:
    return engine.update_phase(case_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/{case_id}/registrar-evento", response_model=CaseRecord)
def registrar_evento(case_id: str, payload: CaseEventCreate, user: dict = Depends(require_permission("casos:escrever"))) -> CaseRecord:
    return engine.register_event(case_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/{case_id}/timeline", response_model=CaseTimelineResponse)
def timeline(case_id: str, user: dict = Depends(require_permission("casos:ler"))) -> CaseTimelineResponse:
    return engine.timeline(case_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))
