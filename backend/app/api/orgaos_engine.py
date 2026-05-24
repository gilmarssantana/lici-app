from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_permission
from app.schemas.orgao import (
    OrgaoCreate,
    OrgaoEvent,
    OrgaoEventCreate,
    OrgaoHistoricoResponse,
    OrgaoListResponse,
    OrgaoRecord,
    OrgaoUpdate,
)
from app.services.orgao_engine import LiciOrgaosEngine

router = APIRouter(prefix="/orgaos", tags=["LICI Órgãos Engine"])
engine = LiciOrgaosEngine()


@router.get("/engine")
def obter_orgaos_engine(user: dict = Depends(require_permission("orgaos:ler"))) -> dict[str, object]:
    return engine.info()


@router.get("", response_model=OrgaoListResponse)
def listar_orgaos(user: dict = Depends(require_permission("orgaos:ler"))) -> OrgaoListResponse:
    return engine.list(organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/{orgao_id}", response_model=OrgaoRecord)
def obter_orgao(orgao_id: str, user: dict = Depends(require_permission("orgaos:ler"))) -> OrgaoRecord:
    return engine.get(orgao_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/registrar", response_model=OrgaoRecord)
def registrar_orgao(payload: OrgaoCreate, user: dict = Depends(require_permission("orgaos:escrever"))) -> OrgaoRecord:
    return engine.registrar(payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.patch("/{orgao_id}", response_model=OrgaoRecord)
def atualizar_orgao(orgao_id: str, payload: OrgaoUpdate, user: dict = Depends(require_permission("orgaos:escrever"))) -> OrgaoRecord:
    return engine.atualizar(orgao_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/{orgao_id}/arquivar", response_model=OrgaoRecord)
def arquivar_orgao(orgao_id: str, user: dict = Depends(require_permission("orgaos:escrever"))) -> OrgaoRecord:
    return engine.arquivar(orgao_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/{orgao_id}/registrar-evento", response_model=OrgaoEvent)
def registrar_evento_orgao(orgao_id: str, payload: OrgaoEventCreate, user: dict = Depends(require_permission("orgaos:escrever"))) -> OrgaoEvent:
    return engine.registrar_evento(orgao_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/{orgao_id}/historico", response_model=OrgaoHistoricoResponse)
def historico_orgao(orgao_id: str, user: dict = Depends(require_permission("orgaos:ler"))) -> OrgaoHistoricoResponse:
    return engine.historico(orgao_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))
