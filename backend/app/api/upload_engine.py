from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.security import require_permission
from app.schemas.upload import UploadAnalyzeRequest, UploadAnalyzeResponse, UploadDocumentListResponse, UploadDocumentRecord, UploadDocumentUpdate, UploadResponse
from app.services.upload_engine import LiciUploadEngine

router = APIRouter(prefix="/upload", tags=["LICI Upload Engine"])
engine = LiciUploadEngine()


@router.get("/engine")
def obter_upload_engine(_: dict = Depends(require_permission("upload:ler"))) -> dict[str, object]:
    return engine.engine_info()


@router.post("/edital", response_model=UploadResponse)
def upload_edital(file: UploadFile = File(...), user: dict = Depends(require_permission("upload:escrever"))) -> UploadResponse:
    return engine.receive_edital(file, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/documentos", response_model=UploadDocumentListResponse)
def listar_documentos(incluir_arquivados: bool = False, user: dict = Depends(require_permission("upload:ler"))) -> UploadDocumentListResponse:
    return engine.list_documents(organization_id=user.get("active_organization_id") or user.get("organization_id"), incluir_arquivados=incluir_arquivados)


@router.get("/documentos/{document_id}", response_model=UploadDocumentRecord)
def obter_documento(document_id: str, user: dict = Depends(require_permission("upload:ler"))) -> UploadDocumentRecord:
    return engine.get_document(document_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.patch("/documentos/{document_id}", response_model=UploadDocumentRecord)
def atualizar_documento(document_id: str, payload: UploadDocumentUpdate, user: dict = Depends(require_permission("upload:escrever"))) -> UploadDocumentRecord:
    return engine.update_document(document_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/documentos/{document_id}/arquivar", response_model=UploadDocumentRecord)
def arquivar_documento(document_id: str, user: dict = Depends(require_permission("upload:escrever"))) -> UploadDocumentRecord:
    return engine.archive_document(document_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/documentos/{document_id}/analisar", response_model=UploadAnalyzeResponse)
def analisar_documento(document_id: str, payload: UploadAnalyzeRequest | None = None, user: dict = Depends(require_permission("upload:escrever"))) -> UploadAnalyzeResponse:
    return engine.analyze_document(document_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))
