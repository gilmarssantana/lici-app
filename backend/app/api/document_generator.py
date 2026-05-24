from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_permission
from app.schemas.document_generator import DocumentGenerateRequest, DocumentGenerateResponse, GeneratedDocumentListResponse, GeneratedDocumentRecord, GeneratedDocumentUpdate
from app.services.document_generator import LiciDocumentGenerator

router = APIRouter(prefix="/documentos", tags=["LICI Document Generator"])
generator = LiciDocumentGenerator()


@router.get("/engine")
def obter_document_generator(_: dict = Depends(require_permission("documentos:ler"))) -> dict[str, object]:
    return generator.engine_info()


@router.post("/gerar-impugnacao", response_model=DocumentGenerateResponse)
def gerar_impugnacao(payload: DocumentGenerateRequest, user: dict = Depends(require_permission("documentos:gerar"))) -> DocumentGenerateResponse:
    return generator.gerar_impugnacao(payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/gerar-recurso", response_model=DocumentGenerateResponse)
def gerar_recurso(payload: DocumentGenerateRequest, user: dict = Depends(require_permission("documentos:gerar"))) -> DocumentGenerateResponse:
    return generator.gerar_recurso(payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/gerar-contrarrazoes", response_model=DocumentGenerateResponse)
def gerar_contrarrazoes(payload: DocumentGenerateRequest, user: dict = Depends(require_permission("documentos:gerar"))) -> DocumentGenerateResponse:
    return generator.gerar_contrarrazoes(payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/gerados", response_model=GeneratedDocumentListResponse)
def listar_documentos_gerados(incluir_arquivados: bool = False, user: dict = Depends(require_permission("documentos:ler"))) -> GeneratedDocumentListResponse:
    return generator.list_generated(organization_id=user.get("active_organization_id") or user.get("organization_id"), incluir_arquivados=incluir_arquivados)


@router.get("/gerados/{document_id}", response_model=GeneratedDocumentRecord)
def obter_documento_gerado(document_id: str, user: dict = Depends(require_permission("documentos:ler"))) -> GeneratedDocumentRecord:
    return generator.get_generated(document_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.patch("/gerados/{document_id}", response_model=GeneratedDocumentRecord)
def atualizar_documento_gerado(document_id: str, payload: GeneratedDocumentUpdate, user: dict = Depends(require_permission("documentos:gerar"))) -> GeneratedDocumentRecord:
    return generator.update_generated(document_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/gerados/{document_id}/arquivar", response_model=GeneratedDocumentRecord)
def arquivar_documento_gerado(document_id: str, user: dict = Depends(require_permission("documentos:gerar"))) -> GeneratedDocumentRecord:
    return generator.archive_generated(document_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))
