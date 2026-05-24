from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_permission
from app.services.dashboard import LiciDashboardService

router = APIRouter(prefix="/dashboard", tags=["LICI Dashboard API"])
dashboard = LiciDashboardService()


@router.get("/resumo")
def resumo(user: dict = Depends(require_permission("dados:ler"))) -> dict:
    return dashboard.resumo(organization_id=user.get("active_organization_id") or user.get("organization_id"), user=user)


@router.get("/oportunidades")
def oportunidades(user: dict = Depends(require_permission("dados:ler", "radar:ler"))) -> dict:
    return dashboard.oportunidades(organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/casos")
def casos(user: dict = Depends(require_permission("dados:ler", "casos:ler"))) -> dict:
    return dashboard.casos(organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/alertas")
def alertas(_: dict = Depends(require_permission("dados:ler"))) -> dict:
    return dashboard.alertas()


@router.get("/memorias")
def memorias(user: dict = Depends(require_permission("dados:ler", "memoria:ler"))) -> dict:
    return dashboard.memorias(organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/kpis")
def kpis(user: dict = Depends(require_permission("dados:ler"))) -> dict:
    return dashboard.kpis(organization_id=user.get("active_organization_id") or user.get("organization_id"))
