from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_admin
from app.schemas.notificacao import NotificationResponse, NotificationSendRequest, NotificationTestRequest
from app.services.notificacao_engine import LiciNotificationEngine

router = APIRouter(prefix='/notificacoes', tags=['LICI Notificações Externas'])
engine = LiciNotificationEngine()


@router.get('/engine')
def obter_notificacoes_engine(_: dict = Depends(require_admin)) -> dict[str, object]:
    return engine.info()


@router.get('/logs')
def listar_logs(_: dict = Depends(require_admin)) -> dict[str, object]:
    return engine.logs()


@router.get('/logs/{log_id}')
def obter_log(log_id: str, _: dict = Depends(require_admin)) -> dict[str, object]:
    return engine.get_log(log_id)


@router.post('/logs/{log_id}/arquivar')
def arquivar_log(log_id: str, user: dict = Depends(require_admin)) -> dict[str, object]:
    return engine.arquivar_log(log_id, user)


@router.post('/testar', response_model=NotificationResponse)
def testar_notificacao(payload: NotificationTestRequest, user: dict = Depends(require_admin)) -> NotificationResponse:
    return engine.testar(payload, user)


@router.post('/enviar', response_model=NotificationResponse)
def enviar_notificacao(payload: NotificationSendRequest, user: dict = Depends(require_admin)) -> NotificationResponse:
    return engine.enviar(payload, user)
