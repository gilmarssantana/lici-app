from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.security import require_permission
from app.services.export_engine import LiciExportEngine

router = APIRouter(prefix="/export", tags=["LICI Export Engine"])
engine = LiciExportEngine()


@router.get("/engine")
def obter_export_engine(_: dict = Depends(require_permission("export:ler"))) -> dict[str, object]:
    return engine.engine_info()


@router.get("/documentos/{document_id}/txt")
def exportar_documento_txt(document_id: str, _: dict = Depends(require_permission("export:ler"))) -> FileResponse:
    path = engine.export_document_txt(document_id)
    return _file(path, "text/plain; charset=utf-8")


@router.get("/documentos/{document_id}/docx")
def exportar_documento_docx(document_id: str, _: dict = Depends(require_permission("export:ler"))) -> FileResponse:
    path = engine.export_document_docx(document_id)
    return _file(path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.get("/casos/{case_id}/relatorio-txt")
def exportar_relatorio_caso_txt(case_id: str, _: dict = Depends(require_permission("export:ler"))) -> FileResponse:
    path = engine.export_case_report_txt(case_id)
    return _file(path, "text/plain; charset=utf-8")


@router.get("/casos/{case_id}/relatorio-docx")
def exportar_relatorio_caso_docx(case_id: str, _: dict = Depends(require_permission("export:ler"))) -> FileResponse:
    path = engine.export_case_report_docx(case_id)
    return _file(path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def _file(path: Path, media_type: str) -> FileResponse:
    return FileResponse(path=path, filename=path.name, media_type=media_type)
