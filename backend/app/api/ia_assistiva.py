from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_permission
from app.schemas.ia_assistiva import AssistiveFeedbackRequest, AssistiveRequest, AssistiveResponse, AssistiveTelemetrySummary
from app.services.ia_assistiva import LiciAssistiveAIService

router = APIRouter(prefix='/ia-assistiva', tags=['LICI IA Assistiva Contextual'])
service = LiciAssistiveAIService()


def org(user: dict) -> str:
    return user.get('active_organization_id') or user.get('organization_id') or 'default-org'


@router.get('/engine')
def engine(_: dict = Depends(require_permission('dados:ler'))) -> dict[str, object]:
    return service.info()


@router.post('/responder', response_model=AssistiveResponse)
def responder(payload: AssistiveRequest, user: dict = Depends(require_permission('dados:ler'))) -> AssistiveResponse:
    return service.responder(payload, user)


@router.post('/feedback', response_model=AssistiveTelemetrySummary)
def feedback(payload: AssistiveFeedbackRequest, user: dict = Depends(require_permission('dados:ler'))) -> AssistiveTelemetrySummary:
    return service.feedback(payload, user)


@router.get('/telemetria', response_model=AssistiveTelemetrySummary)
def telemetria(user: dict = Depends(require_permission('dados:ler'))) -> AssistiveTelemetrySummary:
    return service.telemetria(org(user))
