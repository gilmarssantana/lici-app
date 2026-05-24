from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.security import require_permission
from app.services.audit_log import audit_event
from app.services.global_search import LiciGlobalSearchService

router = APIRouter(prefix="/busca", tags=["LICI Busca Global"])
service = LiciGlobalSearchService()


@router.get("/global")
def busca_global(q: str = Query(default="", min_length=0), _: dict = Depends(require_permission("dados:ler"))) -> dict:
    result = service.search(q)
    if q.strip():
        audit_event("busca_global", "consulta", "ok", {"q": q, "total": result.get("total", 0)})
    return result
