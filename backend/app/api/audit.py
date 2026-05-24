from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.security import require_permission
from app.services.audit_log import AUDIT_LOG_FILE, LiciAuditLog

router = APIRouter(prefix="/audit", tags=["LICI Audit Log"])
audit = LiciAuditLog()


@router.get("/logs")
def listar_audit_logs(
    limite: int = Query(default=200, ge=1, le=1000),
    modulo: str | None = Query(default=None),
    acao: str | None = Query(default=None),
    status: str | None = Query(default=None),
    _: dict = Depends(require_permission("audit:ler")),
) -> dict[str, object]:
    logs = audit.listar(limite=limite, modulo=modulo, acao=acao, status=status)
    return {
        "arquivo": str(AUDIT_LOG_FILE),
        "total": len(logs),
        "logs": logs,
    }
