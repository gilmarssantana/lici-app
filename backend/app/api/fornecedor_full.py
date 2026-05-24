from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.security import get_current_user
from app.schemas.fornecedor_full import FornecedorDashboardResponse, FornecedorListResponse, FornecedorRecord, FornecedorRecordCreate, FornecedorRecordUpdate
from app.services.fornecedor_full import LiciFornecedorFullService

router = APIRouter(prefix='/fornecedor-full', tags=['LICI Fornecedor Full'])
service = LiciFornecedorFullService()


def org(user: dict) -> str:
    return user.get('active_organization_id') or user.get('organization_id') or 'default-org'


@router.get('/engine')
def engine(_: dict = Depends(get_current_user)) -> dict[str, object]:
    return service.info()


@router.get('/dashboard', response_model=FornecedorDashboardResponse)
def dashboard(user: dict = Depends(get_current_user)) -> FornecedorDashboardResponse:
    return service.dashboard(org(user))


@router.get('/registros', response_model=FornecedorListResponse)
def listar(tipo: str | None = Query(default=None), limit: int = Query(default=200, ge=1, le=1000), offset: int = Query(default=0, ge=0), user: dict = Depends(get_current_user)) -> FornecedorListResponse:
    itens = service.list(org(user), tipo=tipo, limit=limit, offset=offset)
    return FornecedorListResponse(itens=itens, total=len(itens))


@router.post('/registros', response_model=FornecedorRecord)
def criar(payload: FornecedorRecordCreate, user: dict = Depends(get_current_user)) -> FornecedorRecord:
    return service.create(payload, org(user))


@router.patch('/registros/{record_id}', response_model=FornecedorRecord)
def atualizar(record_id: str, payload: FornecedorRecordUpdate, user: dict = Depends(get_current_user)) -> FornecedorRecord:
    return service.update(record_id, payload, org(user))
