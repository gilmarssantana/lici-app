from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.security import get_current_user
from app.schemas.company_document import (
    CompanyChecklistRequest,
    CompanyChecklistResponse,
    CompanyDocument,
    CompanyDocumentCreate,
    CompanyDocumentDashboard,
    CompanyDocumentListResponse,
    CompanyDocumentUpdate,
    CompanyDossier,
)
from app.services.company_document import LiciCompanyDocumentService

router = APIRouter(prefix='/documental', tags=['LICI Documental Empresarial 360'])
service = LiciCompanyDocumentService()


def org(user: dict) -> str:
    return user.get('active_organization_id') or user.get('organization_id') or 'default-org'


@router.get('/engine')
def engine(_: dict = Depends(get_current_user)) -> dict[str, object]:
    return service.info()


@router.get('/dashboard', response_model=CompanyDocumentDashboard)
def dashboard(user: dict = Depends(get_current_user)) -> CompanyDocumentDashboard:
    return service.dashboard(org(user))


@router.get('/documentos', response_model=CompanyDocumentListResponse)
def listar_documentos(
    empresa_id: str | None = Query(default=None),
    cliente_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    tipo_documental: str | None = Query(default=None),
    escopo: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
) -> CompanyDocumentListResponse:
    itens = service.list_documents(org(user), limit=limit, offset=offset, empresa_id=empresa_id, cliente_id=cliente_id, status=status, tipo_documental=tipo_documental, escopo=escopo)
    return CompanyDocumentListResponse(itens=itens, total=len(itens))


@router.post('/documentos', response_model=CompanyDocument)
def criar_documento(payload: CompanyDocumentCreate, user: dict = Depends(get_current_user)) -> CompanyDocument:
    return service.create_document(payload, org(user))


@router.post('/documentos/upload', response_model=CompanyDocument)
def upload_documento(
    file: UploadFile = File(...),
    metadata: str = Form(...),
    user: dict = Depends(get_current_user),
) -> CompanyDocument:
    payload = CompanyDocumentCreate(**json.loads(metadata))
    return service.upload_document(file, org(user), payload)


@router.patch('/documentos/{document_id}', response_model=CompanyDocument)
def atualizar_documento(document_id: str, payload: CompanyDocumentUpdate, user: dict = Depends(get_current_user)) -> CompanyDocument:
    return service.update_document(document_id, payload, org(user))


@router.get('/dossie', response_model=CompanyDossier)
def dossie(empresa_id: str | None = Query(default=None), empresa_nome: str = Query(default=''), user: dict = Depends(get_current_user)) -> CompanyDossier:
    return service.dossier(org(user), empresa_id=empresa_id, empresa_nome=empresa_nome)


@router.post('/checklist', response_model=CompanyChecklistResponse)
def checklist(payload: CompanyChecklistRequest, user: dict = Depends(get_current_user)) -> CompanyChecklistResponse:
    return service.checklist(org(user), payload)
