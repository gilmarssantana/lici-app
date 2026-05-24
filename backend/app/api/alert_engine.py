from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_permission
from app.schemas.alert import (
    AlertGenerateRequest,
    AlertGenerateResponse,
    AlertListResponse,
    AlertLogsResponse,
    AlertMarkReadResponse,
)
from app.services.alert_engine import LiciAlertEngine

router = APIRouter(prefix="/alertas", tags=["LICI Alert Engine"])
engine = LiciAlertEngine()


@router.get("/engine")
def obter_alert_engine(_: dict = Depends(require_permission("dados:ler"))) -> dict[str, object]:
    return {
        "nome": "LICI Alert Engine",
        "objetivo": "Gerar alertas operacionais automáticos para oportunidades importantes, riscos críticos e ações pendentes.",
        "endpoints": [
            "GET /alertas/engine",
            "GET /alertas",
            "POST /alertas/gerar",
            "POST /alertas/{id}/marcar-lido",
        ],
        "severidades": ["critica", "alta", "media", "baixa"],
        "funcoes": [
            "ler fila da triagem",
            "gerar alertas para prioridade_alta",
            "gerar alertas para prazos críticos",
            "gerar alertas para casos vivos que exigem ação",
            "salvar alertas em JSON",
            "permitir marcar alerta como lido",
        ],
        "persistencia": ["/root/lici-app/alertas/alertas.json", "/root/lici-app/alertas/logs.json"],
        "integracoes": ["Triage Engine", "Radar Engine", "Case Engine", "Memory Core"],
    }


@router.get("", response_model=AlertListResponse)
def listar_alertas(incluir_lidos: bool = True, _: dict = Depends(require_permission("dados:ler"))) -> AlertListResponse:
    return engine.list_alerts(incluir_lidos=incluir_lidos)


@router.post("/gerar", response_model=AlertGenerateResponse)
def gerar_alertas(payload: AlertGenerateRequest | None = None, _: dict = Depends(require_permission("dados:escrever"))) -> AlertGenerateResponse:
    return engine.gerar(payload)


@router.post("/{alert_id}/marcar-lido", response_model=AlertMarkReadResponse)
def marcar_lido(alert_id: str, _: dict = Depends(require_permission("dados:escrever"))) -> AlertMarkReadResponse:
    return engine.marcar_lido(alert_id)


@router.post("/{alert_id}/arquivar", response_model=AlertMarkReadResponse)
def arquivar_alerta(alert_id: str, _: dict = Depends(require_permission("dados:escrever"))) -> AlertMarkReadResponse:
    return engine.arquivar(alert_id)


@router.get("/logs", response_model=AlertLogsResponse)
def logs(_: dict = Depends(require_permission("audit:ler"))) -> AlertLogsResponse:
    return engine.logs()
