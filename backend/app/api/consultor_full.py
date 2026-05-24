from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.security import get_current_user
from app.schemas.consultor_full import (
    ConsultorFollowup,
    ConsultorFollowupCreate,
    ConsultorFollowupListResponse,
    ConsultorFollowupUpdate,
    ConsultorFullDashboardResponse,
    ConsultorFullListResponse,
    ConsultorFullRecord,
    ConsultorFullRecordCreate,
    ConsultorFullRecordUpdate,
    ConsultorLead,
    ConsultorLeadCreate,
    ConsultorLeadListResponse,
    ConsultorLeadUpdate,
)
from app.services.consultor_full import LiciConsultorFullService

router = APIRouter(prefix='/consultor-full', tags=['LICI Consultor Full'])
service = LiciConsultorFullService()


def org(user: dict) -> str:
    return user.get('active_organization_id') or user.get('organization_id') or 'default-org'


@router.get('/engine')
def engine(_: dict = Depends(get_current_user)) -> dict[str, object]:
    return service.info()


@router.get('/dashboard', response_model=ConsultorFullDashboardResponse)
def dashboard(user: dict = Depends(get_current_user)) -> ConsultorFullDashboardResponse:
    return service.dashboard(org(user))


@router.get('/pipeline')
def pipeline(user: dict = Depends(get_current_user)) -> dict[str, object]:
    return service.pipeline(org(user))


@router.get('/central-360')
def central_360(user: dict = Depends(get_current_user)) -> list[dict[str, object]]:
    return service.central_360(org(user))


@router.get('/leads', response_model=ConsultorLeadListResponse)
def listar_leads(
    status: str | None = Query(default=None),
    pipeline_etapa: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
) -> ConsultorLeadListResponse:
    itens = service.list_leads(org(user), status_value=status, pipeline_etapa=pipeline_etapa, limit=limit, offset=offset)
    return ConsultorLeadListResponse(itens=itens, total=len(itens))


@router.post('/leads', response_model=ConsultorLead)
def criar_lead(payload: ConsultorLeadCreate, user: dict = Depends(get_current_user)) -> ConsultorLead:
    return service.create_lead(payload, org(user))


@router.patch('/leads/{lead_id}', response_model=ConsultorLead)
def atualizar_lead(lead_id: str, payload: ConsultorLeadUpdate, user: dict = Depends(get_current_user)) -> ConsultorLead:
    return service.update_lead(lead_id, payload, org(user))


@router.get('/followups', response_model=ConsultorFollowupListResponse)
def listar_followups(
    lead_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
) -> ConsultorFollowupListResponse:
    itens = service.list_followups(org(user), lead_id=lead_id, status_value=status, limit=limit, offset=offset)
    return ConsultorFollowupListResponse(itens=itens, total=len(itens))


@router.post('/followups', response_model=ConsultorFollowup)
def criar_followup(payload: ConsultorFollowupCreate, user: dict = Depends(get_current_user)) -> ConsultorFollowup:
    return service.create_followup(payload, org(user))


@router.patch('/followups/{followup_id}', response_model=ConsultorFollowup)
def atualizar_followup(followup_id: str, payload: ConsultorFollowupUpdate, user: dict = Depends(get_current_user)) -> ConsultorFollowup:
    return service.update_followup(followup_id, payload, org(user))


@router.get('/registros', response_model=ConsultorFullListResponse)
def listar(tipo: str | None = Query(default=None), limit: int = Query(default=200, ge=1, le=1000), offset: int = Query(default=0, ge=0), user: dict = Depends(get_current_user)) -> ConsultorFullListResponse:
    itens = service.list(org(user), tipo=tipo, limit=limit, offset=offset)
    return ConsultorFullListResponse(itens=itens, total=len(itens))


@router.post('/registros', response_model=ConsultorFullRecord)
def criar(payload: ConsultorFullRecordCreate, user: dict = Depends(get_current_user)) -> ConsultorFullRecord:
    return service.create(payload, org(user))


@router.patch('/registros/{record_id}', response_model=ConsultorFullRecord)
def atualizar(record_id: str, payload: ConsultorFullRecordUpdate, user: dict = Depends(get_current_user)) -> ConsultorFullRecord:
    return service.update(record_id, payload, org(user))
